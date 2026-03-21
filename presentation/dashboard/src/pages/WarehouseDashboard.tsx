import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { useUiStore } from '@/stores/uiStore';
import { formatDateTime, formatDate } from '@/lib/format';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import {
  useMaterials,
  useLowStock,
  useCreateTransaction,
  useDeleteTransaction,
  useMaterialTransactions,
  type MaterialItem,
  type TransactionItem,
} from '@/hooks/useMaterials';
import { usePurchaseRequests, type PurchaseRequestItem } from '@/hooks/usePurchaseRequests';

const TABS = [
  { id: 'inventory', label: 'Inventory' },
  { id: 'low-stock', label: 'Low Stock' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'requests', label: 'Requests' },
];

export default function WarehouseDashboard() {
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);
  const [tab, setTab] = useState('inventory');

  const factoryParams = activeFactoryId ? { factory_id: activeFactoryId } : undefined;
  const { data: materialsData, isLoading: materialsLoading, isError: materialsError } = useMaterials(factoryParams);
  const materials = materialsData?.items || [];
  const { data: lowStockData, isLoading: lowStockLoading, isError: lowStockError } = useLowStock(activeFactoryId || undefined);
  const lowStockItems = lowStockData?.items || [];
  const { data: requestsData, isLoading: requestsLoading, isError: requestsError } = usePurchaseRequests(factoryParams);
  const requests = requestsData?.items || [];

  const hasError = materialsError || lowStockError || requestsError;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Warehouse</h1>
        <p className="mt-1 text-sm text-gray-500">Inventory, deliveries, purchase requests</p>
      </div>

      {/* API Error */}
      {hasError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">⚠ Error loading warehouse data. Try refreshing.</p>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="text-center">
          <p className="text-2xl font-bold text-gray-900">{materials.length}</p>
          <p className="text-xs text-gray-500">Total Materials</p>
        </Card>
        <Card className="text-center">
          <p className="text-2xl font-bold text-orange-600">{lowStockItems.length}</p>
          <p className="text-xs text-gray-500">Low Stock</p>
        </Card>
        <Card className="text-center">
          <p className="text-2xl font-bold text-blue-600">{requests.length}</p>
          <p className="text-xs text-gray-500">Pending Requests</p>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} activeTab={tab} onChange={setTab} />

      {/* Tab Content */}
      {tab === 'inventory' && (
        <InventoryTab materials={materials} isLoading={materialsLoading} />
      )}
      {tab === 'low-stock' && (
        <LowStockTab items={lowStockItems} isLoading={lowStockLoading} />
      )}
      {tab === 'transactions' && (
        <TransactionsTab materials={materials} isLoading={materialsLoading} />
      )}
      {tab === 'requests' && (
        <PurchaseRequestsTab requests={requests} isLoading={requestsLoading} />
      )}
    </div>
  );
}

/* ---- INVENTORY TAB ---- */

