import { cn } from '@/lib/cn';

export type StoneTypology = 'tiles' | '3d' | 'sink' | 'countertop' | 'freeform';

const OPTIONS: { value: StoneTypology; label: string; icon: string }[] = [
  { value: 'tiles', label: 'Flat tile', icon: '▭' },
  { value: '3d', label: '3D', icon: '◬' },
  { value: 'sink', label: 'Sink', icon: '◯' },
  { value: 'countertop', label: 'Countertop', icon: '▬' },
  { value: 'freeform', label: 'Freeform', icon: '✦' },
];

interface Props {
  value: StoneTypology | null | undefined;
  onChange: (next: StoneTypology) => void;
  size?: 'sm' | 'md';
}

export function TypologySelector({ value, onChange, size = 'md' }: Props) {
  return (
    <div className="flex flex-wrap gap-1">
      {OPTIONS.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            type="button"
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={cn(
              'flex items-center gap-1 rounded-md border transition',
              size === 'sm' ? 'px-2 py-1 text-xs' : 'px-3 py-1.5 text-sm',
              active
                ? 'border-primary-500 bg-primary-50 text-primary-700 dark:border-gold-500 dark:bg-gold-500/10 dark:text-gold-300'
                : 'border-gray-300 text-gray-700 hover:border-gray-400 dark:border-stone-700 dark:text-stone-300 dark:hover:border-stone-500',
            )}
          >
            <span aria-hidden>{opt.icon}</span>
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
