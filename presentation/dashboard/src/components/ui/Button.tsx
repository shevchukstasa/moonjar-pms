import { ButtonHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/cn';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => (
    <button ref={ref} className={cn(
      'inline-flex items-center justify-center rounded-md font-medium transition-colors disabled:opacity-50',
      variant === 'primary' && 'bg-primary-500 text-white hover:bg-primary-600',
      variant === 'secondary' && 'bg-gray-200 text-gray-800 hover:bg-gray-300',
      variant === 'danger' && 'bg-red-500 text-white hover:bg-red-600',
      variant === 'ghost' && 'text-gray-600 hover:bg-gray-100',
      size === 'sm' && 'px-3 py-1.5 text-sm', size === 'md' && 'px-4 py-2 text-sm', size === 'lg' && 'px-6 py-3 text-base',
      className,
    )} {...props} />
  ),
);
Button.displayName = 'Button';