function InventoryTab({ materials, isLoading }: { materials: MaterialItem[]; isLoading: boolean }) {
  const [search, setSearch] = useState('');

  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  }

  const filtered = search
    ? materials.filter((m) => m.name.toLowerCase().includes(search.toLowerCase()))
    : materials;

  if (materials.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No materials in inventory</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search */}
      <input
        type="text"
        placeholder="Search materials..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
      />

      {filtered.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
          <p className="text-gray-400">No materials match your search</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((m) => (
            <div
              key={m.id}
              className="rounded-lg border border-gray-200 bg-white p-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-900">{m.name}</span>
                <Badge status={m.material_type} />
              </div>
              <div className="mt-2 flex items-baseline gap-1">
                <span className={`text-lg font-bold ${m.is_low_stock ? 'text-red-600' : 'text-green-600'}`}>
                  {m.balance}
                </span>
                <span className="text-sm text-gray-400">/ {m.min_balance}</span>
                <span className="text-xs text-gray-400">{m.unit}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---- LOW STOCK TAB ---- */

function LowStockTab({ items, isLoading }: { items: MaterialItem[]; isLoading: boolean }) {
  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  }

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
            <p className="mt-0.5 text-sm text-gray-500">
              Balance: {m.balance} / {m.min_balance} {m.unit}
            </p>
          </div>
          <span className="text-lg font-bold text-red-600">
            -{m.deficit ?? (m.min_balance - m.balance)}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ---- TRANSACTIONS TAB ---- */

type FormMode = 'none' | 'receive' | 'write-off';

const WRITE_OFF_REASONS = ['breakage', 'loss', 'damage', 'expired', 'adjustment', 'other'] as const;

function TransactionsTab({
  materials,
  isLoading,
}: {
  materials: MaterialItem[];
  isLoading: boolean;
}) {
  const [selectedMaterialId, setSelectedMaterialId] = useState<string | undefined>(undefined);
  const [formMode, setFormMode] = useState<FormMode>('none');
  const [qty, setQty] = useState(0);
  const [reason, setReason] = useState('breakage');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');

  const createTransaction = useCreateTransaction();
  const deleteTxMut = useDeleteTransaction();
  const [deleteTxId, setDeleteTxId] = useState<string | null>(null);
  const { data: txData, isLoading: txLoading } = useMaterialTransactions(selectedMaterialId);
  const transactions = txData?.items || [];

  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  }

  if (materials.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No materials available</p>
      </div>
    );
  }

  const resetForm = () => {
    setFormMode('none');
    setQty(0);
    setReason('breakage');
    setNotes('');
    setError('');
  };

  const handleSubmit = async () => {
    if (!selectedMaterialId || qty <= 0) return;
    setError('');
    try {
      const selectedMat = materials.find((m) => m.id === selectedMaterialId);
      await createTransaction.mutateAsync({
        material_id: selectedMaterialId,
        factory_id: selectedMat?.factory_id ?? '',
        type: formMode === 'receive' ? 'receive' : 'manual_write_off',
        quantity: qty,
        reason: formMode === 'write-off' ? reason : undefined,
        notes: notes || undefined,
      });
      resetForm();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setError(resp?.detail || 'Failed to create transaction');
    }
  };

  const fmtDate = (d: string | null) => d ? formatDateTime(d) : '--';

  const txBadge = (type: string) => {
    if (type === 'receive') return <Badge status="receive" label="Receive" />;
    if (type === 'manual_write_off') return <Badge status="manual_write_off" label="Write Off" />;
    return <Badge status={type} label={type.replace(/_/g, ' ')} />;
  };

  return (
    <div className="space-y-4">
      {/* Material selector */}
      <select
        value={selectedMaterialId || ''}
        onChange={(e) => {
          setSelectedMaterialId(e.target.value || undefined);
          resetForm();
        }}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
      >
        <option value="">Select material...</option>
        {materials.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name} ({m.balance} {m.unit})
          </option>
        ))}
      </select>

      {selectedMaterialId && (
        <>
          {/* Action buttons */}
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={formMode === 'receive' ? 'primary' : 'secondary'}
              onClick={() => setFormMode(formMode === 'receive' ? 'none' : 'receive')}
            >
              Receive
            </Button>
            <Button
              size="sm"
              variant={formMode === 'write-off' ? 'danger' : 'secondary'}
              onClick={() => setFormMode(formMode === 'write-off' ? 'none' : 'write-off')}
            >
              Write Off
            </Button>
          </div>

          {/* Inline form */}
          {formMode !== 'none' && (
            <Card className={formMode === 'receive' ? 'border-green-200 bg-green-50/30' : 'border-red-200 bg-red-50/30'}>
              <h4 className="mb-3 text-sm font-semibold text-gray-900">
                {formMode === 'receive' ? 'Receive Material' : 'Write Off Material'}
              </h4>

              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className="w-20 text-sm font-medium text-gray-700">Quantity</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={1}
                    value={qty || ''}
                    onChange={(e) => setQty(Math.max(0, parseInt(e.target.value) || 0))}
                    placeholder="0"
                    className="min-h-[44px] flex-1 rounded-md border border-gray-300 px-3 py-2 text-center text-lg font-semibold focus:border-primary-500 focus:outline-none"
                  />
                </div>

                {formMode === 'write-off' && (
                  <div className="flex items-center gap-3">
                    <span className="w-20 text-sm font-medium text-gray-700">Reason</span>
                    <select
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                    >
                      {WRITE_OFF_REASONS.map((r) => (
                        <option key={r} value={r}>{r[0].toUpperCase() + r.slice(1)}</option>
                      ))}
                    </select>
                  </div>
                )}

                <textarea
                  placeholder="Notes (optional)"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  rows={2}
                />
              </div>

              {error && <p className="mt-2 text-sm text-red-500">{error}</p>}

              <div className="mt-3 flex gap-2">
                <Button
                  className="flex-1"
                  variant={formMode === 'receive' ? 'primary' : 'danger'}
                  onClick={handleSubmit}
                  disabled={qty <= 0 || createTransaction.isPending}
                >
                  {createTransaction.isPending
                    ? 'Submitting...'
                    : formMode === 'receive'
                      ? 'Confirm Receive'
                      : 'Confirm Write Off'}
                </Button>
                <Button variant="ghost" onClick={resetForm}>
                  Cancel
                </Button>
              </div>
            </Card>
          )}

          {/* Transaction list */}
          {txLoading ? (
            <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>
          ) : transactions.length === 0 ? (
            <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
              <p className="text-gray-400">No transactions for this material</p>
            </div>
          ) : (
            <div className="space-y-2">
              {transactions.map((tx: TransactionItem) => (
                <div
                  key={tx.id}
                  className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      {txBadge(tx.type)}
                      <span className="text-sm text-gray-400">{fmtDate(tx.created_at)}</span>
                    </div>
                    {tx.notes && (
                      <p className="mt-0.5 text-xs text-gray-500">{tx.notes}</p>
                    )}
                    {tx.created_by_name && (
                      <p className="mt-0.5 text-xs text-gray-400">by {tx.created_by_name}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-lg font-bold ${
                        tx.type === 'receive' ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {tx.type === 'receive' ? '+' : '-'}{tx.quantity}
                    </span>
                    <Button
                      size="sm"
                      variant="danger"
                      disabled={deleteTxMut.isPending}
                      onClick={() => setDeleteTxId(tx.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <ConfirmDialog
        open={!!deleteTxId}
        onClose={() => setDeleteTxId(null)}
        onConfirm={() => { if (deleteTxId) deleteTxMut.mutate(deleteTxId); setDeleteTxId(null); }}
        title="Delete Transaction"
        message="Are you sure you want to delete this transaction? The stock balance will be reversed. This action cannot be undone."
      />
    </div>
  );
}

/* ---- PURCHASE REQUESTS TAB ---- */

function PurchaseRequestsTab({
  requests,
  isLoading,
}: {
  requests: PurchaseRequestItem[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  }

  if (requests.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No purchase requests</p>
      </div>
    );
  }

  const fmtDate = (d: string | null) => d ? formatDate(d) : '--';

  return (
    <div className="space-y-3">
      {requests.map((r) => (
        <div key={r.id} className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold">{r.supplier_name || 'No supplier'}</span>
              <Badge status={r.status} />
              <Badge status={r.source} />
            </div>
            <p className="mt-0.5 text-sm text-gray-500">
              Created: {fmtDate(r.created_at)}
              {r.expected_delivery_date && ` | Expected: ${fmtDate(r.expected_delivery_date)}`}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
