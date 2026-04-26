"""
Single source of truth for size-string normalisation.

Sizes get typed in many places — order intake, AdminSizesPage,
delivery scans (OCR), Telegram bot, manual edit. Each typist drops
their own variants:

    "5×21,5"   "5x21.5"   "5 x 21.5"   "5х21.5"   "5X21,5"

Without normalisation, `_check_stone_stock_and_create_task` and
friends compare "5x21,5" (position) against "5x21.5" (catalog) byte
by byte and conclude no match → silent stone shortage.

`normalize_size_str()` flattens every variant to ONE canonical form:
    lowercase, no spaces, ASCII `x`, decimal point.

Apply this anywhere two sizes are compared OR before persistence so
the catalog stays clean. See BUSINESS_LOGIC_FULL.md §29.
"""

from __future__ import annotations


_X_SUBSTITUTES = {
    "х",  # cyrillic ha
    "Х",  # cyrillic capital ha
    "×",  # unicode multiplication sign
    "✕",  # heavy multiplication x
    "✕",  # multiplication X (same as ✕, kept for clarity)
    "×",  # MULTIPLICATION SIGN — same as ×
    "*",  # arithmetic asterisk sometimes typed
}


def normalize_size_str(s: str | None) -> str:
    """Canonicalise a size string for comparison or storage.

    Rules (in order):
      1. None / empty                     → ''
      2. lowercase + strip outer whitespace
      3. comma → dot (decimal separator unification)
      4. all "×" / "х" / "✕" / "*" → "x"
      5. remove every internal whitespace

    Examples:
      "5×21,5"      → "5x21.5"
      " 5 x 21.5 "  → "5x21.5"
      "5х21,5"      → "5x21.5"   (cyrillic ha)
      "10 X 10"     → "10x10"
      None / ""     → ""
    """
    if not s:
        return ""
    out = str(s).strip().lower()
    out = out.replace(",", ".")
    for ch in _X_SUBSTITUTES:
        if ch in out:
            out = out.replace(ch, "x")
    out = "".join(out.split())  # remove all whitespace
    return out
