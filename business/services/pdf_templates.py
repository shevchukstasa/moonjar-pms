"""
PDF Template Registry — defines supplier/format templates for PDF order parsing.

Each template describes:
  - name: Human-readable template name
  - detection: keywords, layout markers, and structural cues to identify the template
  - column_mapping: expected column order/names for the items table
  - header_extraction: patterns specific to this template for header fields
  - date_format: preferred date interpretation for this supplier

Templates are matched via `detect_template()` which scores each template
against the extracted PDF text and returns the best match (or "generic" fallback).
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ColumnHints:
    """Expected column semantics for a template's items table."""
    color_names: list[str] = field(default_factory=lambda: ["color", "colour", "warna"])
    size_names: list[str] = field(default_factory=lambda: ["size", "dimension", "ukuran"])
    qty_names: list[str] = field(default_factory=lambda: ["qty", "quantity", "jumlah", "pcs"])
    application_names: list[str] = field(default_factory=lambda: ["application", "aplikasi"])
    finishing_names: list[str] = field(default_factory=lambda: ["finishing", "finish"])
    collection_names: list[str] = field(default_factory=lambda: ["collection", "koleksi"])
    product_type_names: list[str] = field(default_factory=lambda: ["product", "type", "produk"])
    notes_names: list[str] = field(default_factory=lambda: ["notes", "note", "catatan", "remarks"])
    # Fixed column order when headers are not recognized (0-indexed, after skipping row-number col)
    positional_order: Optional[list[str]] = None


@dataclass
class TemplateHeaderPatterns:
    """Custom regex patterns for extracting header fields from a specific template."""
    order_number: list[str] = field(default_factory=list)
    client: list[str] = field(default_factory=list)
    location: list[str] = field(default_factory=list)
    manager: list[str] = field(default_factory=list)
    deadline_keywords: list[str] = field(default_factory=list)
    doc_date_keywords: list[str] = field(default_factory=list)


@dataclass
class PdfTemplate:
    """A single PDF template definition."""
    id: str
    name: str
    description: str
    # Detection: keywords that must appear (case-insensitive)
    detection_keywords: list[str] = field(default_factory=list)
    # Detection: regex patterns that should match in the full text
    detection_patterns: list[str] = field(default_factory=list)
    # Minimum keyword matches to consider this template (default: all must match)
    min_keyword_matches: int = 0  # 0 = all keywords must match
    # Column hints for this template
    columns: ColumnHints = field(default_factory=ColumnHints)
    # Header extraction overrides (empty = use generic patterns)
    header_patterns: TemplateHeaderPatterns = field(default_factory=TemplateHeaderPatterns)
    # Date format preference: "dmy" (DD/MM/YYYY, default for ID) or "mdy" (MM/DD/YYYY)
    date_format: str = "dmy"
    # Language hint for the template
    language: str = "en"


# ─── Template Definitions ─────────────────────────────

MOONJAR_STANDARD = PdfTemplate(
    id="moonjar_standard",
    name="Moonjar Standard Order",
    description="Default Moonjar internal order template with color/size/qty table",
    detection_keywords=["moonjar", "order"],
    detection_patterns=[
        r"(?i)moonjar",
        r"(?i)order\s*(?:number|no|#)",
    ],
    min_keyword_matches=1,
    columns=ColumnHints(
        positional_order=["color", "size", "quantity", "application", "finishing"],
    ),
    date_format="dmy",
    language="en",
)

MOONJAR_INDONESIAN = PdfTemplate(
    id="moonjar_id",
    name="Moonjar Indonesian Order",
    description="Indonesian language variant of Moonjar order template",
    detection_keywords=["moonjar"],
    detection_patterns=[
        r"(?i)moonjar",
        r"(?i)(nomor|tanggal|pesanan|jumlah|warna|ukuran)",
    ],
    min_keyword_matches=1,
    columns=ColumnHints(
        color_names=["warna", "color", "colour"],
        size_names=["ukuran", "size", "dimensi"],
        qty_names=["jumlah", "qty", "quantity", "buah"],
        application_names=["aplikasi", "application"],
        finishing_names=["finishing", "finisasi"],
        collection_names=["koleksi", "collection"],
        positional_order=["color", "size", "quantity", "application", "finishing"],
    ),
    header_patterns=TemplateHeaderPatterns(
        order_number=[r"(?:Nomor|No)\s*(?:Pesanan|Order)?\s*[:.]?\s*([A-Za-z0-9][\w\-/]+)"],
        client=[r"(?:Pelanggan|Nama|Klien)\s*[:.]?\s*(.+?)(?:\n|$)"],
        location=[r"(?:Alamat|Lokasi|Kota)\s*[:.]?\s*(.+?)(?:\n|$)"],
        deadline_keywords=["pengiriman", "batas", "tenggat", "deadline"],
        doc_date_keywords=["tanggal", "date", "tgl"],
    ),
    date_format="dmy",
    language="id",
)

