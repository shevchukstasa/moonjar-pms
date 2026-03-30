import { cn } from '@/lib/cn';
import { useState } from 'react';

interface Column<T> { key: string; header: string; render?: (item: T) => React.ReactNode; }
interface TableProps<T> { columns: Column<T>[]; data: T[]; className?: string; onRowClick?: (item: T) => void; selectedIndex?: number; }

export function DataTable<T extends Record<string, unknown>>({ columns, data, className, onRowClick, selectedIndex }: TableProps<T>) {
  const [hoveredRow, setHoveredRow] = useState<number | null>(null);
  return (
    <div className={cn('overflow-x-auto rounded-lg border border-gray-200/80 dark:border-stone-700/50', className)}>
      <table className="w-full text-left text-sm">
        <thead className="border-b border-gray-200/60 dark:border-stone-700/50 bg-stone-800 dark:bg-stone-900/80 text-xs font-medium uppercase tracking-wider text-amber-100/80 dark:text-amber-200/60">
          <tr>{columns.map((c) => <th key={c.key} className="px-4 py-3">{c.header}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-stone-800/60">
          {data.map((item, i) => (
            <tr
              key={i}
              className={cn(
                'transition-colors duration-150',
                'bg-white dark:bg-transparent',
                onRowClick && 'cursor-pointer',
                hoveredRow === i && 'bg-stone-50 dark:bg-stone-800/40',
                selectedIndex === i && 'bg-amber-50/60 dark:bg-amber-900/20 border-l-2 border-l-amber-400',
              )}
              onClick={() => onRowClick?.(item)}
              onMouseEnter={() => setHoveredRow(i)}
              onMouseLeave={() => setHoveredRow(null)}
            >
              {columns.map((c) => <td key={c.key} className="px-4 py-3 text-gray-700 dark:text-stone-200">{c.render ? c.render(item) : String(item[c.key] ?? '')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
