import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { useUiStore } from '@/stores/uiStore';
import {
  usePurchaseRequests,
  usePurchaserStats,
  useDeliveries,
  useChangeRequestStatus,
  type PurchaseRequestItem,
} from '@/hooks/usePurchaseRequests';
import { useLowStock, type MaterialItem } from '@/hooks/useMaterials';
import { useSuppliers, type SupplierItem } from '@/hooks/useSuppliers';

const TABS = [
  { id: 'active', label: 'Active' },
  { id: 'deliveries', label: 'Deliveries' },
  { id: 'deficits', label: 'Deficits' },
  { id: 'suppliers', label: 'Suppliers' },
];

export default function PurchaserDashboard() {
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);
  const [tab, setTab] = useState('active');

  const { data: stats, isLoading: statsLoading } = usePurchaserStats(
    activeFactoryId || undefined,
  );

  const { data: activeData, isLoading: activeLoading } = usePurchaseRequests(
    activeFactoryId
      ? { factory_id: activeFactoryId, status: 'pending,approved,sent' }
      : { status: 'pending,approved,sent' },
  );
  const activeRequests = activeData?.items || [];

  const { data: deliveriesData, isLoading: deliveriesLoading } = useDeliveries(
    activeFactoryId || undefined,
  );
  const deliveries = deliveriesData?.items || [];

  const { data: lowStockData, isLoading: lowStockLoading } = useLowStock(
    activeFactoryId || undefined,
  );
  const lowStockItems = lowStockData?.items || [];

  const { data: suppliersData, isLoading: suppliersLoading } = useSuppliers();
  const suppliers = suppliersData?.items || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Purchaser</h1>
        <p className="mt-1 text-sm text-gray-500">
          Purchase requests, deliveries, suppliers
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="text-center">
          <p className="text-2xl font-bold text-blue-600">
            {statsLoading ? '-' : (stats?.active_requests ?? 0)}
          </p>
          <p className="text-xs text-gray-500">Active Requests</p>
        </Card>
        <Card className="text-center">
          <p className="text-2xl font-bold text-orange-600">
            {statsLoading ? '-' : (stats?.pending_approval ?? 0)}
          </p>
          <p className="text-xs text-gray-500">Pending Approval</p>
        </Card>
        <Card className="text-center">
          <p className="text-2xl font-bold text-green-600">
            {statsLoading ? '-' : (stats?.awaiting_delivery ?? 0)}
          </p>
          <p className="text-xs text-gray-500">Awaiting Delivery</p>
        </Card>
        <Card className="text-center">
          <p className="text-2xl font-bold text-red-600">
            {statsLoading ? '-' : (stats?.overdue_deliveries ?? 0)}
          </p>
          <p className="text-xs text-gray-500">Overdue</p>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} activeTab={tab} onChange={setTab} />

      {/* Tab Content */}
      {tab === 'active' && (
        <ActiveRequestsTab requests={activeRequests} isLoading={activeLoading} />
      )}
      {tab === 'deliveries' && (
        <DeliveriesTab deliveries={deliveries} isLoading={deliveriesLoading} />
      )}
      {tab === 'deficits' && (
        <DeficitsTab items={lowStockItems} isLoading={lowStockLoading} />
      )}
      {tab === 'suppliers' && (
        <SuppliersTab suppliers={suppliers} isLoading={suppliersLoading} />
      )}
    </div>
  );
}

/* ---- Helper: extract readable material names from materials_json ---- */
function getMaterialsSummary(
  materialsJson: Record<string, unknown> | Array<Record<string, unknown>>,
): string {
  if (Array.isArray(materialsJson)) {
    const names = materialsJson
      .map((m) => (m.name as string) || (m.material_name as string) || 'Unknown')
      .slice(0, 3);
    const suffix = materialsJson.length > 3 ? ` +${materialsJson.length - 3}` : '';
    return names.join(', ') + suffix;
  }
  if (typeof materialsJson === 'object' && materialsJson !== null) {
    const keys = Object.keys(materialsJson).slice(0, 3);
    if (keys.length === 0) return 'No materials';
    const suffix =
      Object.keys(materialsJson).length > 3
        ? ` +${Object.keys(materialsJson).length - 3}`
        : '';
    return keys.join(', ') + suffix;
  }
  return 'No materials';
}

