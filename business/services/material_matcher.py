"""
Smart material name matcher for delivery note processing.
Handles Indonesian → English translation and fuzzy matching.

Flow: Delivery note (Indonesian) → translate → tokenize → score against DB materials
      → return best match or suggest new material creation.

Used by: warehouse receiving (Telegram bot, PDF parser, manual entry).
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("moonjar.material_matcher")


# ────────────────────────────────────────────────────────────────
# Indonesian → English translation dictionary
# ────────────────────────────────────────────────────────────────

# Multi-word phrases MUST come before single words in lookup order.
# The matching algorithm tries two-word phrases first, then single words.
INDO_TO_EN: dict[str, str] = {
    # ── Multi-word phrases (checked first) ──────────────────────
    "batu alam": "natural stone",
    "batu lava": "lava stone",
    "batu andesit": "andesite stone",
    "batu basalt": "basalt stone",
    "batu kali": "river stone",
    "batu apung": "pumice stone",
    "batu pasir": "sandstone",
    "batu kapur": "limestone",
    "batu marmer": "marble",
    "batu granit": "granite",
    "batu porselen": "porcelain stone",
    "tanah liat": "clay",
    "tanah putih": "white clay",
    "tanah merah": "red clay",
    "pasir kuarsa": "quartz sand",
    "serbuk kayu": "sawdust",
    "abu terbang": "fly ash",
    "bubble wrap": "bubble wrap",
    "lakban bening": "clear tape",
    "kertas koran": "newspaper",
    "cat semprot": "spray paint",
    "lem kayu": "wood glue",
    "kawat las": "welding wire",
    "besi siku": "angle iron",
    "gas elpiji": "lpg gas",
    "minyak tanah": "kerosene",
    "kayu bakar": "firewood",
    "amplas halus": "fine sandpaper",
    "amplas kasar": "coarse sandpaper",

    # ── Stone types ─────────────────────────────────────────────
    "batu": "stone",
    "keramik": "ceramic",
    "ubin": "tile",
    "genteng": "roof tile",
    "porselen": "porcelain",
    "teraso": "terrazzo",
    "marmer": "marble",
    "granit": "granite",
    "andesit": "andesite",
    "basalt": "basalt",
    "travertine": "travertine",
    "onyx": "onyx",

    # ── Raw materials / minerals ────────────────────────────────
    "kaolin": "kaolin",
    "feldspar": "feldspar",
    "bentonit": "bentonite",
    "silika": "silica",
    "kuarsa": "quartz",
    "calcium": "calcium",
    "alumina": "alumina",
    "zirkonium": "zirconium",
    "zirkon": "zircon",
    "wollastonit": "wollastonite",
    "bedak": "talc",
    "talk": "talc",
    "dolomit": "dolomite",
    "kapur": "calcium carbonate",
    "calcium": "calcium",
    "sodium": "sodium",
    "kalium": "potassium",
    "magnesium": "magnesium",
    "barium": "barium",
    "strontium": "strontium",
    "lithium": "lithium",
    "boron": "boron",
    "seng": "zinc",
    "timah": "tin",
    "tembaga": "copper",
    "besi": "iron",
    "mangan": "manganese",
    "kobalt": "cobalt",
    "nikel": "nickel",
    "krom": "chromium",
    "titanium": "titanium",

    # ── Chemicals ───────────────────────────────────────────────
    "oksida": "oxide",
    "karbonat": "carbonate",
    "nitrat": "nitrate",
    "sulfat": "sulfate",
    "hidroksida": "hydroxide",
    "silikat": "silicate",
    "fosfat": "phosphate",
    "pigmen": "pigment",
    "pewarna": "colorant",
    "glasir": "glaze",
    "engobe": "engobe",
    "frit": "frit",
    "semen": "cement",
    "gipsum": "gypsum",
    "epoksi": "epoxy",
    "resin": "resin",
    "pernis": "varnish",
    "lilin": "wax",
    "parafin": "paraffin",
    "asam": "acid",

    # ── Colors ──────────────────────────────────────────────────
    "hitam": "black",
    "putih": "white",
    "merah": "red",
    "hijau": "green",
    "biru": "blue",
    "kuning": "yellow",
    "coklat": "brown",
    "abu": "gray",
    "abu-abu": "gray",
    "emas": "gold",
    "perak": "silver",
    "krem": "cream",
    "oranye": "orange",
    "ungu": "purple",
    "pink": "pink",
    "tua": "dark",
    "muda": "light",
    "gelap": "dark",
    "terang": "light",
    "tomat": "tomato",

    # ── Units ───────────────────────────────────────────────────
    "kg": "kg",
    "gram": "g",
    "ton": "ton",
    "liter": "liters",
    "mililiter": "ml",
    "buah": "pcs",
    "lembar": "pcs",
    "batang": "pcs",
    "potong": "pcs",
    "pasang": "pairs",
    "lusin": "dozen",
    "karung": "bags",
    "sak": "bags",
    "bal": "bales",
    "galon": "gallons",
    "botol": "bottles",
    "ember": "buckets",
    "drum": "drums",
    "tabung": "cylinders",
    "roll": "rolls",
    "gulung": "rolls",
    "meter": "meters",

    # ── Packaging ───────────────────────────────────────────────
    "kardus": "box",
    "kotak": "box",
    "palet": "pallet",
    "plastik": "plastic",
    "karton": "carton",
    "kertas": "paper",
    "label": "label",
    "stiker": "sticker",
    "lakban": "tape",
    "isolasi": "tape",
    "tali": "rope",
    "rafia": "raffia",
    "stretch": "stretch film",
    "foam": "foam",
    "styrofoam": "styrofoam",
    "sudut": "corner protector",
    "paku": "nails",
    "staples": "staples",
    "lem": "glue",

    # ── Product types ───────────────────────────────────────────
    "meja": "table top",
    "wastafel": "sink",
    "basin": "basin",
    "bak": "basin",
    "mandi": "bath",
    "lantai": "floor",
    "dinding": "wall",
    "pagar": "fence",
    "pilar": "pillar",
    "pot": "pot",
    "vas": "vase",
    "mangkok": "bowl",
    "piring": "plate",
    "tegel": "tile",

    # ── Shapes / descriptors ────────────────────────────────────
    "bulat": "round",
    "oval": "oval",
    "persegi": "square",
    "kotak": "square",
    "segi": "angular",
    "panjang": "long",
    "pendek": "short",
    "besar": "large",
    "kecil": "small",
    "tebal": "thick",
    "tipis": "thin",
    "halus": "fine",
    "kasar": "coarse",
    "poles": "polished",
    "matt": "matte",
    "glossy": "glossy",
    "bertekstur": "textured",

    # ── Tools / consumables ─────────────────────────────────────
    "amplas": "sandpaper",
    "pisau": "knife",
    "gunting": "scissors",
    "sarung": "gloves",
    "masker": "mask",
    "kuas": "brush",
    "spons": "sponge",
    "saringan": "sieve",
    "kain": "cloth",
    "ember": "bucket",
    "selang": "hose",
    "pompa": "pump",
}

# Number of terms: 170+ covering stones, chemicals, packaging, colors,
# units, product types, shapes, tools, minerals, consumables.

# ────────────────────────────────────────────────────────────────
# Supplier → Material Type mapping
# ────────────────────────────────────────────────────────────────

# Known suppliers and what they deliver — everything from them is this type
SUPPLIER_MATERIAL_TYPE: dict[str, str] = {
    "bestone": "stone",
    "cv bestone": "stone",
    "cv. bestone": "stone",
    "bestone indonesia": "stone",
    "cv bestone indonesia": "stone",
    "cv. bestone indonesia": "stone",
    # Add more suppliers as they appear
}

# ────────────────────────────────────────────────────────────────
# Color variants → strip to base material
# ────────────────────────────────────────────────────────────────

# Colors that appear in stone names but don't change the base material
# "Grey Lava" → base material is "Lava", color is "Grey"
STRIP_COLORS = {
    "grey", "gray", "black", "white", "red", "green", "blue",
    "brown", "dark", "light", "cream", "beige", "pink", "yellow",
    "abu", "abu-abu", "hitam", "putih", "merah", "hijau", "biru",
    "coklat", "gelap", "terang", "kuning", "krem",
}

# Size ranges → product subtype
def guess_subtype_from_size(size_str: str) -> str | None:
    """Guess product subtype from size dimensions.

    Rules:
    - Rectangular < 25cm both sides → tiles
    - Rectangular >= 25cm any side → table_top
    - Round (Ø) 29-40cm → AMBIGUOUS (could be table_top, sink, or tile)
      → returns None so the user is asked to choose
    - Round > 40cm → table_top
    - Round < 29cm → tiles
    """
    if not size_str:
        return None

    # Check for round/diameter indicator (Ø29, dia30, etc.)
    round_match = re.search(r'[øØ]\s*(\d+(?:\.\d+)?)|dia\w*\s*(\d+(?:\.\d+)?)', size_str.lower())
    if round_match:
        diameter = float(round_match.group(1) or round_match.group(2))
        if diameter >= 29 and diameter <= 40:
            # Ambiguous range — could be table_top, sink, or tile
            # Return None to trigger user choice in bot
            return None
        elif diameter > 40:
            return "table_top"
        else:
            return "tiles"

    # Rectangular sizes
    m = re.match(r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)', size_str)
    if m:
        w, h = float(m.group(1)), float(m.group(2))
        # Sizes in cm
        if w >= 25 or h >= 25:
            return "table_top"
        return "tiles"
    return "tiles"  # default


def strip_color_from_name(name: str) -> str:
    """Remove color words to get base material name.
    'Grey Lava 5x20' → 'Lava 5x20'"""
    words = name.split()
    filtered = [w for w in words if w.lower() not in STRIP_COLORS]
    return " ".join(filtered) if filtered else name


def get_supplier_material_type(supplier_name: str | None) -> str | None:
    """If we know the supplier, return their default material type."""
    if not supplier_name:
        return None
    key = supplier_name.lower().strip()
    # Try progressively shorter prefixes
    for known, mtype in SUPPLIER_MATERIAL_TYPE.items():
        if known in key:
            return mtype
    return None


# ────────────────────────────────────────────────────────────────
# Size normalization
# ────────────────────────────────────────────────────────────────

_SIZE_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*[/xX×]\s*(\d+(?:[.,]\d+)?)')


def normalize_size(text: str) -> str:
    """
    Convert various size formats to standard NxN format.

    Examples:
        "10/10"   → "10x10"
        "5 x 20"  → "5x20"
        "10 X 10" → "10x10"
        "5,5/10"  → "5.5x10"
    """
    def _replace(m: re.Match) -> str:
        a = m.group(1).replace(",", ".")
        b = m.group(2).replace(",", ".")
        return f"{a}x{b}"
    return _SIZE_RE.sub(_replace, text)


# ────────────────────────────────────────────────────────────────
# Translation
# ────────────────────────────────────────────────────────────────

def translate_material_name(indo_name: str) -> str:
    """
    Translate Indonesian material name to English, preserving unknown words.

    Unknown words (brand names, codes, sizes) pass through unchanged.

    Examples:
        "Batu Lava 10/10"    → "lava stone 10x10"
        "Kaolin putih"       → "white kaolin"
        "Pigmen hitam"       → "black pigment"
        "Frit Tomat 5x20"   → "frit tomato 5x20"
        "Kardus 10x10"      → "box 10x10"
        "Batu wastafel oval" → "stone sink oval"
    """
    normalized = normalize_size(indo_name.strip())
    words = normalized.lower().split()
    result: list[str] = []
    i = 0
    while i < len(words):
        # Try two-word phrases first (e.g. "batu lava", "tanah liat")
        if i + 1 < len(words):
            two_word = f"{words[i]} {words[i + 1]}"
            if two_word in INDO_TO_EN:
                result.append(INDO_TO_EN[two_word])
                i += 2
                continue
        # Single word lookup
        word = words[i]
        if word in INDO_TO_EN:
            result.append(INDO_TO_EN[word])
        else:
            result.append(word)  # Keep as-is (brand names, sizes, codes)
        i += 1
    return " ".join(result)


# ────────────────────────────────────────────────────────────────
# Tokenization
# ────────────────────────────────────────────────────────────────

_SPLIT_RE = re.compile(r'[\s\-_,./()]+')


def tokenize_for_matching(name: str) -> set[str]:
    """
    Extract meaningful tokens from a material name for matching.

    Combines original tokens with translated tokens so that
    "Batu Lava 10x10" matches both "batu" and "lava stone".

    Tokens shorter than 2 chars are dropped (except size tokens like "5x5").
    """
    normalized = normalize_size(name.lower().strip())
    tokens = set(_SPLIT_RE.split(normalized))

    # Also add translated tokens
    translated = translate_material_name(name)
    tokens.update(_SPLIT_RE.split(translated.lower()))

    # Remove empty tokens and very short non-size ones
    return {t for t in tokens if len(t) > 1 or re.match(r'\d', t)}


# ────────────────────────────────────────────────────────────────
# Scoring
# ────────────────────────────────────────────────────────────────

_SIZE_TOKEN_RE = re.compile(r'^\d+(?:\.\d+)?x\d+(?:\.\d+)?$')


def calculate_match_score(
    delivery_tokens: set[str],
    db_tokens: set[str],
) -> float:
    """
    Calculate similarity score between delivery name tokens and DB material tokens.

    Uses F1 score (harmonic mean of precision and recall) on token overlap.
    Returns 0.0–1.0.
    """
    if not delivery_tokens or not db_tokens:
        return 0.0

    intersection = delivery_tokens & db_tokens
    if not intersection:
        return 0.0

    recall = len(intersection) / len(delivery_tokens)
    precision = len(intersection) / len(db_tokens)

    f1 = 2 * recall * precision / (recall + precision)
    return f1


# ────────────────────────────────────────────────────────────────
# Main matching function
# ────────────────────────────────────────────────────────────────

async def find_best_match(
    delivery_name: str,
    delivery_qty: float,
    delivery_unit: str,
    db_materials: list[dict],
    threshold: float = 0.4,
    supplier_name: str | None = None,
) -> dict:
    """
    Find the best matching material from the database.

    Args:
        delivery_name: Material name from delivery note (may be Indonesian).
        delivery_qty:  Quantity from delivery note.
        delivery_unit: Unit from delivery note (e.g. "kg", "karung").
        db_materials:  List of dicts from DB, each with keys:
                       id, name, material_type, unit, product_subtype.
        threshold:     Minimum score to consider a match (default 0.4).

    Returns:
        Dict with keys:
            matched          — True if a match was found above threshold.
            material_id      — UUID of matched material, or None.
            material_name    — DB name of matched material, or None.
            score            — Match confidence 0.0–1.0.
            translated_name  — English translation of delivery name.
            delivery_name    — Original name from delivery note.
            quantity         — Quantity from delivery note.
            unit             — Unit from delivery note.
            suggested_name   — Suggested English name for new material (if no match).
            suggested_type   — Guessed MaterialType value (if no match).
            suggested_subtype— Guessed ProductSubtype value (if no match).
            candidates       — Top 3 near-matches for manual selection.
    """
    translated = translate_material_name(delivery_name)
    # Translate the unit too
    translated_unit = INDO_TO_EN.get(delivery_unit.lower().strip(), delivery_unit)

    # Strip color to get base material name for better matching
    # "Grey Lava 5x20" → "Lava 5x20" → matches "Lava Stone" in DB
    base_name = strip_color_from_name(translated)
    delivery_tokens = tokenize_for_matching(delivery_name)
    base_tokens = tokenize_for_matching(base_name)

    # Supplier context: if we know supplier type, filter/boost relevant materials
    supplier_type = get_supplier_material_type(supplier_name)

    logger.debug(
        "Matching delivery item: original=%r, translated=%r, base=%r, tokens=%s, supplier_type=%s",
        delivery_name, translated, base_name, delivery_tokens, supplier_type,
    )

    # Score all DB materials
    scored: list[tuple[float, dict]] = []
    for mat in db_materials:
        db_tokens = tokenize_for_matching(mat["name"])

        # Score with both full name and base name (without color), take best
        score_full = calculate_match_score(delivery_tokens, db_tokens)
        score_base = calculate_match_score(base_tokens, db_tokens)
        score = max(score_full, score_base)

        # ── Bonus: exact size match ────────────────────────────
        delivery_sizes = re.findall(r'\d+(?:\.\d+)?x\d+(?:\.\d+)?', normalize_size(delivery_name))
        db_sizes = re.findall(r'\d+(?:\.\d+)?x\d+(?:\.\d+)?', normalize_size(mat["name"]))
        if delivery_sizes and db_sizes and delivery_sizes[0] == db_sizes[0]:
            score += 0.15

        # ── Bonus: same unit ───────────────────────────────────
        mat_unit = (mat.get("unit") or "").lower()
        if mat_unit and mat_unit == translated_unit.lower():
            score += 0.05

        # ── Bonus: material type match (guessed or from supplier) ──
        guessed_type = supplier_type or _guess_material_type(translated)
        if mat.get("material_type") and mat["material_type"] == guessed_type:
            score += 0.1  # bigger bonus when supplier confirms type

        # ── Bonus: supplier confirms this is stone and material is stone ──
        if supplier_type == "stone" and mat.get("material_type") == "stone":
            score += 0.1  # strong boost for matching supplier type

        score = max(0.0, min(1.0, score))

        if score > 0:
            scored.append((score, mat))

        logger.debug(
            "  vs %r: db_tokens=%s, score=%.3f",
            mat["name"], db_tokens, score,
        )

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score = scored[0][0] if scored else 0.0
    best_match = scored[0][1] if scored else None

    # Top 3 candidates for manual review
    candidates = [
        {"material_id": m["id"], "material_name": m["name"], "score": round(s, 3)}
        for s, m in scored[:3]
        if s > 0.1
    ]

    # Determine suggestions for new material
    suggested_type = _guess_material_type(translated)
    suggested_subtype = _guess_product_subtype(translated)
    suggested_name = _build_suggested_name(translated)

    if best_match and best_score >= threshold:
        logger.info(
            "Material matched: %r → %r (score=%.3f, id=%s)",
            delivery_name, best_match["name"], best_score, best_match["id"],
        )
        return {
            "matched": True,
            "material_id": best_match["id"],
            "material_name": best_match["name"],
            "score": round(best_score, 3),
            "translated_name": translated,
            "delivery_name": delivery_name,
            "quantity": delivery_qty,
            "unit": translated_unit,
            "suggested_name": None,
            "suggested_type": None,
            "suggested_subtype": None,
            "candidates": candidates,
        }
    else:
        logger.info(
            "No match for %r (best=%r, score=%.3f, threshold=%.2f). "
            "Suggesting new: name=%r, type=%s, subtype=%s",
            delivery_name,
            best_match["name"] if best_match else None,
            best_score,
            threshold,
            suggested_name,
            suggested_type,
            suggested_subtype,
        )
        return {
            "matched": False,
            "material_id": None,
            "material_name": best_match["name"] if best_match else None,
            "score": round(best_score, 3) if best_match else 0.0,
            "translated_name": translated,
            "delivery_name": delivery_name,
            "quantity": delivery_qty,
            "unit": translated_unit,
            "suggested_name": suggested_name,
            "suggested_type": suggested_type,
            "suggested_subtype": suggested_subtype,
            "candidates": candidates,
        }


# ────────────────────────────────────────────────────────────────
# Synchronous convenience wrapper
# ────────────────────────────────────────────────────────────────

def find_best_match_sync(
    delivery_name: str,
    delivery_qty: float,
    delivery_unit: str,
    db_materials: list[dict],
    threshold: float = 0.4,
) -> dict:
    """Synchronous version of find_best_match for non-async callers."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        find_best_match(delivery_name, delivery_qty, delivery_unit, db_materials, threshold)
    )


