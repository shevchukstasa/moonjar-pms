import { HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export function Card({ className, title, children, ...props }: HTMLAttributes<HTMLDivElement> & { title?: string }) {
  return (
    <div className={cn('rounded-lg border border-gray-200 bg-white p-4 shadow-sm', className)} {...props}>
      {title && <h3 className="mb-3 text-sm font-semibold text-gray-900">{title}</h3>}
      {children}
    </div>
  );
}
