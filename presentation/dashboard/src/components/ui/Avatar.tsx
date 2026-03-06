import { cn } from '@/lib/cn';
export function Avatar({ name, className }: { name: string; className?: string }) {
  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  return <div className={cn('flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-xs font-medium text-primary-700', className)}>{initials}</div>;
}
