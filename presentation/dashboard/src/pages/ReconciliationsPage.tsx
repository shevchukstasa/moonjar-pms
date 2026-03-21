import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useUiStore } from '@/stores/uiStore';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { useFactories } from '@/hooks/useFactories';
import {
  reconciliationsApi,
  type Reconciliation,
  type ReconciliationItem,
  type ReconciliationItemInput,
} from '@/api/reconciliations';
import { materialsApi } from '@/api/materials';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { Dialog } from '@/components/ui/Dialog';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { FactorySelector } from '@/components/layout/FactorySelector';

type StatusFilter = 'all' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  scheduled: { label: 'Scheduled', className: 'bg-blue-100 text-blue-700' },
  draft: { label: 'Draft', className: 'bg-gray-100 text-gray-600' },
  in_progress: { label: 'In Progress', className: 'bg-yellow-100 text-yellow-700' },
  completed: { label: 'Completed', className: 'bg-green-100 text-green-700' },
  cancelled: { label: 'Cancelled', className: 'bg-red-100 text-red-600' },
};

/* ──────────────────────────────────────────────────── */
/*  Main Page                                           */
/* ──────────────────────────────────────────────────── */

export default function ReconciliationsPage() {
  const qc = useQueryClient();
  const factoryId = useUiStore((s) => s.activeFactoryId);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [showNewDialog, setShowNewDialog] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const deleteMut = useMutation({
    mutationFn: (id: string) => reconciliationsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reconciliations'] });
      setDeleteId(null);
    },
  });

  const params: Record<string, string> = {};
  if (factoryId) params.factory_id = factoryId;

  const { data, isLoading } = useQuery({
    queryKey: ['reconciliations', params],
    queryFn: () => reconciliationsApi.list(params),
  });

  const reconciliations: Reconciliation[] = data?.items || [];
  const filtered =
    statusFilter === 'all'
      ? reconciliations
      : reconciliations.filter((r) => r.status === statusFilter);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reconciliations</h1>
          <p className="mt-1 text-sm text-gray-500">Inventory checks and stock adjustments</p>
        </div>
        <div className="flex items-center gap-3">
          <FactorySelector />
          <Button onClick={() => setShowNewDialog(true)}>+ New Reconciliation</Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        {(['all', 'in_progress', 'completed', 'scheduled', 'cancelled'] as const).map((s) => (
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

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <div className="text-xs text-gray-500">Total</div>
          <div className="mt-1 text-2xl font-bold">{reconciliations.length}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">In Progress</div>
          <div className="mt-1 text-2xl font-bold text-yellow-600">
            {reconciliations.filter((r) => r.status === 'in_progress').length}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Completed</div>
          <div className="mt-1 text-2xl font-bold text-green-600">
            {reconciliations.filter((r) => r.status === 'completed').length}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Scheduled</div>
          <div className="mt-1 text-2xl font-bold text-blue-600">
            {reconciliations.filter((r) => r.status === 'scheduled').length}
          </div>
        </Card>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-lg font-medium text-gray-400">No reconciliations found</p>
          <p className="mt-1 text-sm text-gray-400">
            Create a new inventory check to get started
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3" />
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Factory</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Notes</th>
                <th className="px-4 py-3">Completed</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((r) => (
                <ReconciliationRow key={r.id} reconciliation={r} onDelete={
                  (r.status === 'draft' || r.status === 'in_progress' || r.status === 'scheduled')
                    ? () => setDeleteId(r.id)
                    : undefined
                } />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* New Reconciliation Dialog */}
      {showNewDialog && (
        <NewReconciliationDialog
          onClose={() => setShowNewDialog(false)}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Reconciliation">
        <p className="text-sm text-gray-600">Are you sure you want to delete this reconciliation? This action will be logged.</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => deleteId && deleteMut.mutate(deleteId)} disabled={deleteMut.isPending}>
            {deleteMut.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Reconciliation Row (expandable)                     */
/* ──────────────────────────────────────────────────── */

function ReconciliationRow({ reconciliation: r, onDelete }: { reconciliation: Reconciliation; onDelete?: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const { data: factoriesData } = useFactories();
  const factories = factoriesData?.items || [];
  const factory = factories.find((f) => f.id === r.factory_id);
  const badge = STATUS_BADGES[r.status] || STATUS_BADGES.in_progress;

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className="cursor-pointer hover:bg-gray-50"
      >
        <td className="px-4 py-3 text-gray-400 w-8">
          <span className={`inline-block transition-transform ${expanded ? 'rotate-90' : ''}`}>
            {'\u25B6'}
          </span>
        </td>
        <td className="px-4 py-3 font-medium whitespace-nowrap">
          {new Date(r.created_at).toLocaleDateString()}
        </td>
        <td className="px-4 py-3">{factory?.name || r.factory_id.slice(0, 8)}</td>
        <td className="px-4 py-3">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.className}`}
          >
            {badge.label}
          </span>
        </td>
        <td className="px-4 py-3 text-gray-500 max-w-[200px] truncate">
          {r.notes || '\u2014'}
        </td>
        <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
          {r.completed_at ? new Date(r.completed_at).toLocaleDateString() : '\u2014'}
        </td>
        <td className="px-4 py-3 text-right">
          {onDelete && (
            <Button
              variant="ghost"
              size="sm"
              className="text-red-600"
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
            >
              Delete
            </Button>
          )}
        </td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={7} className="bg-gray-50 px-6 py-4">
            <ReconciliationDetail reconciliation={r} />
          </td>
        </tr>
      )}
    </>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Reconciliation Detail (items table + actions)       */
/* ──────────────────────────────────────────────────── */

function ReconciliationDetail({ reconciliation: r }: { reconciliation: Reconciliation }) {
  const qc = useQueryClient();
  const [showAddItems, setShowAddItems] = useState(false);
  const [showConfirmComplete, setShowConfirmComplete] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['reconciliation-items', r.id],
    queryFn: () => reconciliationsApi.listItems(r.id),
  });

  const items: ReconciliationItem[] = data?.items || [];

  const completeMutation = useMutation({
    mutationFn: () => reconciliationsApi.complete(r.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reconciliations'] });
      qc.invalidateQueries({ queryKey: ['reconciliation-items', r.id] });
      setShowConfirmComplete(false);
    },
  });

  const isInProgress = r.status === 'in_progress';

  return (
    <div className="space-y-4">
      {/* Action buttons */}
      {isInProgress && (
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowAddItems(true)}>
            + Add Items
          </Button>
          <Button
            onClick={() => setShowConfirmComplete(true)}
            disabled={items.length === 0}
          >
            Complete Reconciliation
          </Button>
        </div>
      )}

      {/* Items table */}
      {isLoading ? (
        <div className="flex justify-center py-6">
          <Spinner className="h-6 w-6" />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center">
          <p className="text-sm text-gray-400">No items recorded yet</p>
          {isInProgress && (
            <p className="mt-1 text-xs text-gray-400">
              Click "Add Items" to start recording inventory counts
            </p>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-2.5">Material</th>
                <th className="px-4 py-2.5 text-right">Expected</th>
                <th className="px-4 py-2.5 text-right">Actual</th>
                <th className="px-4 py-2.5 text-right">Difference</th>
                <th className="px-4 py-2.5">Reason</th>
                <th className="px-4 py-2.5">Explanation</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((item) => {
                const diff = item.difference;
                const diffColor =
                  Math.abs(diff) < 0.001
                    ? 'text-green-600'
                    : 'text-red-600 font-semibold';
                const rowBg =
                  Math.abs(diff) < 0.001 ? '' : 'bg-red-50/40';

                return (
                  <tr key={item.id} className={rowBg}>
                    <td className="px-4 py-2.5 font-medium">{item.material_name}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {item.system_quantity.toFixed(2)}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {item.actual_quantity.toFixed(2)}
                    </td>
                    <td className={`px-4 py-2.5 text-right tabular-nums ${diffColor}`}>
                      {diff > 0 ? '+' : ''}
                      {diff.toFixed(2)}
                    </td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs">
                      {item.reason ? item.reason.replace(/_/g, ' ') : '\u2014'}
                    </td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs max-w-[200px] truncate">
                      {item.explanation || '\u2014'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {/* Summary row */}
          <div className="flex items-center justify-between border-t bg-gray-50 px-4 py-2.5 text-xs font-medium text-gray-500">
            <span>{items.length} item{items.length !== 1 ? 's' : ''}</span>
            <span>
              Discrepancies:{' '}
              <span className="text-red-600">
                {items.filter((i) => Math.abs(i.difference) >= 0.001).length}
              </span>
            </span>
          </div>
        </div>
      )}

      {/* Add Items Dialog */}
      {showAddItems && (
        <AddItemsDialog
          reconciliationId={r.id}
          factoryId={r.factory_id}
          onClose={() => setShowAddItems(false)}
        />
      )}

      {/* Confirm Complete */}
      <ConfirmDialog
        open={showConfirmComplete}
        onClose={() => setShowConfirmComplete(false)}
        onConfirm={() => completeMutation.mutate()}
        title="Complete Reconciliation"
        message={`This will finalize the reconciliation and apply stock adjustments for ${items.filter((i) => Math.abs(i.difference) >= 0.001).length} discrepancies. This action cannot be undone.`}
      />

      {completeMutation.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {(completeMutation.error as any)?.response?.data?.detail ||
            'Failed to complete reconciliation'}
        </div>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  New Reconciliation Dialog                           */
/* ──────────────────────────────────────────────────── */

function NewReconciliationDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const user = useCurrentUser();
  const { data: factoriesData } = useFactories();
  const allFactories = factoriesData?.items || [];

  // PM only sees their assigned factories
  const GLOBAL_ROLES = new Set(['owner', 'administrator', 'ceo']);
  const userFactoryIds = user?.factories?.map((f: { id?: string; factory_id?: string }) => f.id || f.factory_id) || [];
  const isGlobal = user && GLOBAL_ROLES.has(user.role);
  const factories = isGlobal ? allFactories : allFactories.filter((f) => userFactoryIds.includes(f.id));

  const [selectedFactory, setSelectedFactory] = useState('');
  const [notes, setNotes] = useState('');

  // Auto-select if only one factory
  useEffect(() => {
    if (!selectedFactory && factories.length === 1) {
      setSelectedFactory(factories[0].id);
    }
  }, [factories, selectedFactory]);

  const createMutation = useMutation({
    mutationFn: (data: Parameters<typeof reconciliationsApi.create>[0]) =>
      reconciliationsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reconciliations'] });
      onClose();
    },
  });

  const handleSubmit = () => {
    if (!selectedFactory || !user) return;
    createMutation.mutate({
      factory_id: selectedFactory,
      started_by: user.id,
      status: 'in_progress',
      notes: notes || undefined,
    });
  };

  return (
    <Dialog open onClose={onClose} title="New Reconciliation">
      <div className="space-y-4">
        {factories.length > 1 ? (
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Factory *</label>
          <select
            value={selectedFactory}
            onChange={(e) => setSelectedFactory(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">Select factory...</option>
            {factories.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </div>
        ) : factories.length === 1 ? (
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Factory</label>
          <p className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">{factories[0].name}</p>
        </div>
        ) : null}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Notes (optional)</label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Purpose of this reconciliation..."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!selectedFactory || createMutation.isPending}
          >
            {createMutation.isPending && <Spinner className="h-4 w-4 mr-2" />}
            Create
          </Button>
        </div>
        {createMutation.isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {(createMutation.error as any)?.response?.data?.detail ||
              'Failed to create reconciliation'}
          </div>
        )}
      </div>
    </Dialog>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Add Items Dialog                                    */
/* ──────────────────────────────────────────────────── */

const REASON_OPTIONS = [
  { value: '', label: '-- select --' },
  { value: 'natural_losses', label: 'Natural Losses' },
  { value: 'formula_inaccuracy', label: 'Formula Inaccuracy' },
  { value: 'counting_error', label: 'Counting Error' },
  { value: 'theft_damage', label: 'Theft / Damage' },
  { value: 'other', label: 'Other' },
];

interface ItemRow {
  material_id: string;
  expected_qty: string;
  actual_qty: string;
  reason: string;
  explanation: string;
}

const emptyRow = (): ItemRow => ({
  material_id: '',
  expected_qty: '',
  actual_qty: '',
  reason: '',
  explanation: '',
});

function AddItemsDialog({
  reconciliationId,
  factoryId,
  onClose,
}: {
  reconciliationId: string;
  factoryId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [rows, setRows] = useState<ItemRow[]>([emptyRow()]);

  const { data: materialsData, isLoading: materialsLoading } = useQuery({
    queryKey: ['materials-for-recon', factoryId],
    queryFn: () =>
      materialsApi.list({ factory_id: factoryId, per_page: 500 }),
  });

  const materials = materialsData?.items || [];

  const addItemsMutation = useMutation({
    mutationFn: (items: ReconciliationItemInput[]) =>
      reconciliationsApi.addItems(reconciliationId, items),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reconciliation-items', reconciliationId] });
      onClose();
    },
  });

  const updateRow = (index: number, field: keyof ItemRow, value: string) => {
    setRows((prev) =>
      prev.map((r, i) => (i === index ? { ...r, [field]: value } : r)),
    );
  };

  const removeRow = (index: number) => {
    setRows((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = () => {
    const validRows = rows.filter((r) => r.material_id && r.expected_qty && r.actual_qty);
    if (validRows.length === 0) return;

    const items: ReconciliationItemInput[] = validRows.map((r) => ({
      material_id: r.material_id,
      expected_qty: parseFloat(r.expected_qty),
      actual_qty: parseFloat(r.actual_qty),
      reason: r.reason || undefined,
      explanation: r.explanation || undefined,
    }));

    addItemsMutation.mutate(items);
  };

  const validCount = rows.filter((r) => r.material_id && r.expected_qty && r.actual_qty).length;

  return (
    <Dialog open onClose={onClose} title="Add Reconciliation Items" className="max-w-4xl">
      <div className="space-y-4">
        {materialsLoading ? (
          <div className="flex justify-center py-6">
            <Spinner className="h-6 w-6" />
          </div>
        ) : (
          <>
            <div className="max-h-[60vh] overflow-y-auto space-y-3">
              {rows.map((row, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-12 gap-2 items-end rounded-lg border border-gray-200 bg-white p-3"
                >
                  {/* Material */}
                  <div className="col-span-3">
                    {idx === 0 && (
                      <label className="block text-[10px] font-medium text-gray-500 mb-0.5">
                        Material
                      </label>
                    )}
                    <select
                      value={row.material_id}
                      onChange={(e) => updateRow(idx, 'material_id', e.target.value)}
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs"
                    >
                      <option value="">Select...</option>
                      {materials.map((m: any) => (
                        <option key={m.id} value={m.id}>
                          {m.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  {/* Expected */}
                  <div className="col-span-2">
                    {idx === 0 && (
                      <label className="block text-[10px] font-medium text-gray-500 mb-0.5">
                        Expected Qty
                      </label>
                    )}
                    <input
                      type="number"
                      step="0.01"
                      value={row.expected_qty}
                      onChange={(e) => updateRow(idx, 'expected_qty', e.target.value)}
                      placeholder="0.00"
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs"
                    />
                  </div>
                  {/* Actual */}
                  <div className="col-span-2">
                    {idx === 0 && (
                      <label className="block text-[10px] font-medium text-gray-500 mb-0.5">
                        Actual Qty
                      </label>
                    )}
                    <input
                      type="number"
                      step="0.01"
                      value={row.actual_qty}
                      onChange={(e) => updateRow(idx, 'actual_qty', e.target.value)}
                      placeholder="0.00"
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs"
                    />
                  </div>
                  {/* Reason */}
                  <div className="col-span-2">
                    {idx === 0 && (
                      <label className="block text-[10px] font-medium text-gray-500 mb-0.5">
                        Reason
                      </label>
                    )}
                    <select
                      value={row.reason}
                      onChange={(e) => updateRow(idx, 'reason', e.target.value)}
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs"
                    >
                      {REASON_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  {/* Explanation */}
                  <div className="col-span-2">
                    {idx === 0 && (
                      <label className="block text-[10px] font-medium text-gray-500 mb-0.5">
                        Explanation
                      </label>
                    )}
                    <input
                      type="text"
                      value={row.explanation}
                      onChange={(e) => updateRow(idx, 'explanation', e.target.value)}
                      placeholder="Details..."
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs"
                    />
                  </div>
                  {/* Remove */}
                  <div className="col-span-1 flex justify-center">
                    {rows.length > 1 && (
                      <button
                        onClick={() => removeRow(idx)}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
                        title="Remove row"
                      >
                        {'\u2715'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between">
              <Button
                variant="ghost"
                onClick={() => setRows((prev) => [...prev, emptyRow()])}
              >
                + Add Row
              </Button>
              <span className="text-xs text-gray-500">
                {validCount} valid item{validCount !== 1 ? 's' : ''}
              </span>
            </div>
          </>
        )}

        <div className="flex justify-end gap-2 border-t pt-3">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={validCount === 0 || addItemsMutation.isPending}
          >
            {addItemsMutation.isPending && <Spinner className="h-4 w-4 mr-2" />}
            Add {validCount} Item{validCount !== 1 ? 's' : ''}
          </Button>
        </div>

        {addItemsMutation.isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {(addItemsMutation.error as any)?.response?.data?.detail ||
              'Failed to add items'}
          </div>
        )}
      </div>
    </Dialog>
  );
}
