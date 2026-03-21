import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { finishedGoodsApi, type FinishedGoodsItem, type StockUpsertInput, type AvailabilityResponse } from '@/api/finishedGoods';
import { useFactories, type Factory } from '@/hooks/useFactories';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { Spinner } from '@/components/ui/Spinner';
import { Pagination } from '@/components/ui/Pagination';
import { SearchInput } from '@/components/ui/SearchInput';
import { cn } from '@/lib/cn';

// ── Helpers ──────────────────────────────────────────────────────────────

function availabilityColor(available: number, quantity: number): string {
  if (available <= 0) return 'text-red-600 bg-red-50';
  if (quantity > 0 && available / quantity <= 0.25) return 'text-yellow-700 bg-yellow-50';
  return 'text-green-700 bg-green-50';
}

const PER_PAGE = 50;

// ── Main Page ────────────────────────────────────────────────────────────

export default function FinishedGoodsPage() {
  const qc = useQueryClient();

  // Filters
  const [page, setPage] = useState(1);
  const [factoryFilter, setFactoryFilter] = useState('');
  const [colorSearch, setColorSearch] = useState('');
  const [debouncedColor, setDebouncedColor] = useState('');

  // Debounce color search
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const handleColorSearch = (value: string) => {
    setColorSearch(value);
    if (debounceTimer) clearTimeout(debounceTimer);
    const t = setTimeout(() => { setDebouncedColor(value); setPage(1); }, 300);
    setDebounceTimer(t);
  };

  // Dialog state
  const [upsertOpen, setUpsertOpen] = useState(false);
  const [editItem, setEditItem] = useState<FinishedGoodsItem | null>(null);
  const [availOpen, setAvailOpen] = useState(false);
  const [availResult, setAvailResult] = useState<AvailabilityResponse | null>(null);

  // Availability form state
  const [availColor, setAvailColor] = useState('');
  const [availSize, setAvailSize] = useState('');
  const [availNeeded, setAvailNeeded] = useState('');

  // Factories
  const { data: factoriesData } = useFactories();
  const factories: Factory[] = factoriesData?.items ?? [];
  const factoryOptions = useMemo(
    () => [{ value: '', label: 'All Factories' }, ...factories.map((f) => ({ value: f.id, label: f.name }))],
    [factories],
  );

  // Data query
  const { data, isLoading } = useQuery({
    queryKey: ['finished-goods', page, factoryFilter, debouncedColor],
    queryFn: () =>
      finishedGoodsApi.list({
        page,
        per_page: PER_PAGE,
        factory_id: factoryFilter || undefined,
        color: debouncedColor || undefined,
      }),
    placeholderData: keepPreviousData,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));

  // Totals
  const totals = useMemo(() => {
    let qty = 0, reserved = 0;
    for (const it of items) { qty += it.quantity; reserved += it.reserved_quantity; }
    return { qty, reserved, available: qty - reserved };
  }, [items]);

  // Mutations
  const upsertMut = useMutation({
    mutationFn: (data: StockUpsertInput) => finishedGoodsApi.upsert(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['finished-goods'] }); setUpsertOpen(false); setEditItem(null); },
  });

  const availMut = useMutation({
    mutationFn: (params: { color: string; size: string; needed: number }) => finishedGoodsApi.checkAvailability(params),
    onSuccess: (data) => setAvailResult(data),
  });

  const [deleteId, setDeleteId] = useState<string | null>(null);
  const deleteMut = useMutation({
    mutationFn: (id: string) => finishedGoodsApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['finished-goods'] }); setDeleteId(null); },
  });

  // ── Upsert form state ──
  const [form, setForm] = useState({ factory_id: '', color: '', size: '', collection: '', product_type: 'tile', quantity: '', reserved_quantity: '0' });

  const openCreate = () => {
    setEditItem(null);
    setForm({ factory_id: factories[0]?.id ?? '', color: '', size: '', collection: '', product_type: 'tile', quantity: '', reserved_quantity: '0' });
    setUpsertOpen(true);
  };

  const openEdit = (item: FinishedGoodsItem) => {
    setEditItem(item);
    setForm({
      factory_id: item.factory_id,
      color: item.color,
      size: item.size,
      collection: item.collection ?? '',
      product_type: item.product_type,
      quantity: String(item.quantity),
      reserved_quantity: String(item.reserved_quantity),
    });
    setUpsertOpen(true);
  };

  const handleSubmit = () => {
    upsertMut.mutate({
      factory_id: form.factory_id,
      color: form.color,
      size: form.size,
      collection: form.collection || undefined,
      product_type: form.product_type || 'tile',
      quantity: parseInt(form.quantity) || 0,
      reserved_quantity: parseInt(form.reserved_quantity) || 0,
    });
  };

  const handleCheckAvailability = () => {
    if (!availColor || !availSize || !availNeeded) return;
    availMut.mutate({ color: availColor, size: availSize, needed: parseInt(availNeeded) || 1 });
  };

  // ── Render ──
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Finished Goods</h1>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => { setAvailResult(null); setAvailOpen(true); }}>
            Check Availability
          </Button>
          <Button onClick={openCreate}>+ Add Stock</Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-56">
            <Select
              label="Factory"
              options={factoryOptions}
              value={factoryFilter}
              onChange={(e) => { setFactoryFilter(e.target.value); setPage(1); }}
            />
          </div>
          <div className="w-64">
            <label className="mb-1 block text-sm font-medium text-gray-700">Search by Color</label>
            <SearchInput
              value={colorSearch}
              onChange={(e) => handleColorSearch(e.target.value)}
              placeholder="Search color..."
              className="w-full"
            />
          </div>
          <div className="text-sm text-gray-500">
            {total} record{total !== 1 ? 's' : ''}
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20"><Spinner className="h-8 w-8" /></div>
        ) : items.length === 0 ? (
          <div className="py-20 text-center text-gray-400">No finished goods found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  <th className="px-4 py-3">Color</th>
                  <th className="px-4 py-3">Size</th>
                  <th className="px-4 py-3">Collection</th>
                  <th className="px-4 py-3">Factory</th>
                  <th className="px-4 py-3 text-right">Qty</th>
                  <th className="px-4 py-3 text-right">Reserved</th>
                  <th className="px-4 py-3 text-right">Available</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{item.color}</td>
                    <td className="px-4 py-3 text-gray-700">{item.size}</td>
                    <td className="px-4 py-3 text-gray-600">{item.collection || '-'}</td>
                    <td className="px-4 py-3 text-gray-600">{item.factory_name || '-'}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-900">{item.quantity}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-600">{item.reserved_quantity}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={cn('inline-block min-w-[3rem] rounded-full px-2 py-0.5 text-center text-xs font-semibold', availabilityColor(item.available, item.quantity))}>
                        {item.available}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex gap-1">
                        <Button variant="ghost" size="sm" onClick={() => openEdit(item)}>Edit</Button>
                        <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700" onClick={() => setDeleteId(item.id)}>Delete</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 bg-gray-50 font-semibold">
                  <td className="px-4 py-3" colSpan={4}>Totals (this page)</td>
                  <td className="px-4 py-3 text-right font-mono">{totals.qty}</td>
                  <td className="px-4 py-3 text-right font-mono">{totals.reserved}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={cn('inline-block min-w-[3rem] rounded-full px-2 py-0.5 text-center text-xs font-semibold', availabilityColor(totals.available, totals.qty))}>
                      {totals.available}
                    </span>
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center">
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
      )}

      {/* ── Upsert Dialog ── */}
      <Dialog open={upsertOpen} onClose={() => { setUpsertOpen(false); setEditItem(null); }} title={editItem ? 'Edit Stock' : 'Add Stock'} className="w-full max-w-md">
        <div className="space-y-4">
          <Select
            label="Factory"
            options={factories.map((f) => ({ value: f.id, label: f.name }))}
            value={form.factory_id}
            onChange={(e) => setForm((p) => ({ ...p, factory_id: e.target.value }))}
          />
          <Input
            label="Color"
            value={form.color}
            onChange={(e) => setForm((p) => ({ ...p, color: e.target.value }))}
            placeholder="e.g. Ocean Blue"
          />
          <Input
            label="Size"
            value={form.size}
            onChange={(e) => setForm((p) => ({ ...p, size: e.target.value }))}
            placeholder="e.g. 10x10"
          />
          <Input
            label="Collection"
            value={form.collection}
            onChange={(e) => setForm((p) => ({ ...p, collection: e.target.value }))}
            placeholder="Optional"
          />
          <Select
            label="Product Type"
            options={[
              { value: 'tile', label: 'Tile' },
              { value: 'brick', label: 'Brick' },
              { value: 'slab', label: 'Slab' },
              { value: 'other', label: 'Other' },
            ]}
            value={form.product_type}
            onChange={(e) => setForm((p) => ({ ...p, product_type: e.target.value }))}
          />
          <Input
            label="Quantity"
            type="number"
            min={0}
            value={form.quantity}
            onChange={(e) => setForm((p) => ({ ...p, quantity: e.target.value }))}
          />
          <Input
            label="Reserved Quantity"
            type="number"
            min={0}
            value={form.reserved_quantity}
            onChange={(e) => setForm((p) => ({ ...p, reserved_quantity: e.target.value }))}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => { setUpsertOpen(false); setEditItem(null); }}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={upsertMut.isPending || !form.factory_id || !form.color || !form.size}>
              {upsertMut.isPending ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
          {upsertMut.isError && (
            <p className="text-sm text-red-500">Error: {(upsertMut.error as Error)?.message || 'Failed to save'}</p>
          )}
        </div>
      </Dialog>

      {/* ── Availability Dialog ── */}
      <Dialog open={availOpen} onClose={() => setAvailOpen(false)} title="Check Availability" className="w-full max-w-lg">
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <Input
              label="Color"
              value={availColor}
              onChange={(e) => setAvailColor(e.target.value)}
              placeholder="Exact color"
            />
            <Input
              label="Size"
              value={availSize}
              onChange={(e) => setAvailSize(e.target.value)}
              placeholder="e.g. 10x10"
            />
            <Input
              label="Needed"
              type="number"
              min={1}
              value={availNeeded}
              onChange={(e) => setAvailNeeded(e.target.value)}
              placeholder="Qty"
            />
          </div>
          <Button onClick={handleCheckAvailability} disabled={availMut.isPending || !availColor || !availSize || !availNeeded}>
            {availMut.isPending ? 'Checking...' : 'Check'}
          </Button>

          {availResult && (
            <div className="mt-4 space-y-3 rounded-lg border bg-gray-50 p-4">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Need:</span>
                <span className="font-mono font-semibold">{availResult.needed}</span>
                <span className="mx-2 text-gray-300">|</span>
                <span className="text-sm font-medium">Total available:</span>
                <span className={cn('font-mono font-semibold', availResult.sufficient_total ? 'text-green-600' : 'text-red-600')}>
                  {availResult.total_available}
                </span>
              </div>

              {availResult.sufficient_total ? (
                <div className="rounded-md bg-green-50 p-2 text-sm text-green-700">Sufficient stock across all factories</div>
              ) : (
                <div className="rounded-md bg-red-50 p-2 text-sm text-red-700">Insufficient stock (deficit: {availResult.needed - availResult.total_available})</div>
              )}

              {availResult.best_single_factory && (
                <div className="text-sm text-gray-600">
                  Best single factory: <span className="font-medium">{availResult.best_single_factory.factory_name}</span> ({availResult.best_single_factory.available} available)
                </div>
              )}

              {availResult.all_factories.length > 0 && (
                <table className="mt-2 w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-xs font-semibold uppercase text-gray-500">
                      <th className="pb-2">Factory</th>
                      <th className="pb-2 text-right">Qty</th>
                      <th className="pb-2 text-right">Reserved</th>
                      <th className="pb-2 text-right">Available</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {availResult.all_factories.map((f) => (
                      <tr key={f.factory_id}>
                        <td className="py-1.5">{f.factory_name}</td>
                        <td className="py-1.5 text-right font-mono">{f.quantity}</td>
                        <td className="py-1.5 text-right font-mono">{f.reserved}</td>
                        <td className="py-1.5 text-right">
                          <span className={cn('font-mono font-semibold', f.available > 0 ? 'text-green-600' : 'text-red-600')}>
                            {f.available}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Stock Record">
        <p className="text-sm text-gray-600">
          Are you sure you want to delete this stock record? This action will be logged in the audit trail.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>Cancel</Button>
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
