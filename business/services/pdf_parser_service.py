"""
PDF Parser Service — parses order PDFs (multi-template) into structured data.

Flow: PM uploads PDF -> detect template -> parser extracts data -> validate ->
      return preview with per-field confidence -> PM confirms.

Supports multiple supplier templates via pdf_templates registry.
"""

import re
import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Data classes ───────────────────────────────────────

class FieldConfidence:
    """Confidence score for a single extracted field."""
    def __init__(self, value: float = 0.0, source: str = "not_found"):
        # value: 0.0-1.0
        self.value = max(0.0, min(1.0, value))
        # source: "regex", "table", "positional", "fallback", "not_found"
        self.source = source

    def to_dict(self) -> dict:
        return {"value": round(self.value, 2), "source": self.source}


class ParsedOrderItem:
    """A single parsed item from the PDF."""
    def __init__(
        self,
        color: str = "",
        size: str = "",
        quantity_pcs: int = 0,
        quantity_sqm: Optional[float] = None,
        application: Optional[str] = None,
        finishing: Optional[str] = None,
        collection: Optional[str] = None,
        product_type: str = "tile",
        application_type: Optional[str] = None,
        place_of_application: Optional[str] = None,
        thickness: float = 11.0,
    ):
        self.color = color
        self.size = size
        self.quantity_pcs = quantity_pcs
        self.quantity_sqm = quantity_sqm
        self.application = application
        self.finishing = finishing
        self.collection = collection
        self.product_type = product_type
        self.application_type = application_type
        self.place_of_application = place_of_application
        self.thickness = thickness
        # Per-field confidence
        self.field_confidence: dict[str, FieldConfidence] = {}

    def to_dict(self) -> dict:
        return {
            "color": self.color,
            "size": self.size,
            "quantity_pcs": self.quantity_pcs,
            "quantity_sqm": self.quantity_sqm,
            "application": self.application,
            "finishing": self.finishing,
            "collection": self.collection,
            "product_type": self.product_type,
            "application_type": self.application_type,
            "place_of_application": self.place_of_application,
            "thickness": self.thickness,
            "field_confidence": {
                k: v.to_dict() for k, v in self.field_confidence.items()
            },
        }


class ParsedOrder:
    """Complete parsed order from PDF."""
    def __init__(self):
        self.order_number: str = ""
        self.client: str = ""
        self.client_location: Optional[str] = None
        self.sales_manager_name: Optional[str] = None
        self.document_date: Optional[str] = None  # ISO date string
        self.final_deadline: Optional[str] = None  # ISO date string
        self.desired_delivery_date: Optional[str] = None  # ISO date string
        self.mandatory_qc: bool = False
        self.notes: Optional[str] = None
        self.items: list[ParsedOrderItem] = []
        # Per-field confidence for header fields
        self.field_confidence: dict[str, FieldConfidence] = {}

    def to_dict(self) -> dict:
        return {
            "order_number": self.order_number,
            "client": self.client,
            "client_location": self.client_location,
            "sales_manager_name": self.sales_manager_name,
            "document_date": self.document_date,
            "final_deadline": self.final_deadline,
            "desired_delivery_date": self.desired_delivery_date,
            "mandatory_qc": self.mandatory_qc,
            "notes": self.notes,
            "items": [item.to_dict() for item in self.items],
            "field_confidence": {
                k: v.to_dict() for k, v in self.field_confidence.items()
            },
        }


class PdfParseResult:
    """Result of parsing a PDF."""
    def __init__(
        self,
        parsed_order: ParsedOrder,
        confidence: float,
        warnings: list[str],
        template_id: str = "generic",
        template_name: str = "Generic / Unknown",
        template_match_score: float = 0.0,
        validation_errors: Optional[list[str]] = None,
    ):
        self.parsed_order = parsed_order
        self.confidence = confidence
        self.warnings = warnings
        self.template_id = template_id
        self.template_name = template_name
        self.template_match_score = template_match_score
        self.validation_errors = validation_errors or []

    def to_dict(self) -> dict:
        return {
            "parsed_order": self.parsed_order.to_dict(),
            "confidence": round(self.confidence, 2),
            "warnings": self.warnings,
            "template_id": self.template_id,
            "template_name": self.template_name,
            "template_match_score": round(self.template_match_score, 2),
            "validation_errors": self.validation_errors,
        }


