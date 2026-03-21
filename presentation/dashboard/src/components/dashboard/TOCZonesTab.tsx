import { formatDate } from "@/lib/format";
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { tocApi } from '@/api/toc';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { ProgressBar } from '@/components/ui/ProgressBar';

interface BufferZoneItem {
  order_id: string;
  order_number: string;
  zone: 'green' | 'yellow' | 'red';
  delta_pct: number;
  work_pct: number;
  time_pct: number;
  position_count: number;
  eta: string | null;
}

interface BufferZonesResponse {
  zones: BufferZoneItem[];
  summary: { green: number; yellow: number; red: number; total: number };
}

interface TOCZonesTabProps {
  factoryId?: string;
}

const ZONE_CONFIG = {
  green: { bg: 'bg-green-50', border: 'border-green-200', badge: 'bg-green-100 text-green-800', label: 'Green' },
  yellow: { bg: 'bg-yellow-50', border: 'border-yellow-200', badge: 'bg-yellow-100 text-yellow-800', label: 'Yellow' },
  red: { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-100 text-red-800', label: 'Red' },
} as const;

export function TOCZonesTab({ factoryId }: TOCZonesTabProps) {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery<BufferZonesResponse>({
    queryKey: ['buffer-zones', factoryId],
    queryFn: () => tocApi.getBufferZones(factoryId ? { factory_id: factoryId } : undefined),
    refetchInterval: 60_000,
  });

  if (isLoading) {
    return <div className="flex justify-center py-12"><Spinner /></div>;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-800">Error loading buffer zones</p>
      </div>
    );
  }

  // API returns {items: [], summary: {}} but interface expects {zones: []}
  const zones = (data as any)?.zones ?? (data as any)?.items ?? [];
  const summary = data?.summary ?? { green: 0, yellow: 0, red: 0, total: 0 };

  if (!data || zones.length === 0) {
    return (
      <EmptyState
        title="No buffer zone data"
        description="Buffer zone data will appear once orders are scheduled and tracked."
      />
    );
  }

  const greenOrders = zones.filter((z: any) => z.zone === 'green');
  const yellowOrders = zones.filter((z: any) => z.zone === 'yellow');
  const redOrders = zones.filter((z: any) => z.zone === 'red');

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <div className="grid grid-cols-4 gap-3">
        <Card className="p-4">
          <div className="text-2xl font-bold text-gray-900">{summary.total}</div>
          <div className="text-xs text-gray-500 mt-1">Total Orders</div>
        </Card>
        <Card className="p-4 border-green-200 bg-green-50/50">
          <div className="text-2xl font-bold text-green-700">{summary.green}</div>
          <div className="text-xs text-green-600 mt-1">Green Zone</div>
        </Card>
        <Card className="p-4 border-yellow-200 bg-yellow-50/50">
          <div className="text-2xl font-bold text-yellow-700">{summary.yellow}</div>
          <div className="text-xs text-yellow-600 mt-1">Yellow Zone</div>
        </Card>
        <Card className="p-4 border-red-200 bg-red-50/50">
          <div className="text-2xl font-bold text-red-700">{summary.red}</div>
          <div className="text-xs text-red-600 mt-1">Red Zone</div>
        </Card>
      </div>

      {/* 3-column zone board */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {(['green', 'yellow', 'red'] as const).map((zone) => {
          const cfg = ZONE_CONFIG[zone];
          const orders = zone === 'green' ? greenOrders : zone === 'yellow' ? yellowOrders : redOrders;
          const count = zone === 'green' ? summary.green : zone === 'yellow' ? summary.yellow : summary.red;

          return (
            <div key={zone} className={`rounded-lg border ${cfg.border} ${cfg.bg} p-4`}>
              {/* Column header */}
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-900">{cfg.label} Zone</h3>
                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.badge}`}>
                  {count}
                </span>
              </div>

              {/* Cards */}
              <div className="space-y-3">
                {orders.length === 0 ? (
                  <p className="text-center text-xs text-gray-400 py-4">No orders</p>
                ) : (
                  orders.map((order) => (
                    <div
                      key={order.order_id}
                      className="cursor-pointer rounded-md border border-white/60 bg-white p-3 shadow-sm transition-shadow hover:shadow-md"
                      onClick={() => navigate(`/manager/orders/${order.order_id}`)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-gray-900">{order.order_number}</span>
                        <span className={`text-xs font-mono font-medium ${order.delta_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {order.delta_pct >= 0 ? '+' : ''}{order.delta_pct.toFixed(1)}%
                        </span>
                      </div>

                      {/* Work progress */}
                      <div className="mb-1">
                        <div className="flex justify-between text-xs text-gray-500 mb-0.5">
                          <span>Work</span>
                          <span>{order.work_pct.toFixed(0)}%</span>
                        </div>
                        <ProgressBar value={order.work_pct} />
                      </div>

                      {/* Time progress */}
                      <div className="mb-2">
                        <div className="flex justify-between text-xs text-gray-500 mb-0.5">
                          <span>Time</span>
                          <span>{order.time_pct.toFixed(0)}%</span>
                        </div>
                        <ProgressBar value={order.time_pct} />
                      </div>

                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>{order.position_count} position{order.position_count !== 1 ? 's' : ''}</span>
                        {order.eta && <span>ETA: {formatDate(order.eta)}</span>}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
