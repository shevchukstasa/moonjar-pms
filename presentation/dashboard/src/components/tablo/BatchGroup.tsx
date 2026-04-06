import { Badge } from '@/components/ui/Badge';
import { useTabloStore } from '@/stores/tabloStore';
import type { PositionItem } from './PositionRow';
import { formatPlaceOfApplication, formatEdgeProfile, formatShape } from './PositionRow';

interface BatchInfo {
  id: string;
  batch_date: string | null;
  resource_name: string;
  status: string;
  total_pcs: number;
  positions_count: number;
}

interface Props {
  batch: BatchInfo;
  positions: PositionItem[];
}

export function BatchGroup({ batch, positions }: Props) {
  const { expandedBatches, toggleBatch } = useTabloStore();
  const isExpanded = expandedBatches.has(batch.id);

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* Batch header */}
      <button
        onClick={() => toggleBatch(batch.id)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm">{isExpanded ? '▼' : '▶'}</span>
          <span className="text-sm font-medium text-gray-900">{batch.resource_name}</span>
          <span className="text-xs text-gray-500">{batch.batch_date || 'No date'}</span>
          <Badge status={batch.status} />
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>{batch.positions_count} positions</span>
          <span>{batch.total_pcs} pcs</span>
        </div>
      </button>

      {/* Expanded positions */}
      {isExpanded && positions.length > 0 && (
        <div className="border-t">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-xs font-medium uppercase text-gray-500">
              <tr>
                <th className="px-4 py-2">Order</th>
                <th className="px-4 py-2">Color</th>
                <th className="px-4 py-2">Size</th>
                <th className="px-4 py-2">Thickness</th>
                <th className="px-4 py-2">Shape</th>
                <th className="px-4 py-2">Glaze Place</th>
                <th className="px-4 py-2">Edge</th>
                <th className="px-4 py-2 text-right">Qty</th>
                <th className="px-4 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {positions.map((p) => (
                <tr key={p.id} className="bg-white">
                  <td className="px-4 py-2 text-sm">{p.order_number}</td>
                  <td className="px-4 py-2 text-sm">{p.color}</td>
                  <td className="px-4 py-2 text-sm">{p.size}</td>
                  <td className="px-4 py-2 text-sm">{p.thickness_mm ? `${p.thickness_mm} mm` : '10 mm'}</td>
                  <td className="px-4 py-2 text-sm">{formatShape(p.shape, p.width_cm, p.length_cm)}</td>
                  <td className="px-4 py-2 text-sm">{formatPlaceOfApplication(p.place_of_application)}</td>
                  <td className="px-4 py-2 text-sm">
                    {(() => {
                      const edge = formatEdgeProfile(p.edge_profile, p.edge_profile_sides);
                      const isNonDefault = p.edge_profile && p.edge_profile !== 'straight';
                      return isNonDefault ? (
                        <span className="inline-flex items-center rounded bg-orange-50 px-1.5 py-0.5 text-[10px] font-medium text-orange-700">
                          {edge}
                        </span>
                      ) : edge;
                    })()}
                  </td>
                  <td className="px-4 py-2 text-right text-sm">{p.quantity}</td>
                  <td className="px-4 py-2"><Badge status={p.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {isExpanded && positions.length === 0 && (
        <div className="border-t px-4 py-3 text-sm text-gray-400">No positions in this batch</div>
      )}
    </div>
  );
}
