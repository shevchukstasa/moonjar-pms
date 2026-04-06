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

interface LoadingPlanEntry {
  position_id: string;
  loading_method: 'flat' | 'edge' | 'unknown';
  pieces_per_level: number;
  levels_used: number;
  total_pieces: number;
  area_used_sqm: number;
  is_filler?: boolean;
}

interface LoadingPlan {
  total_area_sqm: number;
  utilization_pct: number;
  entries: LoadingPlanEntry[];
  filler_ids?: string[];
}

interface BatchItem {
  id: string;
  batch_date: string | null;
  status: string;
  positions_count: number;
  total_pcs: number;
  notes: string | null;
  loading_plan?: LoadingPlan | null;
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

export function KilnCard({ kiln, batches: rawBatches }: Props) {
  const batches = rawBatches ?? [];
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
                    <span className="text-xs text-gray-400">{isExpanded ? '▼' : '▶'}</span>
                    <span className="text-sm text-gray-700">{b.batch_date || 'No date'}</span>
                    <Badge status={b.status} />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span>{b.positions_count} pos</span>
                    <span>{b.total_pcs} pcs</span>
                    {b.loading_plan && (
                      <span className="flex items-center gap-1.5">
                        <span className={`font-semibold ${
                          b.loading_plan.utilization_pct >= 80 ? 'text-green-600' :
                          b.loading_plan.utilization_pct >= 50 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {b.loading_plan.utilization_pct.toFixed(0)}%
                        </span>
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-200">
                          <div
                            className={`h-full rounded-full ${
                              b.loading_plan.utilization_pct >= 80 ? 'bg-green-500' :
                              b.loading_plan.utilization_pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${Math.min(100, b.loading_plan.utilization_pct)}%` }}
                          />
                        </div>
                      </span>
                    )}
                    {b.loading_plan?.filler_ids && b.loading_plan.filler_ids.length > 0 && (
                      <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
                        +{b.loading_plan.filler_ids.length} filler
                      </span>
                    )}
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
