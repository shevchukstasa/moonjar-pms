import type { CriticalPosition } from '@/api/analytics';
import { cn } from '@/lib/cn';
import { AlertTriangle, Clock } from 'lucide-react';

interface CriticalPositionsTableProps {
  positions: CriticalPosition[];
}

const statusLabels: Record<string, string> = {
  insufficient_materials: 'No Materials',
  awaiting_recipe: 'Awaiting Recipe',
  awaiting_stencil_silkscreen: 'Awaiting Stencil',
  awaiting_color_matching: 'Color Matching',
  blocked_by_qm: 'Blocked by QM',
  planned: 'Planned',
};

export function CriticalPositionsTable({ positions }: CriticalPositionsTableProps) {
  if (!positions.length) {
    return (
      <div className="py-8 text-center text-sm text-gray-500">
        <AlertTriangle className="mx-auto mb-2 h-8 w-8 text-green-400" />
        No critical positions
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-3 py-2 text-left font-medium text-gray-500">Order</th>
            <th className="px-3 py-2 text-left font-medium text-gray-500">Color / Size</th>
            <th className="px-3 py-2 text-right font-medium text-gray-500">Qty</th>
            <th className="px-3 py-2 text-left font-medium text-gray-500">Status</th>
            <th className="px-3 py-2 text-left font-medium text-gray-500">Deadline</th>
            <th className="px-3 py-2 text-right font-medium text-gray-500">Delay</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {positions.slice(0, 20).map((p) => {
            const isOverdue = p.deadline && new Date(p.deadline) < new Date();
            return (
              <tr key={p.position_id} className={cn('hover:bg-gray-50', isOverdue && 'bg-red-50')}>
                <td className="px-3 py-2 font-medium text-gray-900">{p.order_number || '—'}</td>
                <td className="px-3 py-2 text-gray-600">{p.color} / {p.size}</td>
                <td className="px-3 py-2 text-right text-gray-900">{p.quantity}</td>
                <td className="px-3 py-2">
                  <span className="inline-flex items-center rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-800">
                    {statusLabels[p.status] || p.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-gray-600">
                  {p.deadline ? (
                    <span className={cn(isOverdue && 'font-semibold text-red-600')}>
                      {p.deadline}
                    </span>
                  ) : '—'}
                </td>
                <td className="px-3 py-2 text-right">
                  {p.delay_hours > 0 && (
                    <span className="inline-flex items-center gap-0.5 text-red-600">
                      <Clock className="h-3 w-3" />
                      {p.delay_hours}h
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
