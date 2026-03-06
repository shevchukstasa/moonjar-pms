import { InputHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';
export function SearchInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input type="search" placeholder="Search..." className={cn('rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none', className)} {...props} />;
}
