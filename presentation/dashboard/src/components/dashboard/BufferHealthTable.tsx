import type { BufferHealthItem } from '@/api/analytics';
import { cn } from '@/lib/cn';

interface BufferHealthTableProps {
  items: BufferHealthItem[];
}

const healthColors = {
  green: 'bg-green-100 text-green-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  red: 'bg-red-100 text-red-800',
};

export function BufferHealthTable({ items }: BufferHealthTableProps) {
  if (!items.length) {
    return <p className="text-sm text-gray-500">No buffer health data</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-4 py-2 text-left font-medium text-gray-500">Kiln</th>
            {items[0]?.factory_name !== undefined && (
              <th className="px-4 py-2 text-left font-medium text-gray-500">Factory</th>
            )}
            <th className="px-4 py-2 text-left font-medium text-gray-500">Health</th>
            <th className="px-4 py-2 text-right font-medium text-gray-500">Hours</th>
            <th className="px-4 py-2 text-right font-medium text-gray-500">Target</th>
            <th className="px-4 py-2 text-right font-medium text-gray-500">Positions</th>
            <th className="px-4 py-2 text-right font-medium text-gray-500">SQM</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {items.map((item) => (
            <tr key={item.kiln_id} className="hover:bg-gray-50">
              <td className="px-4 py-2 font-medium text-gray-900">{item.kiln_name}</td>
              {item.factory_name !== undefined && (
                <td className="px-4 py-2 text-gray-600">{item.factory_name}</td>
              )}
              <td className="px-4 py-2">
                <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-semibold', healthColors[item.health])}>
                  {item.health.toUpperCase()}
                </span>
              </td>
              <td className="px-4 py-2 text-right text-gray-900">{item.hours}h</td>
              <td className="px-4 py-2 text-right text-gray-500">{item.target}h</td>
              <td className="px-4 py-2 text-right text-gray-900">{item.buffered_count}</td>
              <td className="px-4 py-2 text-right text-gray-900">{item.buffered_sqm.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
