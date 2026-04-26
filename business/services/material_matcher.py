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
    "stone_supplier": "stone",
    "chemical_supplier": "frit",
    "pigment_supplier": "pigment",
    "packaging_supplier": "packaging",
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
    - Rectangular >= 25cm any side → countertop
    - Round (Ø) 29-40cm → AMBIGUOUS (could be countertop, sink, or tile)
      → returns None so the user is asked to choose
    - Round > 40cm → countertop
    - Round < 29cm → tiles
    """
    if not size_str:
        return None

    # Check for round/diameter indicator (Ø29, dia30, etc.)
    round_match = re.search(r'[øØ]\s*(\d+(?:\.\d+)?)|dia\w*\s*(\d+(?:\.\d+)?)', size_str.lower())
    if round_match:
        diameter = float(round_match.group(1) or round_match.group(2))
        if diameter >= 29 and diameter <= 40:
            # Ambiguous range — could be countertop, sink, or tile
            # Return None to trigger user choice in bot
            return None
        elif diameter > 40:
            return "countertop"
        else:
            return "tiles"

    # Rectangular sizes
    m = re.match(r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)', size_str)
    if m:
        w, h = float(m.group(1)), float(m.group(2))
        # Sizes in cm
        if w >= 25 or h >= 25:
            return "countertop"
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
        "10/10"        → "10x10"
        "5 x 20"       → "5x20"
        "10 X 10"      → "10x10"
        "5,5/10"       → "5.5x10"
        "5×20×1.2"     → "5x20x1.2"  (Unicode × → ASCII x)
    """
    # First pass: convert all unicode × (U+00D7) to ASCII x so token-level
    # comparison works ("Lavastone 5×20×1.2" vs "Lavastone 5x20x1.2").
    text = text.replace("×", "x")

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


_CHEMICAL_ALIASES: dict[str, str] = {
    # Every variant maps to the DB's canonical token so "Aluminium Oxide"
    # doesn't match "Cooper oxide" on the shared stop-word "oxide" alone.
    "aluminium": "alumina",
    "aluminum":  "alumina",
    "al2o3":     "alumina",
    "cuprum":    "copper",
    "cooper":    "copper",   # common spelling drift (DB has "Cooper oxide")
    "cu2o":      "copper",
    "zirconia":  "zircon",
    "zirconium": "zircon",
    "silicon":   "silica",
    "sio2":      "silica",
    "ferric":    "iron",
    "ferrous":   "iron",
    "chromium":  "chrome",
    "kobalt":    "cobalt",
    "titanium":  "titania",
    "tio2":      "titania",
    "kalsium":   "calcium",
    "calsium":   "calcium",
}

# Tokens that appear in MANY material names and therefore shouldn't dominate
# scoring on their own (they're informational, not discriminative).
_GENERIC_TOKENS: set[str] = {
    "oxide", "carbonate", "hydroxide", "nitrate", "sulfate", "sulphate",
    "chloride", "phosphate", "silicate",
    "powder", "paste", "liquid", "solution", "glaze", "engobe", "frit",
    "fine", "coarse", "raw", "pure", "mix", "mixed", "type", "grade",
    "stone", "tile", "stick", "kg", "pcs", "ml", "gr", "gram",
    "dark", "light",
}


def _apply_aliases(tokens: set[str]) -> set[str]:
    """Collapse chemical synonyms so that Aluminium ↔ Alumina etc. match."""
    return {_CHEMICAL_ALIASES.get(t, t) for t in tokens}


def tokenize_for_matching(name: str) -> set[str]:
    """
    Extract meaningful tokens from a material name for matching.

    Combines original tokens with translated tokens so that
    "Batu Lava 10x10" matches both "batu" and "lava stone".

    Tokens shorter than 2 chars are dropped (except size tokens like "5x5").
    Chemical synonyms are folded into their canonical form.
    """
    normalized = normalize_size(name.lower().strip())
    tokens = set(_SPLIT_RE.split(normalized))

    # Also add translated tokens
    translated = translate_material_name(name)
    tokens.update(_SPLIT_RE.split(translated.lower()))

    # Remove empty tokens and very short non-size ones
    tokens = {t for t in tokens if len(t) > 1 or re.match(r'\d', t)}

    return _apply_aliases(tokens)


# ────────────────────────────────────────────────────────────────
# Scoring
# ────────────────────────────────────────────────────────────────

_SIZE_TOKEN_RE = re.compile(r'^\d+(?:\.\d+)?x\d+(?:\.\d+)?$')


