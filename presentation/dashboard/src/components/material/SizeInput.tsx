import { cn } from '@/lib/cn';
import type { StoneTypology } from './TypologySelector';

export interface SizeValue {
  shape: 'rectangle' | 'round';
  width_mm?: number | null;
  height_mm?: number | null;
  thickness_mm?: number | null;
  diameter_mm?: number | null;
  thickness_raw?: string | null;  // e.g. "1-2" preserved as text for 3D items
}

interface Props {
  value: SizeValue;
  onChange: (next: SizeValue) => void;
  typology?: StoneTypology | null;
  /** When true, renders compact inputs suitable for inline table editing. */
  compact?: boolean;
}

const ROUND_BY_DEFAULT: StoneTypology[] = ['sink'];

export function SizeInput({ value, onChange, typology, compact = true }: Props) {
  const inputClass = cn(
    'w-full rounded border border-gray-300 bg-white px-2 text-right tabular-nums dark:border-stone-700 dark:bg-stone-900 dark:text-stone-200',
    compact ? 'py-1 text-sm' : 'py-1.5 text-base',
  );
  const labelClass = 'block text-[10px] uppercase tracking-wide text-gray-500 dark:text-stone-500';

  // Allow user to flip shape when ambiguous
  const isRound = value.shape === 'round' || ROUND_BY_DEFAULT.includes(typology ?? 'tiles');

  return (
    <div className="flex flex-wrap items-end gap-2">
      {!isRound ? (
        <>
          <div className="w-16">
            <label className={labelClass}>W cm</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={value.width_mm ? value.width_mm / 10 : ''}
              onChange={(e) =>
                onChange({
                  ...value,
                  width_mm: e.target.value ? Math.round(parseFloat(e.target.value) * 10) : null,
                })
              }
              className={inputClass}
            />
          </div>
          <div className="w-16">
            <label className={labelClass}>H cm</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={value.height_mm ? value.height_mm / 10 : ''}
              onChange={(e) =>
                onChange({
                  ...value,
                  height_mm: e.target.value ? Math.round(parseFloat(e.target.value) * 10) : null,
                })
              }
              className={inputClass}
            />
          </div>
        </>
      ) : (
        <div className="w-20">
          <label className={labelClass}>Ø cm</label>
          <input
            type="number"
            step="0.1"
            min="0"
            value={value.diameter_mm ? value.diameter_mm / 10 : ''}
            onChange={(e) =>
              onChange({
                ...value,
                diameter_mm: e.target.value ? Math.round(parseFloat(e.target.value) * 10) : null,
              })
            }
            className={inputClass}
          />
        </div>
      )}
      <div className="w-20">
        <label className={labelClass}>T cm</label>
        <input
          type="text"
          inputMode="decimal"
          placeholder="1.2 / 1-2"
          value={value.thickness_raw ?? (value.thickness_mm ? String(value.thickness_mm / 10) : '')}
          onChange={(e) => {
            const raw = e.target.value;
            const isRange = /[/\-]/.test(raw);
            if (isRange) {
              onChange({ ...value, thickness_raw: raw, thickness_mm: null });
            } else if (raw === '') {
              onChange({ ...value, thickness_raw: null, thickness_mm: null });
            } else {
              const v = parseFloat(raw);
              onChange({
                ...value,
                thickness_raw: raw,
                thickness_mm: Number.isFinite(v) ? Math.round(v * 10) : null,
              });
            }
          }}
          className={inputClass}
        />
      </div>
      {typology !== 'sink' && (
        <button
          type="button"
          onClick={() => onChange({ ...value, shape: isRound ? 'rectangle' : 'round' })}
          className="text-xs text-gray-500 underline-offset-2 hover:underline dark:text-stone-400"
          title="Toggle round/rectangular"
        >
          {isRound ? 'use W×H' : 'use Ø'}
        </button>
      )}
    </div>
  );
}