# ─── Pattern definitions ───────────────────────────────

# Common order number patterns
ORDER_NUM_PATTERNS = [
    r"(?:Order|Invoice|PO|No|Number|Nomor|#)\s*[:.]?\s*([A-Za-z0-9][\w\-/]+)",
    r"\b([A-Z]{1,4}[-/]\d{2,6}(?:[-/]\w+)?)\b",  # e.g., M-001, PO-2024/123
]

# Client name patterns
CLIENT_PATTERNS = [
    r"(?:Client|Customer|Buyer|Pelanggan|Nama)\s*[:.]?\s*(.+?)(?:\n|$)",
    r"(?:Bill\s*to|Ship\s*to|Kepada)\s*[:.]?\s*(.+?)(?:\n|$)",
]

# Location patterns
LOCATION_PATTERNS = [
    r"(?:Location|Address|Alamat|Lokasi|City|Kota)\s*[:.]?\s*(.+?)(?:\n|$)",
]

# Date patterns (multi-format)
DATE_PATTERNS = [
    r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})",   # DD/MM/YYYY or MM/DD/YYYY
    r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})",    # YYYY-MM-DD
    r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})",
]

DEADLINE_KEYWORDS = ["deadline", "due", "delivery", "pengiriman", "batas", "tenggat"]
DOC_DATE_KEYWORDS = ["date", "tanggal", "document", "order date", "issued"]

# Sales manager patterns
MANAGER_PATTERNS = [
    r"(?:Sales\s*Manager|Manager|Contact|PIC|Salesman)\s*[:.]?\s*(.+?)(?:\n|$)",
]

# Size patterns
SIZE_PATTERN = re.compile(r"(\d+)\s*[x\u00d7X]\s*(\d+)(?:\s*(?:cm|mm))?")

# Known valid sizes (common tile sizes in cm)
KNOWN_SIZES = {
    "10x10", "15x15", "20x20", "20x30", "25x25", "30x30", "30x60",
    "40x40", "45x45", "50x50", "60x60", "60x80", "60x100", "60x120",
    "80x80", "90x90", "100x100", "120x120",
    # Non-square
    "10x20", "10x30", "15x30", "20x40", "20x60", "25x50", "30x45",
    "30x90", "40x60", "40x80", "45x90",
}

# Product type detection
PRODUCT_TYPE_KEYWORDS = {
    "countertop": ["countertop", "counter top", "meja", "top"],
    "sink": ["sink", "wastafel", "basin"],
    "3d": ["3d", "3-d", "three dimensional", "tiga dimensi"],
}

# Finishing detection
FINISHING_KEYWORDS = ["matte", "matt", "glossy", "gloss", "polished", "honed", "natural", "tumbled", "brushed"]


# ─── Parsing helpers ──────────────────────────────────

def _extract_text_from_pdf(file_bytes: bytes) -> tuple[str, list[list[list[str]]]]:
    """Extract text + tables from PDF using pdfplumber."""
    import pdfplumber
    from io import BytesIO

    all_text = []
    all_tables = []

    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text.append(text)
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)

    return "\n".join(all_text), all_tables