/* ---- ACTIVE REQUESTS TAB ---- */
function ActiveRequestsTab({
  requests,
  isLoading,
}: {
  requests: PurchaseRequestItem[];
  isLoading: boolean;
}) {
  const changeStatus = useChangeRequestStatus();
  const [confirmAction, setConfirmAction] = useState<{
    id: string;
    status: string;
    title: string;
    message: string;
  } | null>(null);

  if (isLoading) return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  if (requests.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No active purchase requests</p>
      </div>
    );
  }

  const handleConfirm = async () => {
    if (!confirmAction) return;
    await changeStatus.mutateAsync({
      id: confirmAction.id,
      data: { status: confirmAction.status },
    });
  };

  return (
    <>
      <div className="space-y-3">
        {requests.map((r) => (
          <div
            key={r.id}
            className="rounded-lg border border-gray-200 bg-white p-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-semibold">
                  {r.supplier_name || 'No supplier'}
                </span>
                <Badge status={r.status} />
              </div>
              <span className="text-xs text-gray-400">{r.source}</span>
            </div>

            <p className="mt-1 text-sm text-gray-600">
              {getMaterialsSummary(r.materials_json)}
            </p>

            <div className="mt-1 flex flex-wrap gap-3 text-xs text-gray-400">
              {r.created_at && <span>Created: {new Date(r.created_at).toLocaleDateString()}</span>}
              {r.expected_delivery_date && <span>Expected: {new Date(r.expected_delivery_date).toLocaleDateString()}</span>}
              {r.approved_by_name && <span>Approved by: {r.approved_by_name}</span>}
            </div>

            {r.notes && (
              <p className="mt-1 text-xs italic text-gray-400">{r.notes}</p>
            )}

            {/* Status workflow buttons */}
            <div className="mt-3 flex gap-2">
              {r.status === 'pending' && (
                <Button
                  size="sm"
                  className="bg-green-500 hover:bg-green-600"
                  disabled={changeStatus.isPending}
                  onClick={() =>
                    setConfirmAction({
                      id: r.id,
                      status: 'approved',
                      title: 'Approve Request',
                      message: `Approve purchase request from "${r.supplier_name || 'No supplier'}"?`,
                    })
                  }
                >
                  Approve
                </Button>
              )}
              {r.status === 'approved' && (
                <Button
                  size="sm"
                  disabled={changeStatus.isPending}
                  onClick={() =>
                    setConfirmAction({
                      id: r.id,
                      status: 'sent',
                      title: 'Mark as Sent',
                      message: `Mark order to "${r.supplier_name || 'No supplier'}" as sent to supplier?`,
                    })
                  }
                >
                  Mark Sent
                </Button>
              )}
              {r.status === 'sent' && (
                <Button
                  size="sm"
                  className="bg-green-500 hover:bg-green-600"
                  disabled={changeStatus.isPending}
                  onClick={() =>
                    setConfirmAction({
                      id: r.id,
                      status: 'received',
                      title: 'Mark as Received',
                      message: `Confirm delivery received from "${r.supplier_name || 'No supplier'}"?`,
                    })
                  }
                >
                  Mark Received
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      <ConfirmDialog
        open={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={handleConfirm}
        title={confirmAction?.title || ''}
        message={confirmAction?.message || ''}
      />
    </>
  );
}

/* ---- DELIVERIES TAB ---- */
function DeliveriesTab({
  deliveries,
  isLoading,
}: {
  deliveries: PurchaseRequestItem[];
  isLoading: boolean;
}) {
  if (isLoading) return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  if (deliveries.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No deliveries yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {deliveries.map((d) => (
        <div
          key={d.id}
          className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
        >
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold">
                {d.supplier_name || 'No supplier'}
              </span>
              <Badge status={d.status} />
            </div>
            <p className="mt-0.5 text-sm text-gray-600">
              {getMaterialsSummary(d.materials_json)}
            </p>
            {d.actual_delivery_date && (
              <p className="mt-0.5 text-xs text-gray-400">
                Delivered:{' '}
                {new Date(d.actual_delivery_date).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---- DEFICITS TAB ---- */
function DeficitsTab({
  items,
  isLoading,
}: {
  items: MaterialItem[];
  isLoading: boolean;
}) {
  if (isLoading) return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  if (items.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">All materials above minimum balance</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((m) => (
        <div
          key={m.id}
          className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
        >
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold">{m.name}</span>
              <Badge status={m.material_type} />
            </div>
            <p className="mt-0.5 text-xs text-gray-400">
              {m.supplier_name
                ? `Supplier: ${m.supplier_name}`
                : 'No supplier assigned'}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600">
              {m.balance} / {m.min_balance} {m.unit}
            </p>
            {m.deficit != null && m.deficit > 0 && (
              <p className="text-sm font-bold text-red-600">
                -{m.deficit} {m.unit}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---- SUPPLIERS TAB ---- */
function SuppliersTab({
  suppliers,
  isLoading,
}: {
  suppliers: SupplierItem[];
  isLoading: boolean;
}) {
  if (isLoading) return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  if (suppliers.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No suppliers configured</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {suppliers.map((s) => (
        <Card key={s.id}>
          <div className="flex items-center justify-between">
            <span className="font-semibold">{s.name}</span>
            <Badge
              status={s.is_active ? 'active' : 'inactive'}
              label={s.is_active ? 'Active' : 'Inactive'}
            />
          </div>
          {s.contact_person && (
            <p className="mt-1 text-sm text-gray-600">{s.contact_person}</p>
          )}
          {s.phone && (
            <p className="mt-0.5 text-sm text-gray-500">{s.phone}</p>
          )}
          <p className="mt-1 text-xs text-gray-400">
            Lead time: {s.default_lead_time_days} days
          </p>
          {s.material_types && s.material_types.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {s.material_types.map((mt) => (
                <span
                  key={mt}
                  className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600"
                >
                  {mt}
                </span>
              ))}
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
