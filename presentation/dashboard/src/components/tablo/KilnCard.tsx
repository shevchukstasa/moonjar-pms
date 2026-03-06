import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { useTabloStore } from '@/stores/tabloStore';
import { KilnLevelView } from './KilnLevelView';

interface KilnResource {
  id: string;
  name: string;
  resource_type: string;
  status: string;
  capacity_sqm: number | null;
  capacity_pcs: number | null;
  num_levels: number | null;
  kiln_type: string | null;
}

interface BatchItem {
  id: string;
  batch_date: string | null;
  status: string;
  positions_count: number;
  total_pcs: number;
  notes: string | null;
  positions?: Array<{
    id: string;
    order_number: string;
    color: string;
    size: string;
    quantity: number;
    status: string;
    product_type: string;
    placement_level?: number | null;
  }>;
}

interface Props {
  kiln: KilnResource;
  batches: BatchItem[];
}

export function KilnCard({ kiln, batches }: Props) {
  const { expandedBatches, toggleBatch } = useTabloStore();

  return (
    <Card className="space-y-3">
      {/* Kiln header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg">🔥</span>
          <h3 className="font-semibold text-gray-900">{kiln.name}</h3>
          <Badge status={kiln.status} />
          {kiln.kiln_type && (
            <span className="text-xs text-gray-500">{kiln.kiln_type}</span>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm text-gray-500">
          {kiln.capacity_sqm && <span>Cap: {kiln.capacity_sqm} m&sup2;</span>}
          {kiln.num_levels && <span>Levels: {kiln.num_levels}</span>}
          <span className="font-medium">{batches.length} batch{batches.length !== 1 ? 'es' : ''}</span>
        </div>
      </div>

      {/* Batches */}
      {batches.length > 0 ? (
        <div className="space-y-2">
          {batches.map((b) => {
            const isExpanded = expandedBatches.has(b.id);
            return (
              <div key={b.id} className="rounded-lg border border-gray-200">
                <button
                  onClick={() => toggleBatch(b.id)}
                  className="flex w-full items-center justify-between px-4 py-2 text-left hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-400">{isExpanded ? '\u25BC' : '\u25B6'}</span>
                    <span className="text-sm text-gray-700">{b.batch_date || 'No date'}</span>
                    <Badge status={b.status} />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span>{b.positions_count} pos</span>
                    <span>{b.total_pcs} pcs</span>
                    {b.notes && <span className="italic">{b.notes}</span>}
                  </div>
                </button>

                {isExpanded && b.positions && b.positions.length > 0 && (
                  <div className="border-t">
                    <KilnLevelView positions={b.positions} />
                  </div>
                )}

                {isExpanded && (!b.positions || b.positions.length === 0) && (
                  <div className="border-t px-4 py-2 text-xs text-gray-400">
                    Position details not loaded
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="py-4 text-center text-sm text-gray-400">No batches scheduled</div>
      )}
    </Card>
  );
}