# ────────────────────────────────────────────────────────────────
# Batch matching (for full delivery notes)
# ────────────────────────────────────────────────────────────────

async def match_delivery_items(
    items: list[dict],
    db_materials: list[dict],
    threshold: float = 0.4,
) -> list[dict]:
    """
    Match a list of delivery note items against DB materials.

    Args:
        items: List of dicts with keys: name, quantity, unit.
        db_materials: All materials from DB.
        threshold: Minimum score for auto-match.

    Returns:
        List of match results (same structure as find_best_match output).
    """
    results = []
    for item in items:
        result = await find_best_match(
            delivery_name=item["name"],
            delivery_qty=item.get("quantity", 0),
            delivery_unit=item.get("unit", "pcs"),
            db_materials=db_materials,
            threshold=threshold,
        )
        results.append(result)

    matched_count = sum(1 for r in results if r["matched"])
    logger.info(
        "Batch matching: %d/%d items matched (threshold=%.2f)",
        matched_count, len(results), threshold,
    )
    return results


# ────────────────────────────────────────────────────────────────
# Internal helpers: type/subtype guessing
# ────────────────────────────────────────────────────────────────

def _guess_material_type(translated_name: str) -> str:
    """
    Guess MaterialType enum value from translated name.

    Matches against: stone, pigment, frit, oxide_carbonate,
    other_bulk, packaging, consumable, other.
    """
    lower = translated_name.lower()

    if any(w in lower for w in (
        "stone", "tile", "ceramic", "sink", "table top", "basin",
        "porcelain", "marble", "granite", "andesite", "basalt",
        "terrazzo", "travertine", "onyx", "limestone", "sandstone",
    )):
        return "stone"
    if "frit" in lower:
        return "frit"
    if any(w in lower for w in ("pigment", "colorant")):
        return "pigment"
    if any(w in lower for w in ("oxide", "carbonate", "nitrate", "sulfate", "hydroxide")):
        return "oxide_carbonate"
    if any(w in lower for w in ("glaze", "engobe")):
        return "other_bulk"
    if any(w in lower for w in (
        "box", "carton", "plastic", "tape", "label", "pallet",
        "bubble", "foam", "styrofoam", "stretch", "rope", "raffia",
        "staples", "nails", "corner protector", "sticker",
    )):
        return "packaging"
    if any(w in lower for w in (
        "kaolin", "bentonite", "silica", "clay", "feldspar",
        "quartz", "dolomite", "talc", "wollastonite", "alumina",
        "zircon", "calcium", "cement", "gypsum",
    )):
        return "other_bulk"
    if any(w in lower for w in (
        "sandpaper", "knife", "scissors", "gloves", "mask",
        "brush", "sponge", "sieve", "cloth", "bucket", "hose", "pump",
        "glue", "epoxy", "resin", "wax",
    )):
        return "consumable"

    return "other"