def _parse_date(text: str, prefer_dmy: bool = True) -> Optional[str]:
    """Try to parse a date from text, return ISO format string."""
    # Try YYYY-MM-DD first
    m = re.search(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", text)
    if m:
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return d.isoformat()
        except ValueError:
            pass

    # Try DD/MM/YYYY or MM/DD/YYYY
    m = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", text)
    if m:
        a, b, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Heuristic: if first number > 12, it must be day
        if a > 12:
            try:
                d = date(year, b, a)
                return d.isoformat()
            except ValueError:
                pass
        # If second number > 12, it must be day
        elif b > 12:
            try:
                d = date(year, a, b)
                return d.isoformat()
            except ValueError:
                pass
        else:
            # Ambiguous — use template preference
            if prefer_dmy:
                try:
                    d = date(year, b, a)  # DD/MM/YYYY
                    return d.isoformat()
                except ValueError:
                    pass
            else:
                try:
                    d = date(year, a, b)  # MM/DD/YYYY
                    return d.isoformat()
                except ValueError:
                    pass

    # Try "DD Month YYYY"
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    m = re.search(r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{4})", text, re.IGNORECASE)
    if m:
        try:
            d = date(int(m.group(3)), months[m.group(2).lower()[:3]], int(m.group(1)))
            return d.isoformat()
        except (ValueError, KeyError):
            pass

    return None


def _find_pattern(text: str, patterns: list[str]) -> Optional[str]:
    """Find first matching pattern in text."""
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def _detect_product_type(text: str) -> str:
    """Detect product type from text."""
    text_lower = text.lower()
    for ptype, keywords in PRODUCT_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return ptype
    return "tile"


def _detect_finishing(text: str) -> Optional[str]:
    """Detect finishing type from text."""
    text_lower = text.lower()
    for finishing in FINISHING_KEYWORDS:
        if finishing in text_lower:
            return finishing.title()
    return None


def _parse_quantity(cell: str) -> tuple[int, Optional[float]]:
    """Parse quantity cell. Returns (pcs, sqm or None)."""
    cell = cell.strip()
    pcs = 0
    sqm = None

    # Try to extract pcs
    m = re.search(r"(\d+)\s*(?:pcs|pieces|\u0448\u0442|buah)?", cell, re.IGNORECASE)
    if m:
        pcs = int(m.group(1))

    # Try to extract sqm
    m = re.search(r"([\d.]+)\s*(?:sqm|m\u00b2|m2|\u043a\u0432\.?\s*\u043c)", cell, re.IGNORECASE)
    if m:
        sqm = float(m.group(1))

    # If no unit specified, just try to get a number
    if pcs == 0:
        m = re.search(r"(\d+)", cell)
        if m:
            pcs = int(m.group(1))

    return pcs, sqm


def _normalize_header(header: str) -> str:
    """Normalize table header for matching."""
    return re.sub(r"\s+", " ", header.strip().lower())


def _identify_columns(headers: list[str], template=None) -> dict[str, int]:
    """Map semantic column names to header indices, using template hints if available."""
    from business.services.pdf_templates import ColumnHints

    normalized = [_normalize_header(h or "") for h in headers]
    mapping = {}

    # Use template column hints if available, otherwise defaults
    if template and template.columns:
        cols = template.columns
    else:
        cols = ColumnHints()

    color_keys = cols.color_names
    size_keys = cols.size_names
    qty_keys = cols.qty_names
    app_keys = cols.application_names
    finish_keys = cols.finishing_names
    collection_keys = cols.collection_names
    product_keys = cols.product_type_names
    notes_keys = cols.notes_names

    for i, h in enumerate(normalized):
        if not h:
            continue
        if any(k in h for k in color_keys) and "color" not in mapping:
            mapping["color"] = i
        elif any(k in h for k in size_keys) and "size" not in mapping:
            mapping["size"] = i
        elif any(k in h for k in qty_keys) and "quantity" not in mapping:
            mapping["quantity"] = i
        elif any(k in h for k in app_keys) and "application" not in mapping:
            mapping["application"] = i
        elif any(k in h for k in finish_keys) and "finishing" not in mapping:
            mapping["finishing"] = i
        elif any(k in h for k in collection_keys) and "collection" not in mapping:
            mapping["collection"] = i
        elif any(k in h for k in product_keys) and "product_type" not in mapping:
            mapping["product_type"] = i
        elif any(k in h for k in notes_keys) and "notes" not in mapping:
            mapping["notes"] = i

    return mapping


# ─── Validation ───────────────────────────────────────

def _validate_parsed_order(order: ParsedOrder) -> list[str]:
    """Validate extracted data for consistency. Returns list of validation error messages."""
    errors: list[str] = []

    # Order number
    if not order.order_number:
        errors.append("Order number is missing")
    elif len(order.order_number) < 2:
        errors.append(f"Order number '{order.order_number}' seems too short")

    # Client
    if not order.client:
        errors.append("Client name is missing")

    # Dates
    if order.document_date:
        try:
            doc_date = date.fromisoformat(order.document_date)
            # Sanity: not in the distant past or future
            if doc_date.year < 2020:
                errors.append(f"Document date {order.document_date} seems too old (before 2020)")
            if doc_date > date.today():
                errors.append(f"Document date {order.document_date} is in the future")
        except ValueError:
            errors.append(f"Invalid document date format: {order.document_date}")

    if order.final_deadline:
        try:
            deadline = date.fromisoformat(order.final_deadline)
            if deadline.year < 2020:
                errors.append(f"Deadline {order.final_deadline} seems too old")
        except ValueError:
            errors.append(f"Invalid deadline format: {order.final_deadline}")

    # Deadline should be after document date
    if order.document_date and order.final_deadline:
        try:
            doc_d = date.fromisoformat(order.document_date)
            dead_d = date.fromisoformat(order.final_deadline)
            if dead_d < doc_d:
                errors.append("Deadline is before document date")
        except ValueError:
            pass

    # Items
    if not order.items:
        errors.append("No items extracted")
    else:
        for i, item in enumerate(order.items, 1):
            prefix = f"Item {i}"
            if item.quantity_pcs <= 0:
                errors.append(f"{prefix}: quantity must be > 0 (got {item.quantity_pcs})")
            if item.quantity_pcs > 100000:
                errors.append(f"{prefix}: quantity {item.quantity_pcs} seems unusually large")
            if not item.color:
                errors.append(f"{prefix}: color is missing")
            if not item.size:
                errors.append(f"{prefix}: size is missing")
            else:
                # Validate size format
                size_match = SIZE_PATTERN.search(item.size)
                if size_match:
                    w, h = int(size_match.group(1)), int(size_match.group(2))
                    if w <= 0 or h <= 0:
                        errors.append(f"{prefix}: size dimensions must be positive")
                    elif w > 300 or h > 300:
                        errors.append(f"{prefix}: size {item.size} has unusually large dimensions")
                # Not an error if size doesn't match pattern — could be a custom format

            if item.quantity_sqm is not None and item.quantity_sqm <= 0:
                errors.append(f"{prefix}: sqm quantity must be > 0 if specified")

    return errors


# ─── Main parsing function ────────────────────────────

def parse_order_pdf(file_bytes: bytes) -> PdfParseResult:
    """
    Parse an order PDF and extract structured data.

    Returns PdfParseResult with:
    - parsed_order: structured order data with per-field confidence
    - confidence: 0.0-1.0 overall score
    - warnings: list of parsing issues
    - template_id / template_name: detected template
    - template_match_score: how well the template matched
    - validation_errors: data consistency issues
    """
    warnings: list[str] = []
    confidence_factors: list[float] = []

    # 1. Extract text and tables
    try:
        full_text, tables = _extract_text_from_pdf(file_bytes)
    except ImportError as e:
        logger.error("PDF library not available: %s", e)
        return PdfParseResult(
            parsed_order=ParsedOrder(),
            confidence=0.0,
            warnings=[f"PDF parsing library not available: {str(e)}. Install pdfplumber."],
        )
    except Exception as e:
        logger.error("PDF extraction failed: %s", e)
        return PdfParseResult(
            parsed_order=ParsedOrder(),
            confidence=0.0,
            warnings=[f"Failed to extract text from PDF: {str(e)}"],
        )

    if not full_text.strip():
        return PdfParseResult(
            parsed_order=ParsedOrder(),
            confidence=0.0,
            warnings=["PDF appears to be empty or contains only images (not searchable text)"],
        )

    # 2. Detect template
    from business.services.pdf_templates import detect_template as _detect_tmpl
    template, template_score = _detect_tmpl(full_text)

    if template_score > 0.5:
        logger.info("Detected PDF template: %s (score=%.2f)", template.name, template_score)
    else:
        logger.info("No strong template match (best: %s, score=%.2f), using generic parsing", template.name, template_score)

    order = ParsedOrder()

    # Use template-specific or generic header patterns
    tmpl_hp = template.header_patterns
    order_num_patterns = tmpl_hp.order_number if tmpl_hp.order_number else ORDER_NUM_PATTERNS
    client_patterns = tmpl_hp.client if tmpl_hp.client else CLIENT_PATTERNS
    location_patterns = tmpl_hp.location if tmpl_hp.location else LOCATION_PATTERNS
    manager_patterns = tmpl_hp.manager if tmpl_hp.manager else MANAGER_PATTERNS
    deadline_kw = tmpl_hp.deadline_keywords if tmpl_hp.deadline_keywords else DEADLINE_KEYWORDS
    doc_date_kw = tmpl_hp.doc_date_keywords if tmpl_hp.doc_date_keywords else DOC_DATE_KEYWORDS

    prefer_dmy = template.date_format == "dmy"

    # 3. Extract order number
    order_num = _find_pattern(full_text, order_num_patterns)
    if not order_num and order_num_patterns is not ORDER_NUM_PATTERNS:
        # Fallback to generic patterns
        order_num = _find_pattern(full_text, ORDER_NUM_PATTERNS)
        if order_num:
            order.field_confidence["order_number"] = FieldConfidence(0.6, "fallback")
    if order_num:
        order.order_number = order_num
        if "order_number" not in order.field_confidence:
            order.field_confidence["order_number"] = FieldConfidence(0.9, "regex")
        confidence_factors.append(0.9)
    else:
        warnings.append("Could not find order number")
        order.field_confidence["order_number"] = FieldConfidence(0.0, "not_found")
        confidence_factors.append(0.2)

    # 4. Extract client
    client = _find_pattern(full_text, client_patterns)
    if not client and client_patterns is not CLIENT_PATTERNS:
        client = _find_pattern(full_text, CLIENT_PATTERNS)
        if client:
            order.field_confidence["client"] = FieldConfidence(0.6, "fallback")
    if client:
        order.client = client
        if "client" not in order.field_confidence:
            order.field_confidence["client"] = FieldConfidence(0.9, "regex")
        confidence_factors.append(0.9)
    else:
        warnings.append("Could not find client name")
        order.field_confidence["client"] = FieldConfidence(0.0, "not_found")
        confidence_factors.append(0.2)

    # 5. Extract location
    location = _find_pattern(full_text, location_patterns)
    if not location and location_patterns is not LOCATION_PATTERNS:
        location = _find_pattern(full_text, LOCATION_PATTERNS)
    if location:
        order.client_location = location
        order.field_confidence["client_location"] = FieldConfidence(0.8, "regex")
        confidence_factors.append(0.8)
    else:
        order.field_confidence["client_location"] = FieldConfidence(0.0, "not_found")
        confidence_factors.append(0.5)  # Optional field, less penalty

    # 6. Extract sales manager
    manager = _find_pattern(full_text, manager_patterns)
    if not manager and manager_patterns is not MANAGER_PATTERNS:
        manager = _find_pattern(full_text, MANAGER_PATTERNS)
    if manager:
        order.sales_manager_name = manager
        order.field_confidence["sales_manager_name"] = FieldConfidence(0.8, "regex")

    # 7. Extract dates
    lines = full_text.split("\n")
    for line in lines:
        line_lower = line.lower()
        parsed = _parse_date(line, prefer_dmy=prefer_dmy)
        if not parsed:
            continue

        if any(kw in line_lower for kw in deadline_kw):
            if not order.final_deadline:
                order.final_deadline = parsed
                order.field_confidence["final_deadline"] = FieldConfidence(0.85, "regex")
        elif any(kw in line_lower for kw in doc_date_kw):
            if not order.document_date:
                order.document_date = parsed
                order.field_confidence["document_date"] = FieldConfidence(0.85, "regex")
        elif not order.document_date:
            order.document_date = parsed
            order.field_confidence["document_date"] = FieldConfidence(0.5, "fallback")
        elif not order.final_deadline:
            order.final_deadline = parsed
            order.field_confidence["final_deadline"] = FieldConfidence(0.4, "fallback")

    if order.document_date:
        confidence_factors.append(0.8)
    else:
        warnings.append("Could not find document date")
        order.field_confidence["document_date"] = FieldConfidence(0.0, "not_found")
        confidence_factors.append(0.4)

    # 8. Parse items from tables
    items_parsed = False

    for table in tables:
        if not table or len(table) < 2:
            continue

        # Find header row (first row with text)
        header_row = None
        data_start = 0
        for i, row in enumerate(table):
            if row and any(cell and cell.strip() for cell in row):
                header_row = row
                data_start = i + 1
                break

        if not header_row:
            continue

        col_map = _identify_columns(header_row, template)

        # Need at minimum color + size + quantity to be a valid items table
        if "color" not in col_map or "quantity" not in col_map:
            # Try to detect by position if headers are not recognized
            if len(header_row) >= 3:
                has_sizes = False
                for row in table[data_start:]:
                    for cell in row:
                        if cell and SIZE_PATTERN.search(str(cell)):
                            has_sizes = True
                            break
                    if has_sizes:
                        break

                if not has_sizes:
                    continue

                # Try positional mapping from template or common layouts
                if len(header_row) >= 4:
                    offset = 0
                    first_header = _normalize_header(header_row[0] or "")
                    if first_header in ("no", "#", "no.", "\u043d\u043e\u043c\u0435\u0440", "n") or first_header == "":
                        offset = 1

                    # Use template positional order if available
                    if template and template.columns.positional_order:
                        for j, col_name in enumerate(template.columns.positional_order):
                            if col_name not in col_map and (offset + j) < len(header_row):
                                col_map[col_name] = offset + j
                    else:
                        if "color" not in col_map:
                            col_map["color"] = offset
                        if "size" not in col_map:
                            col_map["size"] = offset + 1
                        if "quantity" not in col_map:
                            col_map["quantity"] = offset + 2
            else:
                continue

        # Parse data rows
        for row in table[data_start:]:
            if not row or not any(cell and str(cell).strip() for cell in row):
                continue

            item = ParsedOrderItem()
            confidence_source = "table"

            # Check if columns were identified by header or positional
            if not any(_normalize_header(header_row[col_map.get("color", 0)] or "") in kw
                       for kw in (template.columns.color_names if template else ["color", "colour", "warna"])):
                confidence_source = "positional"

            # Color
            if "color" in col_map and col_map["color"] < len(row):
                cell = str(row[col_map["color"]] or "").strip()
                if cell:
                    item.color = cell
                    item.field_confidence["color"] = FieldConfidence(
                        0.9 if confidence_source == "table" else 0.6, confidence_source
                    )

            # Size
            if "size" in col_map and col_map["size"] < len(row):
                cell = str(row[col_map["size"]] or "").strip()
                if cell:
                    item.size = cell
                    # Boost confidence if size matches known pattern
                    size_match = SIZE_PATTERN.search(cell)
                    normalized = f"{size_match.group(1)}x{size_match.group(2)}" if size_match else ""
                    if normalized in KNOWN_SIZES:
                        item.field_confidence["size"] = FieldConfidence(0.95, confidence_source)
                    elif size_match:
                        item.field_confidence["size"] = FieldConfidence(0.8, confidence_source)
                    else:
                        item.field_confidence["size"] = FieldConfidence(0.5, confidence_source)

            # Quantity
            if "quantity" in col_map and col_map["quantity"] < len(row):
                cell = str(row[col_map["quantity"]] or "").strip()
                if cell:
                    pcs, sqm = _parse_quantity(cell)
                    item.quantity_pcs = pcs
                    item.quantity_sqm = sqm
                    item.field_confidence["quantity_pcs"] = FieldConfidence(
                        0.9 if pcs > 0 else 0.2, confidence_source
                    )

            # Application
            if "application" in col_map and col_map["application"] < len(row):
                cell = str(row[col_map["application"]] or "").strip()
                if cell:
                    item.application = cell

            # Finishing
            if "finishing" in col_map and col_map["finishing"] < len(row):
                cell = str(row[col_map["finishing"]] or "").strip()
                if cell:
                    item.finishing = cell

            # Collection
            if "collection" in col_map and col_map["collection"] < len(row):
                cell = str(row[col_map["collection"]] or "").strip()
                if cell:
                    item.collection = cell

            # Product type
            if "product_type" in col_map and col_map["product_type"] < len(row):
                cell = str(row[col_map["product_type"]] or "").strip()
                if cell:
                    item.product_type = _detect_product_type(cell)

            # Notes (from table row)
            if "notes" in col_map and col_map["notes"] < len(row):
                cell = str(row[col_map["notes"]] or "").strip()
                if cell:
                    if not item.finishing:
                        item.finishing = _detect_finishing(cell)
                    detected_type = _detect_product_type(cell)
                    if detected_type != "tile":
                        item.product_type = detected_type

            # Only add if we have meaningful data
            if item.color or item.size or item.quantity_pcs > 0:
                if not item.finishing:
                    row_text = " ".join(str(c or "") for c in row)
                    item.finishing = _detect_finishing(row_text)
                order.items.append(item)
                items_parsed = True

    # 9. Fallback: try to parse items from text if no tables found
    if not items_parsed and not tables:
        warnings.append("No tables found in PDF \u2014 attempting text-based extraction")
        for line in lines:
            size_match = SIZE_PATTERN.search(line)
            if not size_match:
                continue

            item = ParsedOrderItem()
            item.size = f"{size_match.group(1)}x{size_match.group(2)}"
            item.field_confidence["size"] = FieldConfidence(0.7, "regex")

            # Try to find quantity on the same line
            qty_match = re.search(r"(\d+)\s*(?:pcs|pieces|buah|\u0448\u0442)", line, re.IGNORECASE)
            if qty_match:
                item.quantity_pcs = int(qty_match.group(1))
                item.field_confidence["quantity_pcs"] = FieldConfidence(0.7, "regex")
            else:
                numbers = re.findall(r"\b(\d+)\b", line)
                size_nums = {size_match.group(1), size_match.group(2)}
                for n in numbers:
                    if n not in size_nums and 0 < int(n) < 100000:
                        item.quantity_pcs = int(n)
                        item.field_confidence["quantity_pcs"] = FieldConfidence(0.4, "fallback")
                        break

            # Try to find color (word before size or after quantity)
            words = line[:size_match.start()].strip().split()
            if words:
                item.color = words[-1]
                item.field_confidence["color"] = FieldConfidence(0.4, "fallback")

            item.finishing = _detect_finishing(line)
            item.product_type = _detect_product_type(line)

            if item.quantity_pcs > 0:
                order.items.append(item)

    # 10. Calculate confidence
    if order.items:
        confidence_factors.append(0.9)
        complete_items = sum(
            1 for it in order.items
            if it.color and it.size and it.quantity_pcs > 0
        )
        item_completeness = complete_items / len(order.items) if order.items else 0
        confidence_factors.append(item_completeness)

        if any(it.quantity_pcs <= 0 for it in order.items):
            warnings.append("Some items have zero or missing quantity")
        if any(not it.color for it in order.items):
            warnings.append("Some items are missing color")
        if any(not it.size for it in order.items):
            warnings.append("Some items are missing size")
    else:
        warnings.append("No order items could be extracted from the PDF")
        confidence_factors.append(0.1)

    # 11. Check for mandatory QC keywords
    qc_keywords = ["mandatory qc", "quality check required", "wajib qc", "qc wajib"]
    if any(kw in full_text.lower() for kw in qc_keywords):
        order.mandatory_qc = True

    # 12. Validate
    validation_errors = _validate_parsed_order(order)
    if validation_errors:
        # Reduce confidence proportionally to validation errors
        error_penalty = min(0.3, len(validation_errors) * 0.05)
        confidence_factors.append(1.0 - error_penalty)

    # Final confidence (also factor in template match)
    if template_score > 0.5:
        confidence_factors.append(min(1.0, template_score))

    confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
    confidence = max(0.0, min(1.0, confidence))

    return PdfParseResult(
        parsed_order=order,
        confidence=confidence,
        warnings=warnings,
        template_id=template.id,
        template_name=template.name,
        template_match_score=template_score,
        validation_errors=validation_errors,
    )


def validate_pdf_file(file_bytes: bytes, filename: str) -> list[str]:
    """Validate PDF file before parsing. Returns list of errors (empty = valid)."""
    errors = []

    # Check file size (max 20MB)
    max_size = 20 * 1024 * 1024
    if len(file_bytes) > max_size:
        errors.append(f"File too large: {len(file_bytes) / 1024 / 1024:.1f}MB (max 20MB)")

    # Check extension
    if not filename.lower().endswith(".pdf"):
        errors.append(f"Invalid file extension: expected .pdf, got {filename}")

    # Check magic bytes
    if not file_bytes.startswith(b"%PDF"):
        errors.append("File does not appear to be a valid PDF (invalid magic bytes)")

    return errors
