import { forwardRef, type InputHTMLAttributes, type ChangeEvent } from 'react';
import { cn } from '@/lib/cn';

interface NumericInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> {
  label?: string;
  error?: string;
  /** Called with the sanitised value (commas → dots) */
  onChange?: (e: ChangeEvent<HTMLInputElement>) => void;
}

/**
 * A numeric text input that accepts both dot and comma as decimal separator.
 * Uses `inputMode="decimal"` so mobile keyboards show a numeric pad.
 */
export const NumericInput = forwardRef<HTMLInputElement, NumericInputProps>(
  ({ className, label, error, onChange, ...props }, ref) => {
    const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
      // Replace comma with dot so the stored value is always dot-separated
      const raw = e.target.value.replace(',', '.');
      // Allow empty, leading minus, partial input like "3." or ".5"
      if (raw === '' || raw === '-' || raw === '.' || raw === '-.' || /^-?\d*\.?\d*$/.test(raw)) {
        // Mutate the synthetic event value so callers get the normalised string
        const synth = { ...e, target: { ...e.target, value: raw } } as ChangeEvent<HTMLInputElement>;
        onChange?.(synth);
      }
    };

    return (
      <div className="w-full">
        {label && <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">{label}</label>}
        <input
          ref={ref}
          type="text"
          inputMode="decimal"
          className={cn(
            'w-full rounded-md border px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:bg-stone-900 dark:text-stone-100 dark:placeholder-stone-500 dark:focus:border-gold-500 dark:focus:ring-gold-500',
            error ? 'border-red-500' : 'border-gray-300 dark:border-stone-700',
            className,
          )}
          onChange={handleChange}
          {...props}
        />
        {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
      </div>
    );
  },
);
NumericInput.displayName = 'NumericInput';
