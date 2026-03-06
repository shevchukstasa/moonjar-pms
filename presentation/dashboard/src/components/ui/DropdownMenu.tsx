import { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/cn';

export function DropdownMenu({ trigger, items, className }: { trigger: React.ReactNode; items: { label: string; onClick: () => void }[]; className?: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); }; document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h); }, []);
  return <div ref={ref} className={cn('relative inline-block', className)}><div onClick={() => setOpen(!open)}>{trigger}</div>{open && <div className="absolute right-0 z-50 mt-1 min-w-[160px] rounded-md border bg-white py-1 shadow-lg">{items.map((item, i) => <button key={i} onClick={() => { item.onClick(); setOpen(false); }} className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100">{item.label}</button>)}</div>}</div>;
}
