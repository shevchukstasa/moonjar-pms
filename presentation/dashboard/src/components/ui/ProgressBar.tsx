import { cn } from '@/lib/cn';
export function ProgressBar({ value, max = 100, className }: { value: number; max?: number; className?: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return <div className={cn('h-2 w-full overflow-hidden rounded-full bg-gray-200', className)}><div className="h-full rounded-full bg-primary-500 transition-all" style={{ width: `${pct}%` }} /></div>;
}
