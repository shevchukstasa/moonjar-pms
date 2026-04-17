import { formatDate } from "@/lib/format";
import { useState } from 'react';
import { toast } from 'sonner';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useOrder, useUpdateOrder } from '@/hooks/useOrders';
import { ordersApi } from '@/api/orders';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { useFactories } from '@/hooks/useFactories';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Tabs } from '@/components/ui/Tabs';
import { Spinner } from '@/components/ui/Spinner';
import { DataTable } from '@/components/ui/Table';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { StatusDropdown } from '@/components/tablo/StatusDropdown';
import { formatEdgeProfile, formatPlaceOfApplication, formatShape, MaterialStatusBadge } from '@/components/tablo/PositionRow';
import { PositionEditDialog } from '@/components/orders/PositionEditDialog';
import { ProductionSplitModal } from '@/components/tablo/ProductionSplitModal';
import { SplitTreeModal } from '@/components/tablo/SplitTreeModal';
import { DatePicker } from '@/components/ui/DatePicker';
import { OrderProgressRing } from '@/components/orders/OrderProgressRing';

/** Format ISO date string as DD/MM (short, year omitted). */
function fmtShortDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso + 'T00:00:00'); // treat as local date
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  return `${day}/${month}`;
}

/** Format position label from position data. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function posLabel(p: any): string {
  if (p.position_label) return p.position_label;
  if (p.position_number != null) {
    return p.split_index != null
      ? `#${p.position_number}.${p.split_index}`
      : `#${p.position_number}`;
  }
  return '#?';
}

/** Check if a position can be split (mirrors backend can_split_position logic). */
function canSplitPosition(p: Record<string, unknown>): boolean {
  const status = p.status as string;
  if (status === 'loaded_in_kiln' || status === 'in_kiln') return false;
  if (p.is_parent) return false;
  if (p.split_category) return false;  // sorting sub-positions
  // Terminal statuses shouldn't be split either
  if (status === 'shipped' || status === 'write_off' || status === 'merged') return false;
  return true;
}

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

  // Factories for edit dropdown
  const { data: factoriesData } = useFactories();
  const factories = factoriesData?.items || [];

  // Edit position
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [editingPosition, setEditingPosition] = useState<Record<string, any> | null>(null);

  // Split position
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [splitPosition, setSplitPosition] = useState<any>(null);
  // Split tree viewer
  const [splitTreePositionId, setSplitTreePositionId] = useState<string | null>(null);

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

  // Reschedule order
  const [rescheduleResult, setRescheduleResult] = useState<{ scheduled?: number; kilns_assigned?: number; materials_reserved?: number } | null>(null);
  const rescheduleMutation = useMutation({
    mutationFn: (id: string) => ordersApi.rescheduleOrder(id),
    onSuccess: (data) => {
      setRescheduleResult(data);
      queryClient.invalidateQueries({ queryKey: ['orders', orderId] });
    },
  });

  // Status override
  const updateOrder = useUpdateOrder();
  const [showOverride, setShowOverride] = useState(false);
  const [overrideStatus, setOverrideStatus] = useState('');
  const [showOverrideConfirm, setShowOverrideConfirm] = useState(false);
  const [overrideSuccess, setOverrideSuccess] = useState(false);

  // Edit order header — all editable fields
  const [isEditing, setIsEditing] = useState(false);
  const [editClient, setEditClient] = useState('');
  const [editDeadline, setEditDeadline] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [editFactoryId, setEditFactoryId] = useState('');
  const [editManagerName, setEditManagerName] = useState('');
  const [editManagerContact, setEditManagerContact] = useState('');
  const [editClientLocation, setEditClientLocation] = useState('');
  const [editDesiredDelivery, setEditDesiredDelivery] = useState('');
  const [editMandatoryQc, setEditMandatoryQc] = useState(false);
  const [editOrderNumber, setEditOrderNumber] = useState('');
  const [editSaving, setEditSaving] = useState(false);

  function startEditing() {
    if (!order) return;
    setEditClient(order.client || '');
    setEditDeadline(order.final_deadline || '');
    setEditNotes(order.notes || '');
    setEditFactoryId(order.factory_id || '');
    setEditManagerName(order.sales_manager_name || '');
    setEditManagerContact(order.sales_manager_contact || '');
    setEditClientLocation(order.client_location || '');
    setEditDesiredDelivery(order.desired_delivery_date || '');
    setEditMandatoryQc(!!order.mandatory_qc);
    setIsEditing(true);
  }

  async function saveEdits() {
    if (!orderId) return;
    setEditSaving(true);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const payload: Record<string, any> = {};
      if (editClient !== (order?.client || '')) payload.client = editClient;
      if (editDeadline !== (order?.final_deadline || '')) payload.final_deadline = editDeadline || null;
      if (editNotes !== (order?.notes || '')) payload.notes = editNotes;
      if (editFactoryId !== (order?.factory_id || '')) payload.factory_id = editFactoryId;
      if (editManagerName !== (order?.sales_manager_name || '')) payload.sales_manager_name = editManagerName || null;
      if (editManagerContact !== (order?.sales_manager_contact || '')) payload.sales_manager_contact = editManagerContact || null;
      if (editClientLocation !== (order?.client_location || '')) payload.client_location = editClientLocation || null;
      if (editDesiredDelivery !== (order?.desired_delivery_date || '')) payload.desired_delivery_date = editDesiredDelivery || null;
      if (editMandatoryQc !== !!order?.mandatory_qc) payload.mandatory_qc = editMandatoryQc;

      if (Object.keys(payload).length > 0) {
        await updateOrder.mutateAsync({ id: orderId, data: payload });
        queryClient.invalidateQueries({ queryKey: ['orders', orderId] });
      }
      setIsEditing(false);
    } finally {
      setEditSaving(false);
    }
  }

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
      render: (item) => item.thickness_mm ? `${item.thickness_mm} mm` : '—',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/manager')}>&larr; Back</Button>
        <OrderProgressRing positions={positions} size={72} />
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

            {/* Edit button */}
            {!isEditing && (
              <button
                className="text-xs text-blue-500 hover:text-blue-700 underline ml-1"
                onClick={startEditing}
              >
                Edit
              </button>
            )}
          </div>
        </div>

        {/* Reschedule Order button -- PM/Admin only */}
        {canReprocess && (
          <Button
            variant="secondary"
            onClick={() => orderId && rescheduleMutation.mutate(orderId)}
            disabled={rescheduleMutation.isPending}
          >
            {rescheduleMutation.isPending ? <Spinner className="h-4 w-4 mr-2" /> : null}
            Reschedule
          </Button>
        )}

        {/* Reprocess Order button -- PM/Admin only */}
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

        {/* Shipment management button -- ready for shipment or already shipped */}
        {(isReadyForShipment || isShipped) && (
          <Button
            className="bg-green-600 hover:bg-green-700 text-white"
            onClick={() => navigate(`/manager/orders/${orderId}/shipment`)}
          >
            {isShipped ? 'View Shipments' : 'Ship Order'}
          </Button>
        )}
        {isShipped && order.shipped_at && (
          <span className="text-sm text-gray-500">
            Shipped {formatDate(order.shipped_at)}
          </span>
        )}
      </div>

      {/* Success banners */}
      {overrideSuccess && (
        <div className="rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800">
          Order status overridden manually.
        </div>
      )}
      {rescheduleResult && (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-800">
          Rescheduled: {rescheduleResult.scheduled ?? 0} positions scheduled, {rescheduleResult.kilns_assigned ?? 0} kilns assigned, {rescheduleResult.materials_reserved ?? 0} materials reserved.
        </div>
      )}
      {rescheduleMutation.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          Reschedule failed: {(rescheduleMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || rescheduleMutation.error?.message || 'Unknown error'}
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

      {/* Order Info -- editable / read-only */}
      {isEditing ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Card>
              <label className="text-xs text-gray-500">Client</label>
              <input
                type="text"
                value={editClient}
                onChange={(e) => setEditClient(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </Card>
            <Card>
              <label className="text-xs text-gray-500">Deadline</label>
              <DatePicker
                value={editDeadline}
                onChange={(v) => setEditDeadline(v)}
                className="mt-1 w-full px-2 py-1.5 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </Card>
            <Card>
              <label className="text-xs text-gray-500">Factory</label>
              <select
                value={editFactoryId}
                onChange={(e) => setEditFactoryId(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">-- Select --</option>
                {factories.map((f) => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
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
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Card>
              <label className="text-xs text-gray-500">Sales Manager</label>
              <input
                type="text"
                value={editManagerName}
                onChange={(e) => setEditManagerName(e.target.value)}
                placeholder="Manager name"
                className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </Card>
            <Card>
              <label className="text-xs text-gray-500">Manager Contact</label>
              <input
                type="text"
                value={editManagerContact}
                onChange={(e) => setEditManagerContact(e.target.value)}
                placeholder="Phone / email"
                className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </Card>
            <Card>
              <label className="text-xs text-gray-500">Client Location</label>
              <input
                type="text"
                value={editClientLocation}
                onChange={(e) => setEditClientLocation(e.target.value)}
                placeholder="Location"
                className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </Card>
            <Card>
              <label className="text-xs text-gray-500">Desired Delivery</label>
              <DatePicker
                value={editDesiredDelivery}
                onChange={(v) => setEditDesiredDelivery(v)}
                className="mt-1 w-full px-2 py-1.5 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </Card>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <label className="text-xs text-gray-500">Notes</label>
              <input
                type="text"
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                placeholder="Add notes..."
                className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </Card>
            <Card>
              <label className="flex items-center gap-2 text-xs text-gray-500">
                <input
                  type="checkbox"
                  checked={editMandatoryQc}
                  onChange={(e) => setEditMandatoryQc(e.target.checked)}
                  className="rounded"
                />
                Mandatory QC
              </label>
            </Card>
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={saveEdits} disabled={editSaving}>
              {editSaving ? <Spinner className="h-4 w-4 mr-2" /> : null}
              Save
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setIsEditing(false)} disabled={editSaving}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Card>
              <div className="text-xs text-gray-500">Client</div>
              <div className="mt-1 font-medium text-gray-900">{order.client || '—'}</div>
            </Card>
            <Card>
              <div className="text-xs text-gray-500">Deadline</div>
              <div className="mt-1 font-medium text-gray-900">
                {order.final_deadline ? formatDate(order.final_deadline) : '—'}
              </div>
            </Card>
            <Card>
              <div className="text-xs text-gray-500">Factory</div>
              <div className="mt-1 font-medium text-gray-900">{order.factory_name || order.factory_id || '—'}</div>
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

          {/* Second row: manager, contact, location, delivery */}
          {(order.sales_manager_name || order.client_location || order.desired_delivery_date || order.mandatory_qc) && (
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {order.sales_manager_name && (
                <Card>
                  <div className="text-xs text-gray-500">Sales Manager</div>
                  <div className="mt-1 font-medium text-gray-900">{order.sales_manager_name}</div>
                  {order.sales_manager_contact && (
                    <div className="text-xs text-gray-500">{order.sales_manager_contact}</div>
                  )}
                </Card>
              )}
              {order.client_location && (
                <Card>
                  <div className="text-xs text-gray-500">Client Location</div>
                  <div className="mt-1 font-medium text-gray-900">{order.client_location}</div>
                </Card>
              )}
              {order.desired_delivery_date && (
                <Card>
                  <div className="text-xs text-gray-500">Desired Delivery</div>
                  <div className="mt-1 font-medium text-gray-900">{formatDate(order.desired_delivery_date)}</div>
                </Card>
              )}
              {order.mandatory_qc && (
                <Card>
                  <div className="text-xs text-gray-500">QC</div>
                  <div className="mt-1 font-medium text-orange-600">Mandatory QC ✓</div>
                </Card>
              )}
            </div>
          )}

          {order.notes && (
            <Card>
              <div className="text-xs text-gray-500">Notes</div>
              <div className="mt-1 text-sm text-gray-700">{order.notes}</div>
            </Card>
          )}
        </>
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
          <div className="space-y-3">
            {positions.map((p: Record<string, unknown>, idx: number) => (
              <PositionCard
                key={(p.id as string) || idx}
                position={p}
                index={idx}
                orderNumber={order.order_number}
                onEdit={() => setEditingPosition(p)}
                onSplit={() => setSplitPosition({
                  id: p.id as string,
                  order_number: order.order_number,
                  quantity: p.quantity as number,
                  color: p.color as string,
                  size: p.size as string,
                  status: p.status as string,
                })}
                onViewTree={() => setSplitTreePositionId(p.id as string)}
              />
            ))}
          </div>
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

      {/* Edit Position Dialog */}
      <PositionEditDialog
        open={!!editingPosition}
        onClose={() => setEditingPosition(null)}
        position={editingPosition}
      />

      {/* Split Position Modal */}
      <ProductionSplitModal
        position={splitPosition}
        onClose={() => {
          setSplitPosition(null);
          queryClient.invalidateQueries({ queryKey: ['orders', orderId] });
        }}
      />

      {/* Split Tree Viewer */}
      <SplitTreeModal
        positionId={splitTreePositionId}
        onClose={() => setSplitTreePositionId(null)}
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
          if (overrideStatus === 'shipped') {
            toast.success(`📦 Order ${order.order_number} shipped — great work!`);
          } else if (overrideStatus === 'ready_for_shipment') {
            toast.success(`✅ Order ${order.order_number} ready for shipment`);
          }
        }}
        title="Override Order Status"
        message={`Manually set order #${order.order_number} status to "${VALID_STATUSES.find((s) => s.value === overrideStatus)?.label ?? overrideStatus}"? This bypasses automatic status calculation.`}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Position Card Component                                            */
/* ------------------------------------------------------------------ */

function PositionCard({
  position: p,
  index,
  orderNumber,
  onEdit,
  onSplit,
  onViewTree,
}: {
  position: Record<string, unknown>;
  index: number;
  orderNumber: string;
  onEdit: () => void;
  onSplit: () => void;
  onViewTree: () => void;
}) {
  const [materialsOpen, setMaterialsOpen] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [materialsData, setMaterialsData] = useState<any[] | null>(null);
  const [materialsLoading, setMaterialsLoading] = useState(false);

  const toggleMaterials = async () => {
    if (materialsOpen) {
      setMaterialsOpen(false);
      return;
    }
    setMaterialsOpen(true);
    if (materialsData !== null) return; // already loaded
    setMaterialsLoading(true);
    try {
      const { default: apiClient } = await import('@/api/client');
      const res = await apiClient.get(`/positions/${p.id}/materials`);
      setMaterialsData(res.data?.requirements || []);
    } catch {
      setMaterialsData([]);
    } finally {
      setMaterialsLoading(false);
    }
  };

  const label = posLabel(p);
  const color = (p.color as string) || '—';
  const size = (p.size as string) || '';
  const quantity = p.quantity as number | undefined;
  const thicknessMm = (p.thickness_mm as number) || 10;
  const shape = formatShape(p.shape as string, p.width_cm as number, p.length_cm as number);
  const glazePlace = formatPlaceOfApplication(p.place_of_application as string);
  const edgeRaw = formatEdgeProfile(p.edge_profile as string, p.edge_profile_sides as number);
  const isNonDefaultEdge = p.edge_profile && p.edge_profile !== 'straight';
  const productType = (p.product_type as string) || '—';
  const application = (p.application as string) || (p.application_method as string) || '—';
  const collection = (p.collection as string) || '—';
  const finishing = (p.finishing as string) || '—';
  const priority = (p.priority_order as number) ?? '—';

  const hasPlanningDates = p.planned_glazing_date || p.planned_kiln_date || p.planned_sorting_date || p.estimated_kiln_name;

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      {/* Header row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-lg font-bold text-gray-400">{label}</span>
          {p.is_parent && (
            <span className="inline-flex items-center rounded bg-orange-50 px-1.5 py-0.5 text-[10px] font-medium text-orange-700" title="Parent position (split)">
              PARENT
            </span>
          )}
          {p.parent_position_id && !p.is_parent && (
            <span className="inline-flex items-center rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700" title="Child of a split position">
              CHILD
            </span>
          )}
          <span className="text-lg font-semibold">{color}</span>
          {size && <span className="text-sm text-gray-500">{size}</span>}
          {quantity != null && (
            <span className="font-mono font-bold">{quantity} pcs</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {p.id ? (
            <StatusDropdown positionId={p.id as string} currentStatus={p.status as string} section="" />
          ) : (
            <Badge status={p.status as string} />
          )}
          <MaterialStatusBadge status={p.material_status as string} />
          {/* Split button — only for positions that can be split */}
          {canSplitPosition(p) && (
            <button
              className="rounded px-2 py-1 text-xs font-medium text-orange-600 hover:bg-orange-50 hover:text-orange-800"
              onClick={onSplit}
              title="Split this position into multiple parts"
            >
              Split
            </button>
          )}
          {/* Split tree — show for parent or child positions */}
          {(p.is_parent || p.parent_position_id) && (
            <button
              className="rounded px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50 hover:text-indigo-800"
              onClick={onViewTree}
              title="View split tree"
            >
              Tree
            </button>
          )}
          <button
            className="rounded px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 hover:text-blue-800"
            onClick={onEdit}
          >
            Edit
          </button>
        </div>
      </div>

      {/* Details grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-1 text-sm text-gray-600">
        <div><span className="text-gray-400">Shape:</span> {shape}</div>
        <div><span className="text-gray-400">Thickness:</span> {thicknessMm} mm</div>
        <div>
          <span className="text-gray-400">Edge:</span>{' '}
          {isNonDefaultEdge ? (
            <span className="inline-flex items-center rounded bg-orange-50 px-1.5 py-0.5 text-[10px] font-medium text-orange-700">
              {edgeRaw}
            </span>
          ) : (
            edgeRaw
          )}
        </div>
        <div><span className="text-gray-400">Glaze:</span> {glazePlace}</div>
        <div><span className="text-gray-400">Application:</span> {application}</div>
        <div><span className="text-gray-400">Collection:</span> {collection}</div>
        <div><span className="text-gray-400">Type:</span> {productType}</div>
        <div><span className="text-gray-400">Finishing:</span> {finishing}</div>
        <div><span className="text-gray-400">Priority:</span> {typeof priority === 'number' ? priority : '—'}</div>
      </div>

      {/* Planning row */}
      {hasPlanningDates && (
        <div className="mt-3 flex gap-4 flex-wrap text-xs border-t pt-2 text-gray-600">
          <span>Glazing: <b>{fmtShortDate(p.planned_glazing_date as string)}</b></span>
          <span>Kiln: <b>{fmtShortDate(p.planned_kiln_date as string)}</b></span>
          <span>Sorting: <b>{fmtShortDate(p.planned_sorting_date as string)}</b></span>
          {p.estimated_kiln_name && (
            <span>Kiln: <b className="text-indigo-600">{p.estimated_kiln_name as string}</b></span>
          )}
          <span>Batch: {p.batch_id ? <span className="text-gray-500">{(p.batch_id as string).slice(0, 8)}...</span> : '—'}</span>
          <span>Delay: {p.delay_hours ? <span className="text-orange-600">{p.delay_hours as number}h</span> : '—'}</span>
        </div>
      )}

      {/* Materials expandable section */}
      <div className="mt-3 border-t pt-2">
        <button
          onClick={toggleMaterials}
          className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
        >
          {materialsOpen ? '▼' : '▶'} Materials
        </button>
        {materialsOpen && (
          <div className="mt-2">
            {materialsLoading ? (
              <div className="text-xs text-gray-400">Loading materials...</div>
            ) : materialsData && materialsData.length > 0 ? (
              <div className="overflow-x-auto rounded border border-gray-200">
                <table className="w-full text-left text-xs">
                  <thead className="border-b bg-gray-50 text-[10px] font-medium uppercase text-gray-500">
                    <tr>
                      <th className="px-2 py-1">Material</th>
                      <th className="px-2 py-1">Type</th>
                      <th className="px-2 py-1 text-right">Qty</th>
                      <th className="px-2 py-1">Unit</th>
                      <th className="px-2 py-1">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {materialsData.map((m: any, i: number) => (
                      <tr key={i} className="bg-white">
                        <td className="px-2 py-1 font-medium text-gray-700">{m.material_name}</td>
                        <td className="px-2 py-1 text-gray-500">{m.type}</td>
                        <td className="px-2 py-1 text-right font-mono">{m.quantity_needed}</td>
                        <td className="px-2 py-1 text-gray-500">{m.unit}</td>
                        <td className="px-2 py-1">
                          {m.reserved ? (
                            <span className="inline-flex items-center rounded bg-green-50 px-1.5 py-0.5 text-[10px] font-medium text-green-700">Reserved</span>
                          ) : (
                            <span className="inline-flex items-center rounded bg-red-50 px-1.5 py-0.5 text-[10px] font-medium text-red-700">Not Reserved</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-xs text-gray-400">No material requirements found (recipe may not be assigned yet)</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
