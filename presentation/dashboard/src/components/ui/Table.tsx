import { cn } from '@/lib/cn';

interface Column<T> { key: string; header: string; render?: (item: T) => React.ReactNode; }
interface TableProps<T> { columns: Column<T>[]; data: T[]; className?: string; onRowClick?: (item: T) => void; }

export function DataTable<T extends Record<string, unknown>>({ columns, data, className, onRowClick }: TableProps<T>) {
  return (
    <div className={cn('overflow-x-auto rounded-lg border border-gray-200', className)}>
      <table className="w-full text-left text-sm">
        <thead className="border-b bg-gray-50 text-xs font-medium uppercase text-gray-500">
          <tr>{columns.map((c) => <th key={c.key} className="px-4 py-3">{c.header}</th>)}</tr>
        </thead>
        <tbody className="divide-y">
          {data.map((item, i) => (
            <tr key={i} className={cn('bg-white', onRowClick && 'cursor-pointer hover:bg-gray-50')} onClick={() => onRowClick?.(item)}>
              {columns.map((c) => <td key={c.key} className="px-4 py-3">{c.render ? c.render(item) : String(item[c.key] ?? '')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
