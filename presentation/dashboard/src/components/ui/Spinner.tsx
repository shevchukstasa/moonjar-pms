import { cn } from '@/lib/cn';
export function Spinner({ className }: { className?: string }) {
  return <div className={cn('h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-primary-500 dark:border-stone-700 dark:border-t-gold-500', className)} />;
}
