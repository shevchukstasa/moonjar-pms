import { cn } from '@/lib/cn';
export function Tooltip({ children, text, className }: { children: React.ReactNode; text: string; className?: string }) {
  return <div className={cn('group relative inline-block', className)}>{children}<div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 rounded bg-gray-900 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">{text}</div></div>;
}