def _token_weight(token: str) -> float:
    """Down-weight generic tokens so shared "oxide" alone can't match two
    different compounds. Size tokens stay at 1.0 — they are discriminative."""
    if token in _GENERIC_TOKENS:
        return 0.25
    return 1.0


def calculate_match_score(
    delivery_tokens: set[str],
    db_tokens: set[str],
) -> float:
    """
    Weighted F1 over token overlap. Generic tokens (oxide, powder, stone, …)
    contribute only 0.25 mass, so "Aluminium Oxide" ↔ "Cooper oxide" — which
    share only "oxide" — can no longer out-score "Aluminium Oxide" ↔
    "Alumina" after alias folding.
    """
    if not delivery_tokens or not db_tokens:
        return 0.0

    intersection = delivery_tokens & db_tokens
    if not intersection:
        return 0.0

    inter_w = sum(_token_weight(t) for t in intersection)
    del_w = sum(_token_weight(t) for t in delivery_tokens)
    db_w = sum(_token_weight(t) for t in db_tokens)

    if del_w == 0 or db_w == 0:
        return 0.0

    recall = inter_w / del_w
    precision = inter_w / db_w
    if recall + precision == 0:
        return 0.0

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
    keterangan: str | None = None,
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
    # Also routes when db_sizes wasn't provided — we just match on short_name
    # in that case and skip size-id resolution.
    if supplier_type == "stone":
        return await smart_match_stone_item(
            delivery_name=delivery_name,
            delivery_qty=delivery_qty,
            delivery_unit=delivery_unit,
            db_materials=db_materials,
            db_sizes=db_sizes or [],
            supplier_type=supplier_type,
            keterangan=keterangan,
        )

    logger.debug(
        "Matching delivery item: original=%r, translated=%r, base=%r, tokens=%s, supplier_type=%s",
        delivery_name, translated, base_name, delivery_tokens, supplier_type,
    )

    # ── Filter DB materials by supplier type ──────────────────
    # If we KNOW the supplier delivers stone → only match against stone materials
    # This prevents "Grey Lava" matching "Dark Grey G9484" (a pigment!).
    # Hard filter: when supplier_type is known, NEVER return materials of a
    # different type — even if the type-filtered set is empty (then we fall
    # through to "create new" rather than misclassifying).
    filtered_materials = db_materials
    if supplier_type:
        filtered_materials = [
            m for m in db_materials if m.get("material_type") == supplier_type
        ]
        logger.debug(
            "Supplier type=%s → hard-filtered to %d materials (from %d)",
            supplier_type, len(filtered_materials), len(db_materials),
        )

    # Score filtered DB materials
    scored: list[tuple[float, dict]] = []
    for mat in filtered_materials:
        db_tokens = tokenize_for_matching(mat["name"])

        # Score with both full name and base name (without color), take best
        score_full = calculate_match_score(delivery_tokens, db_tokens)
        score_base = calculate_match_score(base_tokens, db_tokens)
        score = max(score_full, score_base)

        # ── Size match logic ────────────────────────────────────
        # If BOTH names encode a size (e.g. "Grey Lava 5x20" vs "Grey Lava 10x10"),
        # a mismatch is a strong negative signal — different sizes are different
        # materials in the warehouse, even when the base type is identical.
        # Stone-supplier deliveries take the smart_match_stone_item path above
        # (exact canonical match); this block is for the fuzzy fallback where
        # getting sizes wrong causes visible "Grey Lava 30x40x1.2 → Grey Lava 5x20x1.2"
        # false-positives in the bot.
        delivery_sizes_raw = re.findall(r'\d+(?:\.\d+)?x\d+(?:\.\d+)?', normalize_size(delivery_name))
        mat_sizes_raw = re.findall(r'\d+(?:\.\d+)?x\d+(?:\.\d+)?', normalize_size(mat["name"]))
        if delivery_sizes_raw and mat_sizes_raw:
            d_base = delivery_sizes_raw[0]
            db_base = mat_sizes_raw[0]
            if d_base == db_base:
                score += 0.2  # exact size match
            else:
                # Hard cap: when both sides have a size and they differ, ensure
                # score can't clear the threshold on tokens alone. 0.35 keeps the
                # entry visible as a candidate suggestion without auto-matching.
                score = min(score, 0.35)

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

    # ── LLM fallback for ambiguous matches (score 0.2–threshold) ──
    # When fuzzy matching is uncertain, ask AI to decide among top candidates.
    # Skip when supplier_type is known — we already hard-filtered above and the
    # canonical short_name path (smart_match_stone_item) handles stone exhaustively.
    if candidates and best_score >= 0.2 and not supplier_type:
        try:
            from business.services.telegram_ai import ai_match_material
            ai_result = await ai_match_material(
                delivery_name=delivery_name,
                top_candidates=candidates,
                context=f"supplier: {supplier_name}" if supplier_name else "",
            )
            if ai_result and ai_result.get("confidence", 0) >= 0.6:
                logger.info(
                    "AI fallback matched: %r → %r (confidence=%.2f, reason=%s)",
                    delivery_name, ai_result["material_name"],
                    ai_result["confidence"], ai_result.get("reason", ""),
                )
                return {
                    "matched": True,
                    "material_id": ai_result["material_id"],
                    "material_name": ai_result["material_name"],
                    "score": round(ai_result["confidence"], 3),
                    "translated_name": translated,
                    "delivery_name": delivery_name,
                    "quantity": delivery_qty,
                    "unit": translated_unit,
                    "suggested_name": None,
                    "suggested_type": None,
                    "suggested_subtype": None,
                    "candidates": candidates,
                }
        except Exception as e:
            logger.debug("AI material match fallback failed: %s", e)

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

