import { HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

const cardVariants = {
  default: 'bg-white dark:bg-[var(--bg-card)] border border-gray-200 dark:border-[var(--border)] dark:backdrop-blur-sm',
  glass: 'bg-white/70 dark:bg-stone-900/40 backdrop-blur-xl border border-white/20 dark:border-white/10 shadow-lg',
  flat: 'bg-gray-50 dark:bg-stone-800',
} as const;

type CardVariant = keyof typeof cardVariants;

export function Card({ className, title, variant = 'default', children, ...props }: HTMLAttributes<HTMLDivElement> & { title?: string; variant?: CardVariant }) {
  return (
    <div className={cn('rounded-lg p-4 shadow-sm', cardVariants[variant], className)} {...props}>
      {title && <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">{title}</h3>}
      {children}
    </div>
  );
}
