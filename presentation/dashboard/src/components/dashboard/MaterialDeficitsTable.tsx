import type { DeficitItem } from '@/api/analytics';
import { AlertTriangle } from 'lucide-react';

interface MaterialDeficitsTableProps {
  items: DeficitItem[];
}

export function MaterialDeficitsTable({ items }: MaterialDeficitsTableProps) {
  if (!items.length) {
    return (
      <div className="py-8 text-center text-sm text-gray-500">
        All materials above minimum balance
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-4 py-2 text-left font-medium text-gray-500">Material</th>
            <th className="px-4 py-2 text-left font-medium text-gray-500">Type</th>
            <th className="px-4 py-2 text-right font-medium text-gray-500">Balance</th>
            <th className="px-4 py-2 text-right font-medium text-gray-500">Min</th>
            <th className="px-4 py-2 text-right font-medium text-gray-500">Deficit</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {items.map((item) => (
            <tr key={item.material_id} className="hover:bg-gray-50">
              <td className="px-4 py-2">
                <div className="flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                  <span className="font-medium text-gray-900">{item.name}</span>
                </div>
              </td>
              <td className="px-4 py-2 text-gray-600 capitalize">{item.material_type}</td>
              <td className="px-4 py-2 text-right text-gray-900">{item.balance} {item.unit}</td>
              <td className="px-4 py-2 text-right text-gray-500">{item.min_balance} {item.unit}</td>
              <td className="px-4 py-2 text-right font-semibold text-red-600">-{item.deficit.toFixed(1)} {item.unit}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
