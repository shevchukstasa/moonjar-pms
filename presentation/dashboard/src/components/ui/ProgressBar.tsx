import { cn } from '@/lib/cn';
export function ProgressBar({ value, max = 100, className }: { value: number; max?: number; className?: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return <div className={cn('h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-stone-800', className)}><div className="h-full rounded-full bg-primary-500 transition-all dark:bg-gold-500" style={{ width: `${pct}%` }} /></div>;
}