GENERIC_SUPPLIER = PdfTemplate(
    id="generic_supplier",
    name="Generic Supplier PO",
    description="Generic purchase order / supplier invoice format",
    detection_keywords=[],
    detection_patterns=[
        r"(?i)(purchase\s*order|invoice|quotation|proforma)",
    ],
    min_keyword_matches=0,
    columns=ColumnHints(
        color_names=["color", "colour", "warna", "description"],
        size_names=["size", "dimension", "spec", "ukuran"],
        qty_names=["qty", "quantity", "amount", "jumlah", "pcs"],
    ),
    header_patterns=TemplateHeaderPatterns(
        order_number=[
            r"(?:PO|Purchase\s*Order|Invoice)\s*(?:No|Number|#)?\s*[:.]?\s*([A-Za-z0-9][\w\-/]+)",
        ],
        client=[
            r"(?:Bill\s*to|Ship\s*to|Customer|Buyer)\s*[:.]?\s*(.+?)(?:\n|$)",
        ],
    ),
    date_format="dmy",
    language="en",
)

RUSSIAN_ORDER = PdfTemplate(
    id="russian_order",
    name="Russian Order Template",
    description="Russian language order template",
    detection_keywords=[],
    detection_patterns=[
        r"(?i)(\u0437\u0430\u043a\u0430\u0437|\u0441\u0447\u0435\u0442|\u043d\u0430\u043a\u043b\u0430\u0434\u043d\u0430\u044f|\u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e|\u0446\u0432\u0435\u0442|\u0440\u0430\u0437\u043c\u0435\u0440)",  # заказ|счет|накладная|количество|цвет|размер
    ],
    min_keyword_matches=0,
    columns=ColumnHints(
        color_names=["цвет", "color", "colour"],
        size_names=["размер", "size", "dimension"],
        qty_names=["количество", "кол-во", "шт", "qty"],
        application_names=["применение", "application"],
        finishing_names=["отделка", "finishing"],
        collection_names=["коллекция", "collection"],
        positional_order=["color", "size", "quantity", "application", "finishing"],
    ),
    header_patterns=TemplateHeaderPatterns(
        order_number=[r"(?:Заказ|Номер|№)\s*[:.]?\s*([A-Za-z0-9А-Яа-я][\w\-/]+)"],
        client=[r"(?:Клиент|Заказчик|Покупатель)\s*[:.]?\s*(.+?)(?:\n|$)"],
        location=[r"(?:Адрес|Город|Местоположение)\s*[:.]?\s*(.+?)(?:\n|$)"],
        deadline_keywords=["срок", "дата доставки", "deadline"],
        doc_date_keywords=["дата", "date", "от"],
    ),
    date_format="dmy",
    language="ru",
)

# Fallback template — always matches with lowest priority
GENERIC_FALLBACK = PdfTemplate(
    id="generic",
    name="Generic / Unknown",
    description="Fallback template when no specific format is detected",
    detection_keywords=[],
    detection_patterns=[],
    min_keyword_matches=0,
    date_format="dmy",
    language="en",
)


# ─── Template Registry ────────────────────────────────

# Templates in priority order (first match with highest score wins)
TEMPLATE_REGISTRY: list[PdfTemplate] = [
    MOONJAR_STANDARD,
    MOONJAR_INDONESIAN,
    RUSSIAN_ORDER,
    GENERIC_SUPPLIER,
    # GENERIC_FALLBACK is not in the list — it's the automatic fallback
]


def get_template(template_id: str) -> PdfTemplate:
    """Get a template by ID."""
    for t in TEMPLATE_REGISTRY:
        if t.id == template_id:
            return t
    return GENERIC_FALLBACK


def detect_template(full_text: str) -> tuple[PdfTemplate, float]:
    """
    Detect which template best matches the PDF text.

    Returns (template, match_score) where match_score is 0.0–1.0.
    Falls back to GENERIC_FALLBACK with score 0.0 if nothing matches.
    """
    best_template = GENERIC_FALLBACK
    best_score = 0.0

    text_lower = full_text.lower()

    for template in TEMPLATE_REGISTRY:
        score = _score_template(template, text_lower, full_text)
        if score > best_score:
            best_score = score
            best_template = template

    return best_template, best_score


def _score_template(template: PdfTemplate, text_lower: str, full_text: str) -> float:
    """Score how well a template matches the given text."""
    scores: list[float] = []

    # Keyword matching
    if template.detection_keywords:
        keyword_hits = sum(1 for kw in template.detection_keywords if kw.lower() in text_lower)
        total_keywords = len(template.detection_keywords)
        min_required = template.min_keyword_matches or total_keywords

        if keyword_hits < min_required:
            return 0.0  # Hard fail if minimum keywords not met

        scores.append(keyword_hits / total_keywords)

    # Pattern matching
    if template.detection_patterns:
        pattern_hits = 0
        for pattern in template.detection_patterns:
            try:
                if re.search(pattern, full_text, re.IGNORECASE):
                    pattern_hits += 1
            except re.error:
                continue
        if template.detection_patterns:
            scores.append(pattern_hits / len(template.detection_patterns))

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


def list_templates() -> list[dict]:
    """List all registered templates with metadata (for API / admin UI)."""
    result = []
    for t in TEMPLATE_REGISTRY:
        result.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "language": t.language,
        })
    result.append({
        "id": GENERIC_FALLBACK.id,
        "name": GENERIC_FALLBACK.name,
        "description": GENERIC_FALLBACK.description,
        "language": GENERIC_FALLBACK.language,
    })
    return result
