/**
 * TypeScript port of `business/services/material_naming.py` — the canonical
 * naming rules documented in `docs/BUSINESS_LOGIC_FULL.md §29`.
 *
 * Used by admin/PM/purchaser dialogs to auto-fill `short_name` from the raw
 * delivery-note name as the user types it. Keep the regex and color/provenance
 * word lists in sync with the Python source of truth.
 */

const STRIP_COLOR_WORDS = new Set([
  // English colors
  'grey', 'gray', 'black', 'white', 'red', 'green', 'blue',
  'brown', 'dark', 'light', 'cream', 'beige', 'pink', 'yellow',
  // Indonesian colors
  'abu', 'abu-abu', 'hitam', 'putih', 'merah', 'hijau', 'biru',
  'coklat', 'gelap', 'terang', 'kuning', 'krem',
  // Provenance words (also stripped)
  'bali', 'java', 'lombok',
]);

// Rect sizes: "5x20", "5×20", "5/20"; optional third dimension (thickness).
const RECT_RE = /(\d+(?:[.,]\d+)?)\s*[/xX×]\s*(\d+(?:[.,]\d+)?)(?:\s*[/xX×]\s*(\d+(?:[.,/\-]\d+)?))?/;
// Round: "Ø29", "dia30"
const DIA_RE = /[øØ]\s*(\d+(?:\.\d+)?)|dia\w*\s*(\d+(?:\.\d+)?)/i;

export interface ParsedStoneName {
  color: string | null;
  widthCm: number | null;
  heightCm: number | null;
  thicknessRaw: string | null;   // e.g. "1.2" or "1-2"
  diameterCm: number | null;
  isRound: boolean;
}

function normalizeUnicodeX(text: string): string {
  return text.replace(/×/g, 'x');
}

function stripColorWords(name: string): { color: string | null; rest: string } {
  const words = name.split(/\s+/);
  const color: string[] = [];
  const rest: string[] = [];
  let seenNonColor = false;
  for (const w of words) {
    if (!seenNonColor && STRIP_COLOR_WORDS.has(w.toLowerCase())) {
      color.push(w);
    } else {
      seenNonColor = true;
      rest.push(w);
    }
  }
  return {
    color: color.length ? color.map(c => c[0].toUpperCase() + c.slice(1).toLowerCase()).join(' ') : null,
    rest: rest.join(' '),
  };
}

export function parseStoneDeliveryName(raw: string): ParsedStoneName {
  const text = normalizeUnicodeX((raw || '').trim());
  const { color, rest } = stripColorWords(text);

  let widthCm: number | null = null;
  let heightCm: number | null = null;
  let thicknessRaw: string | null = null;
  let diameterCm: number | null = null;
  let isRound = false;

  const diaMatch = DIA_RE.exec(rest);
  if (diaMatch) {
    isRound = true;
    diameterCm = parseFloat(diaMatch[1] || diaMatch[2]);
    const after = rest.slice(diaMatch.index + diaMatch[0].length);
    const tm = /\s*[xX]\s*(\d+(?:[.,/\-]\d+)?)/.exec(after);
    if (tm) thicknessRaw = tm[1].replace(',', '.');
  } else {
    const rm = RECT_RE.exec(rest);
    if (rm) {
      widthCm = parseFloat(rm[1].replace(',', '.'));
      heightCm = parseFloat(rm[2].replace(',', '.'));
      if (rm[3]) thicknessRaw = rm[3].replace(',', '.');
    }
  }

  return { color, widthCm, heightCm, thicknessRaw, diameterCm, isRound };
}

/** Format size label for short_name: "5×20×1.2" or "Ø35×3" or "". */
export function buildSizeLabel(parsed: ParsedStoneName): string {
  const t = parsed.thicknessRaw ? `×${parsed.thicknessRaw}` : '';
  if (parsed.isRound && parsed.diameterCm != null) {
    return `Ø${formatNum(parsed.diameterCm)}${t}`;
  }
  if (parsed.widthCm != null && parsed.heightCm != null) {
    return `${formatNum(parsed.widthCm)}×${formatNum(parsed.heightCm)}${t}`;
  }
  return '';
}

function formatNum(n: number): string {
  // Avoid trailing zeros: 5 → "5", 5.5 → "5.5"
  return (Math.round(n * 10) / 10).toString();
}

/**
 * Build canonical short_name for a stone from its long delivery-note name.
 * Returns "Lava Stone {size}" or "Lava Stone Freeform" when no size is found.
 */
export function buildStoneShortName(rawName: string): string {
  const parsed = parseStoneDeliveryName(rawName);
  const label = buildSizeLabel(parsed);
  return label ? `Lava Stone ${label}` : 'Lava Stone Freeform';
}