def find_best_match_sync(  # noqa: dead-code — sync wrapper for batch scripts
    delivery_name: str,
    delivery_qty: float,
    delivery_unit: str,
    db_materials: list[dict],
    threshold: float = 0.4,
) -> dict:
    """Synchronous version of find_best_match for non-async callers.

    Currently unused — all callers (delivery router, telegram bot,
    match_delivery_items) are async and call find_best_match directly.
    Kept as a convenience wrapper for potential future sync contexts
    (CLI scripts, management commands, etc.).

    Note: uses deprecated ``get_event_loop().run_until_complete()`` pattern.
    If a sync caller is added, prefer ``asyncio.run()`` instead.
    """
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
        keterangan = item.get("keterangan")
        result = await find_best_match(
            delivery_name=item["name"],
            delivery_qty=item.get("quantity", 0),
            delivery_unit=item.get("unit", "pcs"),
            db_materials=db_materials,
            threshold=threshold,
            supplier_name=supplier_name,
            db_sizes=db_sizes,
            keterangan=keterangan,
        )
        # Carry keterangan (edge profile / shape / design hint) forward so the
        # bot can show it and pre-fill design picker on 3D tiles.
        if keterangan:
            result["keterangan"] = keterangan
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
        "stone", "tile", "ceramic", "sink", "table top", "countertop", "basin",
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

    Uses keyword matching first, then falls back to guess_subtype_from_size()
    when a size pattern (e.g. "5x20", "Ø35") is present in the name but no
    keyword gives a clear answer.

    Returns: "tiles", "sinks", "countertop", "custom", or None.
    """
    lower = translated_name.lower()

    if any(w in lower for w in ("sink", "basin", "wastafel", "bak")):
        return "sinks"
    if any(w in lower for w in ("table", "meja", "counter")):
        return "countertop"
    if any(w in lower for w in ("pot", "vase", "bowl", "plate", "pillar")):
        return "custom"

    # Tiles: stone/tile/ceramic with a size pattern
    if any(w in lower for w in ("tile", "stone", "ceramic")) and re.search(r'\d+x\d+', lower):
        return "tiles"
    # Default for generic stone references
    if any(w in lower for w in ("tile", "stone", "ceramic")):
        return "tiles"

    # Fallback: try to infer subtype from size dimensions in the name
    # e.g. "Lava 5x20" → tiles, "Andesite 60x90" → countertop
    size_match = re.search(r'(\d+(?:\.\d+)?x\d+(?:\.\d+)?|[øØ]\s*\d+(?:\.\d+)?)', lower)
    if size_match:
        return guess_subtype_from_size(size_match.group(0))

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
        product_type: "3d" | "tiles" | "sink" | "countertop" | None
        needs_user_choice: True if ambiguous (user should pick)
    """
    # Step 2a: thickness with range → 3D
    if thickness_raw and re.search(r'[-/]', thickness_raw):
        return "3d", False

    # Step 2b: single thickness → check size rules
    if is_round and diameter is not None:
        if diameter > 40:
            # Large round → auto-assign sink
            return "sink", False
        elif diameter >= 29:
            # Ambiguous range (29-40cm) — could be sink, countertop, or tile
            return None, True
        else:
            return "tiles", False

    if size_raw:
        m = re.match(r'(\d+(?:\.\d+)?)[xX](\d+(?:\.\d+)?)', size_raw)
        if m:
            w, h = float(m.group(1)), float(m.group(2))
            if (w > 40 and h > 40) or (w > 30 and h > 60) or (w > 60 and h > 30):
                # Large rectangle → auto-assign countertop
                return "countertop", False
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
    keterangan: str | None = None,
) -> dict:
    """
    Smart matching for STONE materials using canonical short_name lookup.

    See ``docs/BUSINESS_LOGIC_FULL.md §29``. The algorithm is:

      1. Parse delivery_name via ``material_naming.parse_stone_delivery_name``.
      2. Build canonical ``short_name`` ("Lava Stone {size}").
      3. Look up matching ``Material`` by exact ``short_name`` (filtered to
         ``material_type='stone'``). All color variants of the same size collapse
         to one material — that is the user-stated rule.
      4. Resolve the size in the DB ``Size`` table by mm dimensions.
      5. Return matched / suggested-new with parsed_* fields for the UI.

    No fuzzy scoring. The canonical short_name IS the match key. If callers
    need fuzzy behaviour for non-stone materials they should not route here.
    """
    from business.services import material_naming as nm

    translated = translate_material_name(delivery_name)
    translated_unit = INDO_TO_EN.get(delivery_unit.lower().strip(), delivery_unit)

    # ── Step 1: Parse delivery name via the naming service ────
    parsed_obj = nm.parse_stone_delivery_name(delivery_name)
    color = parsed_obj.color
    base_material = parsed_obj.base
    is_round = parsed_obj.is_round
    diameter_cm = parsed_obj.diameter_mm / 10 if parsed_obj.diameter_mm else None
    thickness_raw = parsed_obj.thickness_raw
    size_raw = None
    if parsed_obj.width_mm and parsed_obj.height_mm:
        size_raw = (
            f"{parsed_obj.width_mm / 10:g}x{parsed_obj.height_mm / 10:g}"
        )

    # Canonical key — used for both lookup and suggestion display
    canonical_short_name = nm.build_short_name(parsed_obj)
    product_type = parsed_obj.typology
    needs_user_choice = parsed_obj.needs_typology_choice
    diameter = diameter_cm  # alias for code below that uses cm-scale values

    # ── Keterangan-driven overrides (from the surat jalan notes column) ──
    # Handwritten keterangan often carries the true typology / shape hint —
    # "wastafel smooth" → sink, "oktagon" → octagon tiles, "triangel" → triangle,
    # "sample" tags a non-standard piece, etc. The size-based auto-detection
    # in material_naming cannot see this text, so apply overrides here.
    parsed_shape = parsed_obj.shape
    keterangan_lc = (keterangan or "").lower()
    if keterangan_lc:
        if any(w in keterangan_lc for w in ("wastafel", "sink", "washbasin")):
            product_type = "sink"
            needs_user_choice = False
        elif "countertop" in keterangan_lc or "table top" in keterangan_lc:
            product_type = "countertop"
            needs_user_choice = False
        elif "sample" in keterangan_lc:
            # Samples are small standalone pieces; treat as tiles but remember
            # they're samples via keterangan (logged downstream).
            if product_type is None:
                product_type = "tiles"
                needs_user_choice = False
        # Shape overrides — keep typology but annotate shape for Size creation.
        if "oktagon" in keterangan_lc or "octagon" in keterangan_lc:
            parsed_shape = "octagon"
        elif "right triangle" in keterangan_lc or "right-triangle" in keterangan_lc \
                or "siku" in keterangan_lc:  # "segitiga siku-siku" = right triangle (id)
            parsed_shape = "right_triangle"
        elif "triangel" in keterangan_lc or "triangle" in keterangan_lc \
                or "segitiga" in keterangan_lc:
            parsed_shape = "triangle"

    logger.debug(
        "smart_match_stone: delivery=%r, parsed=%s",
        delivery_name, parsed_obj,
    )

    # ── Step 2: Resolve size in DB by mm dimensions ──────────
    suggested_size_name: str | None = None
    suggested_size_exists = False
    matched_size_id = None

    if is_round and parsed_obj.diameter_mm is not None:
        for s in db_sizes:
            if s.get("diameter_mm") == parsed_obj.diameter_mm:
                suggested_size_name = s["name"]
                suggested_size_exists = True
                matched_size_id = s["id"]
                break
        if not suggested_size_name:
            d = parsed_obj.diameter_mm / 10
            suggested_size_name = f"Ø{d:g}"
    elif parsed_obj.width_mm and parsed_obj.height_mm:
        w_mm, h_mm = parsed_obj.width_mm, parsed_obj.height_mm
        for s in db_sizes:
            sw = s.get("width_mm", 0)
            sh = s.get("height_mm", 0)
            if (sw == w_mm and sh == h_mm) or (sw == h_mm and sh == w_mm):
                # If thickness is also recorded, prefer an exact thickness match
                if parsed_obj.thickness_mm and s.get("thickness_mm"):
                    if int(s["thickness_mm"]) != parsed_obj.thickness_mm:
                        continue
                suggested_size_name = s["name"]
                suggested_size_exists = True
                matched_size_id = s["id"]
                break
        if not suggested_size_name:
            suggested_size_name = nm.build_size_label(parsed_obj)

    # ── Step 3: Direct lookup by canonical short_name ────────
    # All color variants of the same size collapse here — that is the rule
    # documented in §29. No fuzzy scoring on the stone path.
    stone_materials = [m for m in db_materials if m.get("material_type") == "stone"]
    matched_material = None
    same_base_candidates: list[dict] = []

    target = canonical_short_name.lower().strip()
    for mat in stone_materials:
        mat_short = (mat.get("short_name") or "").lower().strip()
        # Fallback: legacy rows without short_name → normalize their name on the fly
        if not mat_short:
            mat_short = nm.build_short_name_from_raw(mat.get("name") or "").lower().strip()
        if mat_short == target:
            # Don't collapse typologies — same short_name with different
            # product_subtype is a different Material (sink vs tile, etc.).
            # When we know the incoming typology, require it to match.
            mat_subtype = (mat.get("product_subtype") or "").lower()
            if product_type and mat_subtype and mat_subtype != product_type:
                continue
            matched_material = mat
            break
        # Same base + same size_id → list as alternative
        if matched_size_id and mat.get("size_id") == matched_size_id:
            same_base_candidates.append({
                "material_id": mat["id"],
                "material_name": mat.get("short_name") or mat["name"],
                "score": 0.95,
            })

    matched = matched_material is not None
    candidates = (
        [{
            "material_id": matched_material["id"],
            "material_name": matched_material.get("short_name") or matched_material["name"],
            "score": 1.0,
        }]
        if matched
        else same_base_candidates[:3]
    )

    suggestion_context = None
    if not matched and same_base_candidates:
        suggestion_context = "same_base_different_size"
    elif not matched:
        suggestion_context = "new_material"

    result = {
        "matched": matched,
        "material_id": matched_material["id"] if matched else None,
        "material_name": (
            matched_material.get("short_name") or matched_material["name"]
            if matched
            else None
        ),
        "score": 1.0 if matched else 0.0,
        "translated_name": translated,
        "delivery_name": delivery_name,
        "quantity": delivery_qty,
        "unit": translated_unit,
        "suggested_name": canonical_short_name if not matched else None,
        "suggested_short_name": canonical_short_name,
        "suggested_type": "stone",
        "suggested_subtype": product_type,
        "candidates": candidates,
        # Stone-specific extras consumed by the UI
        "suggested_size_name": suggested_size_name,
        "suggested_size_exists": suggested_size_exists,
        "suggested_size_id": matched_size_id,
        "parsed_width_mm": parsed_obj.width_mm,
        "parsed_height_mm": parsed_obj.height_mm,
        "parsed_thickness_mm": parsed_obj.thickness_mm,
        "parsed_thickness_raw": parsed_obj.thickness_raw,
        "parsed_diameter_mm": parsed_obj.diameter_mm,
        "parsed_shape": parsed_shape,
        "suggested_product_type": product_type,
        "needs_user_choice": needs_user_choice,
        "parsed_color": color,
        "parsed_base_material": base_material,
        "suggestion_context": suggestion_context,
        # §29 addendum — 3D tiles of the same size can differ by design
        # (e.g. "Design 1" / "Design 2"). Matcher cannot disambiguate by
        # delivery name alone, so we defer to user choice in the bot/UI.
        "needs_design_choice": product_type == "3d",
    }

    # For 3D items we refuse auto-match: same short_name can map to multiple
    # materials (one per design). Force the bot/UI to present a design picker
    # and then resolve Material via (size_id, '3d', design_id).
    if product_type == "3d":
        result["matched"] = False
        result["material_id"] = None
        result["material_name"] = None
        result["score"] = 0.0

    logger.info(
        "smart_match_stone: %r → matched=%s short_name=%r typology=%s size_exists=%s",
        delivery_name, matched, canonical_short_name,
        product_type, suggested_size_exists,
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
