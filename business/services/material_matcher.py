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
    db_sizes: list[dict] | None = None,
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

    # ── Route to smart stone matcher if supplier is stone ────
    if supplier_type == "stone" and db_sizes is not None:
        return await smart_match_stone_item(
            delivery_name=delivery_name,
            delivery_qty=delivery_qty,
            delivery_unit=delivery_unit,
            db_materials=db_materials,
            db_sizes=db_sizes,
            supplier_type=supplier_type,
        )

    logger.debug(
        "Matching delivery item: original=%r, translated=%r, base=%r, tokens=%s, supplier_type=%s",
        delivery_name, translated, base_name, delivery_tokens, supplier_type,
    )

    # ── Filter DB materials by supplier type ──────────────────
    # If we KNOW the supplier delivers stone → only match against stone materials
    # This prevents "Grey Lava" matching "Dark Grey G9484" (a pigment!)
    filtered_materials = db_materials
    if supplier_type:
        type_filtered = [m for m in db_materials if m.get("material_type") == supplier_type]
        if type_filtered:
            filtered_materials = type_filtered
            logger.debug("Supplier type=%s → filtered to %d materials (from %d)",
                        supplier_type, len(type_filtered), len(db_materials))

    # Score filtered DB materials
    scored: list[tuple[float, dict]] = []
    for mat in filtered_materials:
        db_tokens = tokenize_for_matching(mat["name"])

        # Score with both full name and base name (without color), take best
        score_full = calculate_match_score(delivery_tokens, db_tokens)
        score_base = calculate_match_score(base_tokens, db_tokens)
        score = max(score_full, score_base)

        # ── Bonus: size match (same base size, ignore thickness) ──
        delivery_sizes = re.findall(r'\d+(?:\.\d+)?x\d+(?:\.\d+)?', normalize_size(delivery_name))
        db_sizes = re.findall(r'\d+(?:\.\d+)?x\d+(?:\.\d+)?', normalize_size(mat["name"]))
        if delivery_sizes and db_sizes:
            # Extract just WxH (first 2 numbers), ignore thickness
            d_base = delivery_sizes[0]
            db_base = db_sizes[0]
            if d_base == db_base:
                score += 0.2  # exact size match
            else:
                # Same material, different size is FINE — don't penalize
                # "Lava Stone 5x20" and "Lava Stone 10x10" are same material type
                pass

        # ── Bonus: same unit ───────────────────────────────────
        mat_unit = (mat.get("unit") or "").lower()
        if mat_unit and mat_unit == translated_unit.lower():
            score += 0.05

        # ── Bonus: base material keyword match ─────────────────
        # If delivery has "lava" and DB has "lava" → strong signal
        base_keywords = {"lava", "andesite", "basalt", "granite", "marble",
                        "limestone", "sandstone", "terrazzo", "onyx", "travertine",
                        "frit", "kaolin", "bentonite", "feldspar", "silica"}
        common_base = base_tokens & db_tokens & base_keywords
        if common_base:
            score += 0.25  # strong bonus for same base material

        # ── Bonus: supplier confirms type match ────────────────
        if supplier_type and mat.get("material_type") == supplier_type:
            score += 0.1

        score = max(0.0, min(1.0, score))

        if score > 0:
            scored.append((score, mat))

        logger.debug(
            "  vs %r: db_tokens=%s, score=%.3f, common_base=%s",
            mat["name"], db_tokens, score, common_base if 'common_base' in dir() else set(),
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
    supplier_name: str | None = None,
    db_sizes: list[dict] | None = None,
) -> list[dict]:
    """
    Match a list of delivery note items against DB materials.

    Args:
        items: List of dicts with keys: name, quantity, unit.
        db_materials: All materials from DB.
        threshold: Minimum score for auto-match.
        supplier_name: Supplier name from delivery note (for type filtering).
        db_sizes: All sizes from DB (for smart stone matching).

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
            supplier_name=supplier_name,
            db_sizes=db_sizes,
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


# ────────────────────────────────────────────────────────────────
# Stone-specific: base material normalization
# ────────────────────────────────────────────────────────────────

# Short names → canonical full names for stone base materials
_STONE_BASE_NORMALIZE: dict[str, str] = {
    "lava": "Lava Stone",
    "lava stone": "Lava Stone",
    "andesite": "Andesite Stone",
    "andesite stone": "Andesite Stone",
    "basalt": "Basalt Stone",
    "basalt stone": "Basalt Stone",
    "granite": "Granite",
    "marble": "Marble",
    "limestone": "Limestone",
    "sandstone": "Sandstone",
    "terrazzo": "Terrazzo",
    "travertine": "Travertine",
    "onyx": "Onyx",
    "pumice": "Pumice Stone",
    "pumice stone": "Pumice Stone",
    "river stone": "River Stone",
    "natural stone": "Natural Stone",
    "porcelain": "Porcelain",
    "porcelain stone": "Porcelain Stone",
}

# Regex: size like "5x20", optional thickness like "x1-2" or "x1" or "x1/2"
_STONE_SIZE_RE = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)'
    r'(?:\s*[xX×]\s*(\d+(?:[.,/\-]\d+)?))?'
)

# Regex: diameter like "Ø29" or "dia30"
_DIAMETER_RE = re.compile(r'[øØ]\s*(\d+(?:\.\d+)?)|dia\w*\s*(\d+(?:\.\d+)?)', re.IGNORECASE)


def _parse_stone_delivery_name(delivery_name: str) -> dict:
    """
    Parse a stone delivery item name into components.

    "Grey Lava 5x20x1-2" →
        color="Grey", base_material="Lava Stone",
        size_raw="5x20", thickness_raw="1-2", is_round=False, diameter=None

    "Black Andesite Ø29x2" →
        color="Black", base_material="Andesite Stone",
        size_raw=None, thickness_raw="2", is_round=True, diameter=29.0
    """
    translated = translate_material_name(delivery_name)
    normalized = normalize_size(translated.strip())

    # Extract color
    words = normalized.split()
    color_parts: list[str] = []
    rest_parts: list[str] = []
    for w in words:
        if w.lower() in STRIP_COLORS and not rest_parts:
            color_parts.append(w)
        else:
            rest_parts.append(w)
    color = " ".join(color_parts).strip().title() if color_parts else None
    rest = " ".join(rest_parts)

    # Check for diameter (round shape)
    dia_match = _DIAMETER_RE.search(rest)
    is_round = dia_match is not None
    diameter = None
    if dia_match:
        diameter = float(dia_match.group(1) or dia_match.group(2))

    # Extract size and thickness from rest
    size_raw = None
    thickness_raw = None
    size_match = _STONE_SIZE_RE.search(rest)
    if size_match and not is_round:
        w_val = size_match.group(1).replace(",", ".")
        h_val = size_match.group(2).replace(",", ".")
        size_raw = f"{w_val}x{h_val}"
        if size_match.group(3):
            thickness_raw = size_match.group(3).replace(",", ".")
    elif is_round and size_match:
        # For round items "Ø29x2", the second number after Ø is thickness
        # But _STONE_SIZE_RE might catch "29x2" — check if first num == diameter
        w_val = float(size_match.group(1).replace(",", "."))
        if dia_match and abs(w_val - diameter) < 0.1:
            # "Ø29x2" → thickness is group(2)
            thickness_raw = size_match.group(2).replace(",", ".")
        else:
            h_val = size_match.group(2).replace(",", ".")
            size_raw = f"{size_match.group(1).replace(',', '.')}x{h_val}"
            if size_match.group(3):
                thickness_raw = size_match.group(3).replace(",", ".")

    # Determine base material: strip color, size, thickness from rest
    base_text = rest
    # Remove size pattern
    if size_match:
        base_text = base_text[:size_match.start()] + base_text[size_match.end():]
    # Remove diameter pattern
    if dia_match:
        base_text = base_text[:dia_match.start()] + base_text[dia_match.end():]
    base_text = re.sub(r'[xX×/\-\d.,]+', ' ', base_text).strip()
    base_text = re.sub(r'\s+', ' ', base_text).strip()

    # Normalize base material name
    base_lower = base_text.lower().strip()
    base_material = _STONE_BASE_NORMALIZE.get(base_lower, base_text.title() if base_text else "Stone")

    return {
        "color": color,
        "base_material": base_material,
        "size_raw": size_raw,
        "thickness_raw": thickness_raw,
        "is_round": is_round,
        "diameter": diameter,
    }


def _determine_product_type(
    thickness_raw: str | None,
    size_raw: str | None,
    is_round: bool,
    diameter: float | None,
) -> tuple[str, bool]:
    """
    Determine product type from thickness and size.

    Returns:
        (product_type, needs_user_choice)
        product_type: "3d" | "tiles" | "sink" | "table_top" | None
        needs_user_choice: True if ambiguous (user should pick)
    """
    # Step 2a: thickness with range → 3D
    if thickness_raw and re.search(r'[-/]', thickness_raw):
        return "3d", False

    # Step 2b: single thickness → check size rules
    if is_round and diameter is not None:
        if diameter > 40:
            # Could be sink or table_top — ask user
            return None, True
        elif diameter >= 29:
            # Ambiguous range — could be sink, table_top, or tile
            return None, True
        else:
            return "tiles", False

    if size_raw:
        m = re.match(r'(\d+(?:\.\d+)?)[xX](\d+(?:\.\d+)?)', size_raw)
        if m:
            w, h = float(m.group(1)), float(m.group(2))
            if w > 40 or h > 40:
                # Ø > 40cm equivalent for rect
                return None, True
            if (w > 30 and h > 60) or (w > 60 and h > 30):
                return None, True
            if (w > 40 and h > 40) or (w > 30 and h > 60) or (h > 30 and w > 60):
                return None, True
            return "tiles", False

    # Default for stone with single thickness
    return "tiles", False


async def smart_match_stone_item(
    delivery_name: str,
    delivery_qty: float,
    delivery_unit: str,
    db_materials: list[dict],
    db_sizes: list[dict],
    supplier_type: str | None = None,
) -> dict:
    """
    Smart matching for STONE materials with size DB lookup.

    Flow:
    1. Parse delivery name → color, base_material, size, thickness
    2. Determine product type from thickness (3d/tiles/sink/table_top)
    3. Look up size in DB (convert cm → mm)
    4. Build standard name: "{base_material} {product_type} {size_name}"
    5. Match against existing materials

    Returns dict compatible with find_best_match output, plus:
        - suggested_size_name: str (from DB or proposed new)
        - suggested_size_exists: bool
        - suggested_product_type: str (tiles/3d/sink/table_top)
        - needs_user_choice: bool (ambiguous size → user should pick)
        - parsed_color: str | None
        - parsed_base_material: str
    """
    translated = translate_material_name(delivery_name)
    translated_unit = INDO_TO_EN.get(delivery_unit.lower().strip(), delivery_unit)

    # ── Step 1: Parse delivery name ──────────────────────────
    parsed = _parse_stone_delivery_name(delivery_name)
    color = parsed["color"]
    base_material = parsed["base_material"]
    size_raw = parsed["size_raw"]
    thickness_raw = parsed["thickness_raw"]
    is_round = parsed["is_round"]
    diameter = parsed["diameter"]

    logger.debug(
        "smart_match_stone: delivery=%r, parsed=%s",
        delivery_name, parsed,
    )

    # ── Step 2: Determine product type ───────────────────────
    product_type, needs_user_choice = _determine_product_type(
        thickness_raw, size_raw, is_round, diameter,
    )

    # ── Step 3: Look up size in DB ───────────────────────────
    suggested_size_name = None
    suggested_size_exists = False
    matched_size_id = None

    if is_round and diameter is not None:
        # Round: search by name pattern "Ø{diameter}"
        dia_str = f"Ø{int(diameter)}" if diameter == int(diameter) else f"Ø{diameter}"
        for s in db_sizes:
            if dia_str.lower() in s["name"].lower():
                suggested_size_name = s["name"]
                suggested_size_exists = True
                matched_size_id = s["id"]
                break
        if not suggested_size_name:
            suggested_size_name = dia_str
    elif size_raw:
        # Rectangular: convert cm → mm
        sm = re.match(r'(\d+(?:\.\d+)?)[xX](\d+(?:\.\d+)?)', size_raw)
        if sm:
            w_cm, h_cm = float(sm.group(1)), float(sm.group(2))
            w_mm = int(w_cm * 10)
            h_mm = int(h_cm * 10)

            # Search DB: match both orientations
            for s in db_sizes:
                sw = s.get("width_mm", 0)
                sh = s.get("height_mm", 0)
                if (sw == w_mm and sh == h_mm) or (sw == h_mm and sh == w_mm):
                    suggested_size_name = s["name"]
                    suggested_size_exists = True
                    matched_size_id = s["id"]
                    break

            if not suggested_size_name:
                # Build size name from raw
                suggested_size_name = size_raw

    # ── Step 4: Build standard name ──────────────────────────
    type_label = ""
    if product_type == "3d":
        type_label = "3D"
    elif product_type == "tiles":
        type_label = "Tiles"
    elif product_type == "sink":
        type_label = "Sink"
    elif product_type == "table_top":
        type_label = "Table Top"

    name_parts = [base_material]
    if type_label:
        name_parts.append(type_label)
    if suggested_size_name:
        name_parts.append(suggested_size_name)
    standard_name = " ".join(name_parts)

    logger.debug(
        "smart_match_stone: standard_name=%r, product_type=%s, size=%s (exists=%s)",
        standard_name, product_type, suggested_size_name, suggested_size_exists,
    )

    # ── Step 5: Match against existing materials ─────────────
    # Filter to stone materials only
    stone_materials = [m for m in db_materials if m.get("material_type") == "stone"]
    if not stone_materials:
        stone_materials = db_materials

    best_match = None
    best_score = 0.0
    base_material_matches: list[dict] = []  # Same base, different size

    base_lower = base_material.lower()
    standard_tokens = tokenize_for_matching(standard_name)

    for mat in stone_materials:
        db_tokens = tokenize_for_matching(mat["name"])
        score = calculate_match_score(standard_tokens, db_tokens)

        # Check if same base material
        mat_lower = mat["name"].lower()
        has_same_base = base_lower in mat_lower or any(
            w in mat_lower for w in base_lower.split() if len(w) > 3
        )

        # Bonus: base material keyword
        if has_same_base:
            score += 0.25

        # Bonus: same product type
        if product_type and mat.get("product_subtype"):
            if product_type == mat["product_subtype"]:
                score += 0.15
            elif product_type == "3d" and "3d" in mat_lower:
                score += 0.15

        # Bonus: size match
        if suggested_size_name:
            size_lower = suggested_size_name.lower()
            if size_lower in mat_lower:
                score += 0.2

        # Bonus: same size_id
        if matched_size_id and mat.get("size_id") == matched_size_id:
            score += 0.2

        score = max(0.0, min(1.0, score))

        if has_same_base:
            base_material_matches.append({
                "material_id": mat["id"],
                "material_name": mat["name"],
                "score": round(score, 3),
            })

        if score > best_score:
            best_score = score
            best_match = mat

    # Sort base matches by score
    base_material_matches.sort(key=lambda x: x["score"], reverse=True)

    # Top 3 candidates
    candidates = base_material_matches[:3] if base_material_matches else []
    if not candidates and best_match:
        candidates = [{"material_id": best_match["id"], "material_name": best_match["name"], "score": round(best_score, 3)}]

    threshold = 0.5  # Higher threshold for smart matching
    matched = best_match is not None and best_score >= threshold

    # Determine suggestion context
    suggestion_context = None
    if not matched and base_material_matches:
        suggestion_context = "same_base_different_size"
    elif not matched:
        suggestion_context = "new_material"

    result = {
        "matched": matched,
        "material_id": best_match["id"] if matched and best_match else None,
        "material_name": best_match["name"] if matched and best_match else None,
        "score": round(best_score, 3),
        "translated_name": translated,
        "delivery_name": delivery_name,
        "quantity": delivery_qty,
        "unit": translated_unit,
        "suggested_name": standard_name if not matched else None,
        "suggested_type": "stone",
        "suggested_subtype": product_type,
        "candidates": candidates,
        # Stone-specific extras
        "suggested_size_name": suggested_size_name,
        "suggested_size_exists": suggested_size_exists,
        "suggested_product_type": product_type,
        "needs_user_choice": needs_user_choice,
        "parsed_color": color,
        "parsed_base_material": base_material,
        "suggestion_context": suggestion_context,
    }

    logger.info(
        "smart_match_stone: %r → matched=%s, score=%.3f, standard=%r, "
        "product_type=%s, size_exists=%s, needs_choice=%s",
        delivery_name, matched, best_score, standard_name,
        product_type, suggested_size_exists, needs_user_choice,
    )

    return result


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
