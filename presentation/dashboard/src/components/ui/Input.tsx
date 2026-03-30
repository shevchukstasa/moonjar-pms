import { InputHTMLAttributes, forwardRef, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> { label?: ReactNode; error?: string; }

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, ...props }, ref) => (
    <div className="w-full">
      {label && <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">{label}</label>}
      <input ref={ref} className={cn('w-full rounded-md border px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:bg-stone-900 dark:text-stone-100 dark:placeholder-stone-500 dark:focus:border-gold-500 dark:focus:ring-gold-500', error ? 'border-red-500' : 'border-gray-300 dark:border-stone-700', className)} {...props} />
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  ),
);
Input.displayName = 'Input';