def _guess_product_subtype(translated_name: str) -> Optional[str]:
    """
    Guess MaterialProductSubtype for stone materials.

    Returns: "tiles", "sinks", "table_top", "custom", or None.
    """
    lower = translated_name.lower()

    if any(w in lower for w in ("sink", "basin", "wastafel", "bak")):
        return "sinks"
    if any(w in lower for w in ("table", "meja", "counter")):
        return "table_top"
    if any(w in lower for w in ("pot", "vase", "bowl", "plate", "pillar")):
        return "custom"

    # Tiles: stone/tile/ceramic with a size pattern
    if any(w in lower for w in ("tile", "stone", "ceramic")) and re.search(r'\d+x\d+', lower):
        return "tiles"
    # Default for generic stone references
    if any(w in lower for w in ("tile", "stone", "ceramic")):
        return "tiles"

    return None


def _build_suggested_name(translated_name: str) -> str:
    """
    Build a clean English name for a new material.

    Capitalizes words, keeps sizes as-is (e.g. "10x10").
    """
    words = translated_name.strip().split()
    result: list[str] = []
    for w in words:
        if re.match(r'^\d+(?:\.\d+)?x\d+(?:\.\d+)?$', w):
            result.append(w)  # Keep sizes as-is
        else:
            result.append(w.capitalize())
    return " ".join(result)
