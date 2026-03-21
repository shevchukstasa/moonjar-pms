import { formatDate } from "@/lib/format";
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useOrder, useShipOrder, useUpdateOrder } from '@/hooks/useOrders';
import { ordersApi } from '@/api/orders';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Tabs } from '@/components/ui/Tabs';
import { Spinner } from '@/components/ui/Spinner';
import { DataTable } from '@/components/ui/Table';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { StatusDropdown } from '@/components/tablo/StatusDropdown';
import { formatEdgeProfile, formatPlaceOfApplication, formatShape, MaterialStatusBadge } from '@/components/tablo/PositionRow';

const VALID_STATUSES = [
  { value: 'new', label: 'New' },
  { value: 'in_production', label: 'In Production' },
  { value: 'partially_ready', label: 'Partially Ready' },
  { value: 'ready_for_shipment', label: 'Ready for Shipment' },
  { value: 'shipped', label: 'Shipped' },
  { value: 'cancelled', label: 'Cancelled' },
];

export default function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const { data: order, isLoading, isError } = useOrder(orderId);
  const [tab, setTab] = useState('positions');

  // Ship order
  const shipOrder = useShipOrder();
  const [showShipConfirm, setShowShipConfirm] = useState(false);
  const [shipSuccess, setShipSuccess] = useState(false);

  // Reprocess order
  const currentUser = useCurrentUser();
  const queryClient = useQueryClient();
  const canReprocess = currentUser && ['production_manager', 'administrator', 'owner'].includes(currentUser.role);
  const [reprocessResult, setReprocessResult] = useState<{ message: string; details?: Record<string, unknown> } | null>(null);
  const reprocessMutation = useMutation({
    mutationFn: (id: string) => ordersApi.reprocessOrder(id),
    onSuccess: (data) => {
      setReprocessResult(data);
      queryClient.invalidateQueries({ queryKey: ['orders', orderId] });
    },
  });

  // Status override
  const updateOrder = useUpdateOrder();
  const [showOverride, setShowOverride] = useState(false);
  const [overrideStatus, setOverrideStatus] = useState('');
  const [showOverrideConfirm, setShowOverrideConfirm] = useState(false);
  const [overrideSuccess, setOverrideSuccess] = useState(false);

  if (isLoading) {
    return <div className="flex justify-center py-20"><Spinner className="h-10 w-10" /></div>;
  }

  if (isError) {
    return (
      <div className="space-y-4">
        <button className="text-sm text-gray-500 hover:text-gray-700" onClick={() => navigate("/manager")}>← Back</button>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="font-medium text-red-800">Error loading order</p>
          <p className="mt-1 text-sm text-red-600">Please refresh the page or go back.</p>
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => navigate('/manager')}>&larr; Back</Button>
        <div className="py-12 text-center text-gray-400">Order not found</div>
      </div>
    );
  }

  const positions = order.positions || [];
  const items = order.items || [];
  const isReadyForShipment = order.status === 'ready_for_shipment';
  const isShipped = order.status === 'shipped';

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const positionColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    {
      key: 'position_label',
      header: '#',
      render: (p) => (
        <span className="font-mono text-xs font-semibold text-gray-700">
          {p.position_label ?? (p.position_number != null
            ? (p.split_index != null ? `#${p.position_number}.${p.split_index}` : `#${p.position_number}`)
            : '—')}
        </span>
      ),
    },
    { key: 'color', header: 'Color' },
    { key: 'size', header: 'Size' },
    {
      key: 'thickness_mm',
      header: 'Thickness',
      render: (p) => p.thickness_mm ? `${p.thickness_mm} mm` : '10 mm',
    },
    {
      key: 'shape',
      header: 'Shape',
      render: (p) => formatShape(p.shape, p.width_cm, p.length_cm),
    },
    {
      key: 'place_of_application',
      header: 'Glaze Place',
      render: (p) => formatPlaceOfApplication(p.place_of_application),
    },
    {
      key: 'edge_profile',
      header: 'Edge',
      render: (p) => {
        const edge = formatEdgeProfile(p.edge_profile, p.edge_profile_sides);
        const isNonDefault = p.edge_profile && p.edge_profile !== 'straight';
        return isNonDefault ? (
          <span className="inline-flex items-center rounded bg-orange-50 px-1.5 py-0.5 text-[10px] font-medium text-orange-700">
            {edge}
          </span>
        ) : edge;
      },
    },
    { key: 'quantity', header: 'Qty' },
    {
      key: 'status',
      header: 'Status',
      render: (p) =>
        p.id ? (
          <StatusDropdown positionId={p.id} currentStatus={p.status} section="" />
        ) : (
          <Badge status={p.status} />
        ),
    },
    {
      key: 'material_status',
      header: 'Materials',
      render: (p) => <MaterialStatusBadge status={p.material_status} />,
    },
    { key: 'product_type', header: 'Type' },
    {
      key: 'batch_id',
      header: 'Batch',
      render: (p) => p.batch_id ? <span className="text-xs text-gray-500">{p.batch_id.slice(0, 8)}...</span> : '\u2014',
    },
    {
      key: 'delay_hours',
      header: 'Delay',
      render: (p) => p.delay_hours ? <span className="text-orange-600">{p.delay_hours}h</span> : '\u2014',
    },
  ];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const itemColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    { key: 'color', header: 'Color' },
    { key: 'size', header: 'Size' },
    { key: 'quantity_pcs', header: 'Qty (pcs)' },
    { key: 'application', header: 'Application' },
    { key: 'finishing', header: 'Finishing' },
    { key: 'product_type', header: 'Type' },
    {
      key: 'thickness_mm',
      header: 'Thickness',
      render: (item) => item.thickness_mm ? `${item.thickness_mm} mm` : '\u2014',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/manager')}>&larr; Back</Button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-gray-900">Order {order.order_number}</h1>
            <Badge status={order.status} />

            {/* Override status button */}
            <div className="relative">
              <button
                className="text-xs text-gray-400 hover:text-gray-600 underline ml-1"
                onClick={() => {
                  setOverrideStatus(order.status);
                  setShowOverride((v) => !v);
                }}
              >
                Override status
              </button>
              {showOverride && (
                <div className="absolute left-0 top-6 z-10 rounded-lg border border-gray-200 bg-white shadow-lg p-3 min-w-[220px]">
                  <p className="text-xs font-medium text-orange-600 mb-2">
                    Manual override bypasses automatic status calculation
                  </p>
                  <select
                    value={overrideStatus}
                    onChange={(e) => setOverrideStatus(e.target.value)}
                    className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm mb-2"
                  >
                    {VALID_STATUSES.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={updateOrder.isPending || overrideStatus === order.status}
                      onClick={() => {
                        setShowOverride(false);
                        setShowOverrideConfirm(true);
                      }}
                    >
                      Apply
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setShowOverride(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Reprocess Order button — PM/Admin only */}
        {canReprocess && (
          <Button
            variant="secondary"
            onClick={() => orderId && reprocessMutation.mutate(orderId)}
            disabled={reprocessMutation.isPending}
          >
            {reprocessMutation.isPending ? <Spinner className="h-4 w-4 mr-2" /> : null}
            Reprocess Order
          </Button>
        )}

        {/* Ship Order button — only when ready for shipment */}
        {isReadyForShipment && !isShipped && (
          <Button
            className="bg-green-600 hover:bg-green-700 text-white"
            onClick={() => setShowShipConfirm(true)}
            disabled={shipOrder.isPending}
          >
            {shipOrder.isPending ? <Spinner className="h-4 w-4 mr-2" /> : null}
            Ship Order
          </Button>
        )}
        {isShipped && order.shipped_at && (
          <span className="text-sm text-gray-500">
            Shipped {formatDate(order.shipped_at)}
          </span>
        )}
      </div>

      {/* Success banners */}
      {shipSuccess && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          Order shipped successfully. Sales has been notified.
        </div>
      )}
      {overrideSuccess && (
        <div className="rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800">
          Order status overridden manually.
        </div>
      )}
      {reprocessResult && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          <p className="font-medium">{reprocessResult.message || 'Order reprocessed successfully.'}</p>
          {reprocessResult.details && (
            <pre className="mt-2 max-h-40 overflow-auto rounded bg-blue-100 p-2 text-xs">
              {JSON.stringify(reprocessResult.details, null, 2)}
            </pre>
          )}
        </div>
      )}
      {reprocessMutation.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          Reprocess failed: {(reprocessMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || reprocessMutation.error?.message || 'Unknown error'}
        </div>
      )}

      {/* Order Info */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <div className="text-xs text-gray-500">Client</div>
          <div className="mt-1 font-medium text-gray-900">{order.client || '\u2014'}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Deadline</div>
          <div className="mt-1 font-medium text-gray-900">
            {order.final_deadline ? formatDate(order.final_deadline) : '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Factory</div>
          <div className="mt-1 font-medium text-gray-900">{order.factory_name || order.factory_id || '\u2014'}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Positions</div>
          <div className="mt-1 font-medium text-gray-900">
            <span className="text-green-600">{order.positions_ready || 0}</span>
            <span className="text-gray-400"> / </span>
            <span>{order.positions_count || 0}</span>
            <span className="ml-1 text-xs text-gray-400">ready</span>
          </div>
        </Card>
      </div>

      {order.notes && (
        <Card>
          <div className="text-xs text-gray-500">Notes</div>
          <div className="mt-1 text-sm text-gray-700">{order.notes}</div>
        </Card>
      )}

      {/* Tabs */}
      <Tabs
        tabs={[
          { id: 'positions', label: `Positions (${positions.length})` },
          { id: 'items', label: `Items (${items.length})` },
        ]}
        activeTab={tab}
        onChange={setTab}
      />

      {/* Content */}
      {tab === 'positions' && (
        positions.length > 0 ? (
          <DataTable columns={positionColumns} data={positions} />
        ) : (
          <div className="py-8 text-center text-gray-400">No positions yet</div>
        )
      )}

      {tab === 'items' && (
        items.length > 0 ? (
          <DataTable columns={itemColumns} data={items} />
        ) : (
          <div className="py-8 text-center text-gray-400">No items</div>
        )
      )}

      {/* Confirm Ship */}
      <ConfirmDialog
        open={showShipConfirm}
        onClose={() => setShowShipConfirm(false)}
        onConfirm={async () => {
          if (!orderId) return;
          await shipOrder.mutateAsync(orderId);
          setShipSuccess(true);
        }}
        title="Confirm Shipment"
        message={`Confirm shipment of order #${order.order_number}? This will notify Sales and mark the order as shipped.`}
      />

      {/* Confirm Status Override */}
      <ConfirmDialog
        open={showOverrideConfirm}
        onClose={() => setShowOverrideConfirm(false)}
        onConfirm={async () => {
          if (!orderId) return;
          await updateOrder.mutateAsync({
            id: orderId,
            data: { status: overrideStatus, status_override: true },
          });
          setOverrideSuccess(true);
        }}
        title="Override Order Status"
        message={`Manually set order #${order.order_number} status to "${VALID_STATUSES.find((s) => s.value === overrideStatus)?.label ?? overrideStatus}"? This bypasses automatic status calculation.`}
      />
    </div>
  );
}
