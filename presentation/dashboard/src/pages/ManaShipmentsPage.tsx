import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useUiStore } from '@/stores/uiStore';
import { useFactories } from '@/hooks/useFactories';
import {
  manaShipmentsApi,
  type ManaShipment,
  type ManaShipmentItem,
} from '@/api/manaShipments';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { Dialog } from '@/components/ui/Dialog';
import { FactorySelector } from '@/components/layout/FactorySelector';

type StatusFilter = 'all' | 'pending' | 'confirmed' | 'shipped';

const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  pending: { label: 'Pending', className: 'bg-yellow-100 text-yellow-700' },
  confirmed: { label: 'Confirmed', className: 'bg-blue-100 text-blue-700' },
  shipped: { label: 'Shipped', className: 'bg-green-100 text-green-700' },
};

/* ──────────────────────────────────────────────────── */
/*  Main Page                                           */
/* ──────────────────────────────────────────────────── */

export default function ManaShipmentsPage() {
  const qc = useQueryClient();
  const factoryId = useUiStore((s) => s.activeFactoryId);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const deleteMut = useMutation({
    mutationFn: (id: string) => manaShipmentsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mana-shipments'] });
      setDeleteId(null);
    },
  });

  const params: Record<string, string> = {};
  if (factoryId) params.factory_id = factoryId;

  const { data, isLoading } = useQuery({
    queryKey: ['mana-shipments', params],
    queryFn: () => manaShipmentsApi.list(params),
  });

  const shipments: ManaShipment[] = data?.items || [];
  const filtered =
    statusFilter === 'all'
      ? shipments
      : shipments.filter((s) => s.status === statusFilter);

  const now = new Date();
  const thisMonth = shipments.filter(
    (s) => new Date(s.created_at).getMonth() === now.getMonth() &&
           new Date(s.created_at).getFullYear() === now.getFullYear(),
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mana Shipments</h1>
          <p className="mt-1 text-sm text-gray-500">
            Defective tiles routed to Mana for external glazing
          </p>
        </div>
        <FactorySelector />
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <div className="text-xs text-gray-500">Total Shipments</div>
          <div className="mt-1 text-2xl font-bold">{shipments.length}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Pending Confirmation</div>
          <div className="mt-1 text-2xl font-bold text-yellow-600">
            {shipments.filter((s) => s.status === 'pending').length}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Shipped</div>
          <div className="mt-1 text-2xl font-bold text-green-600">
            {shipments.filter((s) => s.status === 'shipped').length}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">This Month</div>
          <div className="mt-1 text-2xl font-bold text-blue-600">{thisMonth.length}</div>
        </Card>
      </div>

      {/* Status filter tabs */}
      <div className="flex flex-wrap items-center gap-2">
        {(['all', 'pending', 'confirmed', 'shipped'] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
              statusFilter === s
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {s === 'all' ? 'All' : STATUS_BADGES[s]?.label || s}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-lg font-medium text-gray-400">No Mana shipments found</p>
          <p className="mt-1 text-sm text-gray-400">
            Shipments are created automatically when defective tiles are routed to Mana
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 w-8" />
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Factory</th>
                <th className="px-4 py-3">Items</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Confirmed By</th>
                <th className="px-4 py-3">Shipped At</th>
                <th className="px-4 py-3">Notes</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((s) => (
                <ShipmentRow
                  key={s.id}
                  shipment={s}
                  onDelete={
                    s.status !== 'shipped' ? () => setDeleteId(s.id) : undefined
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Shipment">
        <p className="text-sm text-gray-600">
          Are you sure you want to delete this Mana shipment? This action cannot be undone.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteId && deleteMut.mutate(deleteId)}
            disabled={deleteMut.isPending}
          >
            {deleteMut.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Shipment Row (expandable)                           */
/* ──────────────────────────────────────────────────── */

function ShipmentRow({
  shipment: s,
  onDelete,
}: {
  shipment: ManaShipment;
  onDelete?: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const qc = useQueryClient();
  const { data: factoriesData } = useFactories();
  const factories = factoriesData?.items || [];
  const factory = factories.find((f) => f.id === s.factory_id);
  const badge = STATUS_BADGES[s.status] || STATUS_BADGES.pending;

  const confirmMut = useMutation({
    mutationFn: () => manaShipmentsApi.confirm(s.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mana-shipments'] }),
  });

  const shipMut = useMutation({
    mutationFn: () => manaShipmentsApi.ship(s.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mana-shipments'] }),
  });

  const totalQty = (s.items_json || []).reduce(
    (sum, item) => sum + (item.quantity || 0),
    0,
  );

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className="cursor-pointer hover:bg-gray-50"
      >
        <td className="px-4 py-3 text-gray-400 w-8">
          <span
            className={`inline-block transition-transform ${expanded ? 'rotate-90' : ''}`}
          >
            {'▶'}
          </span>
        </td>
        <td className="px-4 py-3 font-medium whitespace-nowrap">
          {new Date(s.created_at).toLocaleDateString()}
        </td>
        <td className="px-4 py-3">{factory?.name || s.factory_id.slice(0, 8)}</td>
        <td className="px-4 py-3">
          {(s.items_json || []).length} items ({totalQty} pcs)
        </td>
        <td className="px-4 py-3">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.className}`}
          >
            {badge.label}
          </span>
        </td>
        <td className="px-4 py-3 text-gray-500">
          {s.confirmed_by ? s.confirmed_by.slice(0, 8) + '...' : '—'}
        </td>
        <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
          {s.shipped_at ? new Date(s.shipped_at).toLocaleDateString() : '—'}
        </td>
        <td className="px-4 py-3 text-gray-500 max-w-[200px] truncate">
          {s.notes || '—'}
        </td>
        <td className="px-4 py-3 text-right">
          <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
            {s.status === 'pending' && (
              <Button
                size="sm"
                onClick={() => confirmMut.mutate()}
                disabled={confirmMut.isPending}
              >
                {confirmMut.isPending ? '...' : 'Confirm'}
              </Button>
            )}
            {s.status === 'confirmed' && (
              <Button
                size="sm"
                onClick={() => shipMut.mutate()}
                disabled={shipMut.isPending}
              >
                {shipMut.isPending ? '...' : 'Ship'}
              </Button>
            )}
            {onDelete && (
              <Button size="sm" variant="danger" onClick={onDelete}>
                Delete
              </Button>
            )}
          </div>
        </td>
      </tr>

      {/* Expanded detail */}
      {expanded && (
        <tr>
          <td colSpan={9} className="bg-gray-50 px-8 py-4">
            <div className="text-xs font-semibold uppercase text-gray-400 mb-2">
              Shipment Items
            </div>
            {(s.items_json || []).length === 0 ? (
              <p className="text-sm text-gray-400">No items</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500">
                    <th className="text-left pb-1">Color</th>
                    <th className="text-left pb-1">Size</th>
                    <th className="text-right pb-1">Qty</th>
                    <th className="text-left pb-1 pl-4">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {(s.items_json as ManaShipmentItem[]).map((item, idx) => (
                    <tr key={idx} className="border-t border-gray-200">
                      <td className="py-1">{item.color}</td>
                      <td className="py-1">{item.size}</td>
                      <td className="py-1 text-right">{item.quantity}</td>
                      <td className="py-1 pl-4 text-gray-500">{item.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
