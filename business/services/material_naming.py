"""Material naming, typology detection, and unit validation.

Single source of truth for the canonical model documented in
``docs/BUSINESS_LOGIC_FULL.md §29``. Used by:

  - ``api/routers/delivery.py`` — to build response with parsed_* fields
  - ``business/services/material_matcher.py`` — to canonicalise names before lookup
  - ``business/services/telegram_bot.py`` — to enforce unit rules in inline keyboards
  - frontend ``/materials/preview-name`` endpoint — for live name preview

For non-stone materials, ``short_name`` defaults to ``name``; only stone has
the canonical ``"Lava Stone {size}"`` rule.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# ── Type aliases ───────────────────────────────────────────────────

Typology = Literal["tiles", "3d", "sink", "countertop", "freeform"]
Shape = Literal["rectangle", "round", "triangle", "octagon", "freeform"]


# ── Constants ──────────────────────────────────────────────────────

# Color words stripped from delivery names (informational — color is NOT stored
# on Material; multiple color variants of same size collapse into one material).
STRIP_COLOR_WORDS = {
    "grey", "gray", "black", "white", "red", "green", "blue",
    "brown", "dark", "light", "cream", "beige", "pink", "yellow",
    "abu", "abu-abu", "hitam", "putih", "merah", "hijau", "biru",
    "coklat", "gelap", "terang", "kuning", "krem",
    # Origin / provenance words that aren't part of canonical name
    "bali", "java", "lombok",
}

# Words meaning "Lava" / "Lava Stone" in delivery wording — all collapse to base.
LAVA_BASE_WORDS = {"lava", "lavastone", "batu"}

# Allowed units per material_type. Hard validation at API boundary.
ALLOWED_UNITS_PER_TYPE: dict[str, set[str]] = {
    "stone": {"pcs", "m²"},
    "pigment": {"kg", "g"},
    "frit": {"kg", "g"},
    "oxide_carbonate": {"kg", "g"},
    "other_bulk": {"kg", "g"},
    "packaging": {"pcs", "m", "kg"},
    "consumable": {"pcs", "m", "kg"},
    "other": {"pcs", "m", "kg", "g", "L", "ml"},
}

DEFAULT_UNIT_PER_TYPE: dict[str, str] = {
    "stone": "pcs",
    "pigment": "kg",
    "frit": "kg",
    "oxide_carbonate": "kg",
    "other_bulk": "kg",
    "packaging": "pcs",
    "consumable": "pcs",
    "other": "pcs",
}

# 5 valid stone typologies. Legacy values (sinks/table_top/custom) are
# accepted for backward compat by the API but never returned by parser.
VALID_TYPOLOGIES: set[str] = {"tiles", "3d", "sink", "countertop", "freeform"}


# ── Regex helpers ──────────────────────────────────────────────────

_RECT_RE = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*[/xX×]\s*(\d+(?:[.,]\d+)?)'
    r'(?:\s*[/xX×]\s*(\d+(?:[.,/\-]\d+)?))?'
)
_DIA_RE = re.compile(r'[øØ]\s*(\d+(?:\.\d+)?)|dia\w*\s*(\d+(?:\.\d+)?)', re.IGNORECASE)
_NORMALIZE_X = re.compile(r'[×Xx]')


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class ParsedStoneName:
    """Result of parsing a raw stone delivery-note item name."""
    color: str | None
    base: str  # Always "Lava Stone" for now (single supplier base material)
    width_mm: int | None = None
    height_mm: int | None = None
    thickness_mm: int | None = None
    diameter_mm: int | None = None
    thickness_raw: str | None = None  # Original string e.g. "1-2"
    is_round: bool = False
    shape: Shape = "rectangle"
    typology: Typology | None = None
    needs_typology_choice: bool = False
    # Hint keywords detected in the source name (e.g. "sink", "wastafel", "countertop")
    explicit_typology_hints: set[str] = field(default_factory=set)


# ── Public API ─────────────────────────────────────────────────────

def normalize_unicode_x(text: str) -> str:
    """Replace all unicode × (U+00D7) with ASCII x. Idempotent.

    Required because OCR returns mix of × and x; downstream regex assumes one.
    """
    return text.replace("×", "x")


def is_valid_unit_for_type(material_type: str, unit: str) -> bool:
    """True if the unit is allowed for this material_type. See §29 table."""
    if not material_type or not unit:
        return False
    allowed = ALLOWED_UNITS_PER_TYPE.get(material_type)
    if allowed is None:
        return True  # unknown type → permissive
    return unit in allowed


def allowed_units_for_type(material_type: str) -> list[str]:
    """List of allowed units for this material_type (UI uses this to render dropdown)."""
    return sorted(ALLOWED_UNITS_PER_TYPE.get(material_type, {"pcs"}))


def default_unit_for_type(material_type: str) -> str:
    return DEFAULT_UNIT_PER_TYPE.get(material_type, "pcs")


def strip_color_words(name: str) -> tuple[str | None, str]:
    """Split off leading color words from the name.

    Returns (color, rest). Color is None if no color word present.
    Words are matched case-insensitively, only at the start of the name.
    """
    words = name.split()
    color_parts: list[str] = []
    rest_parts: list[str] = []
    seen_non_color = False
    for w in words:
        wl = w.lower()
        if wl in STRIP_COLOR_WORDS and not seen_non_color:
            color_parts.append(w)
        else:
            seen_non_color = True
            rest_parts.append(w)
    color = " ".join(color_parts).title() if color_parts else None
    return color, " ".join(rest_parts)


def parse_stone_delivery_name(raw_name: str) -> ParsedStoneName:
    """Parse a stone delivery-note item name into structured components.

    Examples:
        "Grey Lava 5×20×1.2"     → color="Grey", w=50,h=200,t=12, typology="tiles"
        "Black Lava 5×20×1-2"    → thickness_raw="1-2", typology="3d"
        "Bali Lava Sink Ø35×3"   → diameter=350, thickness=30, typology="sink"
        "Lava 60×100×3"          → countertop (large rect)
        "Grey Lava 5x20"         → width=50,height=200, no thickness
    """
    text = normalize_unicode_x(raw_name.strip())

    # Strip color and provenance words; what's left is base + size
    color, rest = strip_color_words(text)

    # Extract size first (so we can find typology hints in remaining text)
    diameter_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    thickness_mm: int | None = None
    thickness_raw: str | None = None
    is_round = False
    shape: Shape = "rectangle"

    dia_match = _DIA_RE.search(rest)
    if dia_match:
        is_round = True
        shape = "round"
        d_str = dia_match.group(1) or dia_match.group(2)
        diameter_mm = int(round(float(d_str) * 10))
        # Look for thickness/height after diameter
        after = rest[dia_match.end():]
        thick_match = re.search(r'\s*[xX]\s*(\d+(?:[.,/\-]\d+)?)', after)
        if thick_match:
            thickness_raw = thick_match.group(1).replace(",", ".")
            # If no range markers, parse as single number
            if not re.search(r'[/\-]', thickness_raw):
                try:
                    thickness_mm = int(round(float(thickness_raw) * 10))
                except ValueError:
                    pass
    else:
        rect_match = _RECT_RE.search(rest)
        if rect_match:
            w_cm = float(rect_match.group(1).replace(",", "."))
            h_cm = float(rect_match.group(2).replace(",", "."))
            width_mm = int(round(w_cm * 10))
            height_mm = int(round(h_cm * 10))
            if rect_match.group(3):
                thickness_raw = rect_match.group(3).replace(",", ".")
                if not re.search(r'[/\-]', thickness_raw):
                    try:
                        thickness_mm = int(round(float(thickness_raw) * 10))
                    except ValueError:
                        pass

    # Extract typology hints from the words around the size
    rest_lower = rest.lower()
    hints: set[str] = set()
    for kw in ("sink", "wastafel", "countertop", "top", "table", "freeform"):
        if kw in rest_lower:
            hints.add(kw)

    # Determine typology
    typology, needs_choice = _determine_typology(
        thickness_raw=thickness_raw,
        width_mm=width_mm,
        height_mm=height_mm,
        diameter_mm=diameter_mm,
        is_round=is_round,
        hints=hints,
    )

    return ParsedStoneName(
        color=color,
        base="Lava Stone",
        width_mm=width_mm,
        height_mm=height_mm,
        thickness_mm=thickness_mm,
        diameter_mm=diameter_mm,
        thickness_raw=thickness_raw,
        is_round=is_round,
        shape=shape,
        typology=typology,
        needs_typology_choice=needs_choice,
        explicit_typology_hints=hints,
    )


def _determine_typology(
    *,
    thickness_raw: str | None,
    width_mm: int | None,
    height_mm: int | None,
    diameter_mm: int | None,
    is_round: bool,
    hints: set[str],
) -> tuple[Typology | None, bool]:
    """Apply §29 auto-detect rules. Returns (typology, needs_user_choice)."""
    # Explicit hints win
    if "freeform" in hints:
        return "freeform", False
    if "sink" in hints or "wastafel" in hints:
        return "sink", False
    if "countertop" in hints or ("top" in hints and "table" in hints):
        return "countertop", False

    # Range thickness "1-2" or "1/2" → 3d
    if thickness_raw and re.search(r'[/\-]', thickness_raw):
        return "3d", False

    # Round shapes by diameter
    if is_round and diameter_mm is not None:
        d_cm = diameter_mm / 10
        if d_cm > 40:
            return "sink", False  # Default for large round
        if d_cm >= 29:
            return None, True  # Ambiguous: tile/sink/countertop
        return "tiles", False

    # Rectangular by largest dimension
    if width_mm and height_mm:
        max_cm = max(width_mm, height_mm) / 10
        if max_cm > 40:
            return "countertop", False
        return "tiles", False

    # No size info — let user pick
    return None, True


def build_size_label(parsed: ParsedStoneName) -> str:
    """Build human-readable size label for short_name from a parsed item.

    "Lava Stone 5×20×1.2" → label "5×20×1.2"
    "Lava Stone Ø35×3"    → label "Ø35×3"
    """
    if parsed.is_round and parsed.diameter_mm:
        d_cm = parsed.diameter_mm / 10
        d_str = f"{d_cm:g}"
        if parsed.thickness_raw:
            return f"Ø{d_str}×{parsed.thickness_raw}"
        return f"Ø{d_str}"

    if parsed.width_mm and parsed.height_mm:
        w = f"{parsed.width_mm / 10:g}"
        h = f"{parsed.height_mm / 10:g}"
        if parsed.thickness_raw:
            return f"{w}×{h}×{parsed.thickness_raw}"
        return f"{w}×{h}"

    return ""


def build_short_name(parsed: ParsedStoneName, design_name: str | None = None) -> str:
    """Build canonical short_name. Always "Lava Stone {size}" for stone.

    If design_name is provided, appends " · {design_name}" as a discriminator
    so materials of same size but different 3D variants/patterns stay distinct.
    Falls back to "Lava Stone Freeform" when no size could be parsed.
    """
    label = build_size_label(parsed)
    core = f"{parsed.base} {label}" if label else f"{parsed.base} Freeform"
    if design_name:
        core = f"{core} · {design_name.strip()}"
    return core[:100]


def build_short_name_from_raw(raw_name: str, design_name: str | None = None) -> str:
    """Convenience: parse + build_short_name in one call."""
    return build_short_name(parse_stone_delivery_name(raw_name), design_name=design_name)


__all__ = [
    "Typology",
    "Shape",
    "ParsedStoneName",
    "STRIP_COLOR_WORDS",
    "LAVA_BASE_WORDS",
    "ALLOWED_UNITS_PER_TYPE",
    "DEFAULT_UNIT_PER_TYPE",
    "VALID_TYPOLOGIES",
    "normalize_unicode_x",
    "is_valid_unit_for_type",
    "allowed_units_for_type",
    "default_unit_for_type",
    "strip_color_words",
    "parse_stone_delivery_name",
    "build_size_label",
    "build_short_name",
    "build_short_name_from_raw",
]
