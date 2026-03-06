import { useEffect, useRef } from 'react';
import { cn } from '@/lib/cn';

export function Dialog({ open, onClose, title, children, className }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (open) ref.current?.showModal(); else ref.current?.close(); }, [open]);
  return (
    <dialog ref={ref} onClose={onClose} className={cn('rounded-xl border-0 p-0 shadow-xl backdrop:bg-black/50', className)}>
      <div className="p-6">
        <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold">{title}</h2><button onClick={onClose} className="text-gray-400 hover:text-gray-600">&times;</button></div>
        {children}
      </div>
    </dialog>
  );
}
