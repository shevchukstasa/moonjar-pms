import { ButtonHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/cn';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'gold';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => (
    <button ref={ref} className={cn(
      'inline-flex items-center justify-center rounded-md font-medium transition-all duration-200 active:scale-[0.98] disabled:opacity-50',
      variant === 'primary' && 'bg-primary-500 text-white hover:bg-primary-600 hover:shadow-md dark:bg-gold-500 dark:text-stone-950 dark:hover:bg-gold-400',
      variant === 'secondary' && 'bg-gray-200 text-gray-800 hover:bg-gray-300 hover:shadow-sm dark:bg-stone-800 dark:text-stone-200 dark:hover:bg-stone-700',
      variant === 'danger' && 'bg-red-500 text-white hover:bg-red-600 hover:shadow-md dark:bg-red-600 dark:hover:bg-red-500',
      variant === 'ghost' && 'text-gray-600 hover:bg-gray-100 dark:text-stone-400 dark:hover:bg-stone-800',
      variant === 'gold' && 'bg-gradient-to-r from-amber-500 to-amber-600 text-white hover:from-amber-600 hover:to-amber-700 hover:shadow-md dark:from-gold-500 dark:to-gold-600 dark:text-stone-950 dark:hover:from-gold-400 dark:hover:to-gold-500',
      size === 'sm' && 'px-3 py-1.5 text-sm', size === 'md' && 'px-4 py-2 text-sm', size === 'lg' && 'px-6 py-3 text-base',
      className,
    )} {...props} />
  ),
);
Button.displayName = 'Button';
