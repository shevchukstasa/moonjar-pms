"""
PDF Parser Service — parses order PDFs (fixed template) into structured data.

Flow: PM uploads PDF → parser extracts data → returns preview with confidence → PM confirms.
Supports the standard Moonjar order template with:
  - Order header (order number, client, date, deadline)
  - Items table (color, size, quantity, application, finishing, etc.)
"""

import re
import logging
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Data classes ───────────────────────────────────────

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
        }


class PdfParseResult:
    """Result of parsing a PDF."""
    def __init__(
        self,
        parsed_order: ParsedOrder,
        confidence: float,
        warnings: list[str],
    ):
        self.parsed_order = parsed_order
        self.confidence = confidence
        self.warnings = warnings

    def to_dict(self) -> dict:
        return {
            "parsed_order": self.parsed_order.to_dict(),
            "confidence": round(self.confidence, 2),
            "warnings": self.warnings,
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
SIZE_PATTERN = re.compile(r"(\d+)\s*[x×X]\s*(\d+)(?:\s*(?:cm|mm))?")

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


def _parse_date(text: str) -> Optional[str]:
    """Try to parse a date from text, return ISO format string."""
    # Try YYYY-MM-DD first
    m = re.search(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", text)
    if m:
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return d.isoformat()
        except ValueError:
            pass

    # Try DD/MM/YYYY
    m = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Heuristic: if first number > 12, it's DD/MM/YYYY
        if day > 12:
            try:
                d = date(year, month, day)
                return d.isoformat()
            except ValueError:
                pass
        # If second number > 12, it's MM/DD/YYYY
        elif month > 12:
            try:
                d = date(year, day, month)
                return d.isoformat()
            except ValueError:
                pass
        else:
            # Assume DD/MM/YYYY (more common in Indonesia)
            try:
                d = date(year, month, day)
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
    m = re.search(r"(\d+)\s*(?:pcs|pieces|шт|buah)?", cell, re.IGNORECASE)
    if m:
        pcs = int(m.group(1))

    # Try to extract sqm
    m = re.search(r"([\d.]+)\s*(?:sqm|m²|m2|кв\.?\s*м)", cell, re.IGNORECASE)
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


def _identify_columns(headers: list[str]) -> dict[str, int]:
    """Map semantic column names to header indices."""
    normalized = [_normalize_header(h or "") for h in headers]
    mapping = {}

    color_keys = ["color", "colour", "warna", "цвет"]
    size_keys = ["size", "dimension", "ukuran", "размер", "dim"]
    qty_keys = ["qty", "quantity", "jumlah", "количество", "pcs", "amount"]
    app_keys = ["application", "aplikasi", "применение"]
    finish_keys = ["finishing", "finish", "finisasi", "отделка"]
    collection_keys = ["collection", "koleksi", "коллекция"]
    product_keys = ["product", "type", "produk", "тип", "jenis"]
    notes_keys = ["notes", "note", "catatan", "remarks", "remark"]

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


# ─── Main parsing function ────────────────────────────

def parse_order_pdf(file_bytes: bytes) -> PdfParseResult:
    """
    Parse an order PDF and extract structured data.

    Returns PdfParseResult with:
    - parsed_order: structured order data
    - confidence: 0.0–1.0 score
    - warnings: list of parsing issues
    """
    warnings: list[str] = []
    confidence_factors: list[float] = []

    # 1. Extract text and tables
    try:
        full_text, tables = _extract_text_from_pdf(file_bytes)
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

    order = ParsedOrder()

    # 2. Extract order number
    order_num = _find_pattern(full_text, ORDER_NUM_PATTERNS)
    if order_num:
        order.order_number = order_num
        confidence_factors.append(0.9)
    else:
        warnings.append("Could not find order number")
        confidence_factors.append(0.2)

    # 3. Extract client
    client = _find_pattern(full_text, CLIENT_PATTERNS)
    if client:
        order.client = client
        confidence_factors.append(0.9)
    else:
        warnings.append("Could not find client name")
        confidence_factors.append(0.2)

    # 4. Extract location
    location = _find_pattern(full_text, LOCATION_PATTERNS)
    if location:
        order.client_location = location
        confidence_factors.append(0.8)
    else:
        confidence_factors.append(0.5)  # Optional field, less penalty

    # 5. Extract sales manager
    manager = _find_pattern(full_text, MANAGER_PATTERNS)
    if manager:
        order.sales_manager_name = manager

    # 6. Extract dates
    # Find all date-like strings with context
    lines = full_text.split("\n")
    for line in lines:
        line_lower = line.lower()
        parsed = _parse_date(line)
        if not parsed:
            continue

        if any(kw in line_lower for kw in DEADLINE_KEYWORDS):
            if not order.final_deadline:
                order.final_deadline = parsed
        elif any(kw in line_lower for kw in DOC_DATE_KEYWORDS):
            if not order.document_date:
                order.document_date = parsed
        elif not order.document_date:
            order.document_date = parsed
        elif not order.final_deadline:
            order.final_deadline = parsed

    if order.document_date:
        confidence_factors.append(0.8)
    else:
        warnings.append("Could not find document date")
        confidence_factors.append(0.4)

    # 7. Parse items from tables
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

        col_map = _identify_columns(header_row)

        # Need at minimum color + size + quantity to be a valid items table
        if "color" not in col_map or "quantity" not in col_map:
            # Try to detect by position if headers are not recognized
            # Common order: #, Color, Size, Qty, Application, Finishing, Notes
            if len(header_row) >= 3:
                # Heuristic: assume standard column order
                # Check if any data rows have size-like patterns
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

                # Try positional mapping for common layouts
                if len(header_row) >= 4:
                    # Skip first column if it looks like a row number
                    offset = 0
                    first_header = _normalize_header(header_row[0] or "")
                    if first_header in ("no", "#", "no.", "номер", "n") or first_header == "":
                        offset = 1

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

            # Color
            if "color" in col_map and col_map["color"] < len(row):
                cell = str(row[col_map["color"]] or "").strip()
                if cell:
                    item.color = cell

            # Size
            if "size" in col_map and col_map["size"] < len(row):
                cell = str(row[col_map["size"]] or "").strip()
                if cell:
                    item.size = cell

            # Quantity
            if "quantity" in col_map and col_map["quantity"] < len(row):
                cell = str(row[col_map["quantity"]] or "").strip()
                if cell:
                    pcs, sqm = _parse_quantity(cell)
                    item.quantity_pcs = pcs
                    item.quantity_sqm = sqm

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
                    # Detect finishing from notes if not already set
                    if not item.finishing:
                        item.finishing = _detect_finishing(cell)
                    # Detect product type from notes
                    detected_type = _detect_product_type(cell)
                    if detected_type != "tile":
                        item.product_type = detected_type

            # Only add if we have meaningful data
            if item.color or item.size or item.quantity_pcs > 0:
                # If no finishing detected from dedicated column, try to detect from all text
                if not item.finishing:
                    row_text = " ".join(str(c or "") for c in row)
                    item.finishing = _detect_finishing(row_text)
                order.items.append(item)
                items_parsed = True

    # 8. Fallback: try to parse items from text if no tables found
    if not items_parsed and not tables:
        warnings.append("No tables found in PDF — attempting text-based extraction")
        # Look for lines with size patterns
        for line in lines:
            size_match = SIZE_PATTERN.search(line)
            if not size_match:
                continue

            item = ParsedOrderItem()
            item.size = f"{size_match.group(1)}x{size_match.group(2)}"

            # Try to find quantity on the same line
            qty_match = re.search(r"(\d+)\s*(?:pcs|pieces|buah|шт)", line, re.IGNORECASE)
            if qty_match:
                item.quantity_pcs = int(qty_match.group(1))
            else:
                # Just find any number that's not part of the size
                numbers = re.findall(r"\b(\d+)\b", line)
                size_nums = {size_match.group(1), size_match.group(2)}
                for n in numbers:
                    if n not in size_nums and 0 < int(n) < 100000:
                        item.quantity_pcs = int(n)
                        break

            # Try to find color (word before size or after quantity)
            words = line[:size_match.start()].strip().split()
            if words:
                item.color = words[-1]

            item.finishing = _detect_finishing(line)
            item.product_type = _detect_product_type(line)

            if item.quantity_pcs > 0:
                order.items.append(item)

    # 9. Calculate confidence
    if order.items:
        confidence_factors.append(0.9)
        # Check item quality
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

    # 10. Check for mandatory QC keywords
    qc_keywords = ["mandatory qc", "quality check required", "wajib qc", "qc wajib"]
    if any(kw in full_text.lower() for kw in qc_keywords):
        order.mandatory_qc = True

    # Final confidence
    confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
    confidence = max(0.0, min(1.0, confidence))

    return PdfParseResult(
        parsed_order=order,
        confidence=confidence,
        warnings=warnings,
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
