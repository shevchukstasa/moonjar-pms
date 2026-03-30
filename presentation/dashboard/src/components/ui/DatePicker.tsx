import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

interface DatePickerProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> {
  value?: string;
  onChange?: (value: string) => void;
}

export const DatePicker = forwardRef<HTMLInputElement, DatePickerProps>(
  ({ value, onChange, className, ...props }, ref) => (
    <input
      ref={ref}
      type="date"
      value={value || ''}
      onChange={(e) => onChange?.(e.target.value)}
      className={cn('rounded-md border border-gray-300 px-3 py-2 text-sm', className)}
      {...props}
    />
  ),
);
DatePicker.displayName = 'DatePicker';
