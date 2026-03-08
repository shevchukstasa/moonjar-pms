import { cn } from '@/lib/cn';

type Period = 'week' | 'month' | 'quarter' | 'year';

interface PeriodSelectorProps {
  value: Period;
  onChange: (period: Period) => void;
  className?: string;
}

const periods: { label: string; value: Period }[] = [
  { label: 'Week', value: 'week' },
  { label: 'Month', value: 'month' },
  { label: 'Quarter', value: 'quarter' },
  { label: 'Year', value: 'year' },
];

export function PeriodSelector({ value, onChange, className }: PeriodSelectorProps) {
  return (
    <div className={cn('flex gap-1 rounded-lg bg-gray-100 p-1', className)}>
      {periods.map((p) => (
        <button
          key={p.value}
          onClick={() => onChange(p.value)}
          className={cn(
            'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
            value === p.value
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700',
          )}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

export function periodToDateRange(period: Period): { date_from: string; date_to: string } {
  const today = new Date();
  const to = today.toISOString().split('T')[0];
  let from: Date;

  switch (period) {
    case 'week':
      from = new Date(today);
      from.setDate(from.getDate() - 7);
      break;
    case 'month':
      from = new Date(today);
      from.setMonth(from.getMonth() - 1);
      break;
    case 'quarter':
      from = new Date(today);
      from.setMonth(from.getMonth() - 3);
      break;
    case 'year':
      from = new Date(today);
      from.setFullYear(from.getFullYear() - 1);
      break;
  }

  return { date_from: from.toISOString().split('T')[0], date_to: to };
}
