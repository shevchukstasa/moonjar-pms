import type { SizeValue } from './SizeInput';
import type { StoneTypology } from './TypologySelector';

interface Props {
  longName: string;
  size: SizeValue;
  typology?: StoneTypology | null;
}

/**
 * Live preview of canonical short_name. Mirrors the rule in
 * docs/BUSINESS_LOGIC_FULL.md §29: "Lava Stone {size}" for stone.
 *
 * For freeform with no size → "Lava Stone Freeform".
 */
export function NamePreview({ longName, size, typology }: Props) {
  const sizeLabel = buildSizeLabel(size);
  const shortName = sizeLabel ? `Lava Stone ${sizeLabel}` : 'Lava Stone Freeform';

  return (
    <div className="flex flex-col gap-0.5 text-xs">
      <div className="text-gray-500 dark:text-stone-500">
        Long: <span className="text-gray-700 dark:text-stone-300">{longName || '—'}</span>
      </div>
      <div className="font-medium text-primary-700 dark:text-gold-300">
        Short: {shortName}
        {typology && <span className="ml-2 text-gray-400">({typology})</span>}
      </div>
    </div>
  );
}

function buildSizeLabel(s: SizeValue): string | null {
  const t = s.thickness_raw || (s.thickness_mm ? String(s.thickness_mm / 10) : '');
  if (s.shape === 'round' && s.diameter_mm) {
    const d = s.diameter_mm / 10;
    return t ? `Ø${d}×${t}` : `Ø${d}`;
  }
  if (s.width_mm && s.height_mm) {
    const w = s.width_mm / 10;
    const h = s.height_mm / 10;
    return t ? `${w}×${h}×${t}` : `${w}×${h}`;
  }
  return null;
}
