import { InputHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';
export function SearchInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input type="search" placeholder="Search..." className={cn('rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100 dark:placeholder-stone-500 dark:focus:border-gold-500', className)} {...props} />;
}
