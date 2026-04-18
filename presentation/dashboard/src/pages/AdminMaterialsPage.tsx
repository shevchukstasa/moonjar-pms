import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMaterials, useCreateMaterial, useUpdateMaterial, useDeleteMaterial, useCreateTransaction, type MaterialItem } from '@/hooks/useMaterials';
import {
  useMaterialHierarchy,
  useCreateMaterialGroup,
  useUpdateMaterialGroup,
  useCreateMaterialSubgroup,
  useUpdateMaterialSubgroup,
  type MaterialGroup,
  type MaterialSubgroup,
} from '@/hooks/useMaterialGroups';
import { useFactories } from '@/hooks/useFactories';
import { useSuppliers } from '@/hooks/useSuppliers';
import { useSizes } from '@/hooks/useSizes';
import type { SizeItem } from '@/api/sizes';
import { useWarehouseSections } from '@/hooks/useWarehouseSections';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { NumericInput } from '@/components/ui/NumericInput';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { MaterialDeduplication } from '@/components/admin/MaterialDeduplication';
import { CsvImportDialog } from '@/components/admin/CsvImportDialog';
import { CSV_CONFIGS } from '@/config/csvImportConfigs';
import { useQueryClient } from '@tanstack/react-query';

// ── Constants ────────────────────────────────────────────────────────────

const UNIT_OPTIONS = [
  { value: 'kg',  label: 'kg' },
  { value: 'g',   label: 'g' },
  { value: 'l',   label: 'L' },
  { value: 'ml',  label: 'ml' },
  { value: 'pcs', label: 'pcs' },
  { value: 'm',   label: 'm' },
  { value: 'm2',  label: 'm\u00B2' },
];

// ── Helpers ──────────────────────────────────────────────────────────────

/** Build a flat list of subgroups from hierarchy for type tabs & dropdowns */
function flatSubgroups(hierarchy: MaterialGroup[] | undefined) {
  if (!hierarchy) return [];
  const result: { value: string; label: string; subgroupId: string; icon: string }[] = [];
  for (const g of hierarchy) {
    for (const sg of g.subgroups) {
      result.push({
        value: sg.code,
        label: sg.name,
        subgroupId: sg.id,
        icon: sg.icon || '',
      });
    }
  }
  return result;
}

// ── Form interfaces ─────────────────────────────────────────────────────

interface CatalogForm {
  name: string;
  short_name: string;
  full_name: string;
  subgroup_id: string;
  material_type: string;
  unit: string;
  supplier_id: string;
  size_id: string;
  balance_override: string;  // admin/owner override — blank = don't touch
}

const emptyCatalogForm: CatalogForm = {
  name: '',
  short_name: '',
  full_name: '',
  subgroup_id: '',
  material_type: '',
  unit: 'kg',
  supplier_id: '',
  size_id: '',
  balance_override: '',
};

/** Build auto-name for stone material from a Size record */
function stoneName(size: SizeItem | undefined): string {
  if (!size) return '';
  const dims = `${size.width_mm}x${size.height_mm}`;
  const th = size.thickness_mm ? ` ${size.thickness_mm}mm` : '';
  const sh = size.shape && size.shape !== 'rectangle' ? ` ${size.shape}` : '';
  return `LAVA STONE ${dims}${th}${sh}`;
}

const STONE_TYPES = ['stone', 'tile', 'sink', 'custom_product'];

interface StockForm {
  balance: string;
  min_balance: string;
  warehouse_section: string;
}

const emptyStockForm: StockForm = {
  balance: '0',
  min_balance: '0',
  warehouse_section: 'raw_materials',
};

interface TxForm {
  type: 'receive' | 'manual_write_off' | 'inventory';
  quantity: string;
  notes: string;
}

// ── SubgroupTypeTabs shared component ───────────────────────────────────

function SubgroupTypeTabs({
  subgroups,
  activeType,
  setActiveType,
  countsByType,
  totalCount,
}: {
  subgroups: { value: string; label: string; icon: string }[];
  activeType: string;
  setActiveType: (v: string) => void;
  countsByType: Record<string, number>;
  totalCount: number;
}) {
  return (
    <div className="flex flex-wrap gap-1 rounded-lg bg-gray-100 p-1">
      <button
        onClick={() => setActiveType('all')}
        className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          activeType === 'all'
            ? 'bg-white text-gray-900 shadow-sm'
            : 'text-gray-500 hover:text-gray-700'
        }`}
      >
        All
        {totalCount > 0 && (
          <span className="ml-1.5 rounded-full bg-gray-200 px-1.5 py-0.5 text-xs">
            {totalCount}
          </span>
        )}
      </button>
      {subgroups.map((sg) => {
        const count = countsByType[sg.value] ?? 0;
        return (
          <button
            key={sg.value}
            onClick={() => setActiveType(sg.value)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              activeType === sg.value
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {sg.icon ? `${sg.icon} ` : ''}{sg.label}
            {count > 0 && (
              <span className="ml-1.5 rounded-full bg-gray-200 px-1.5 py-0.5 text-xs">
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────

export default function AdminMaterialsPage() {
  const navigate = useNavigate();
  const [mainTab, setMainTab] = useState('catalog');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Materials</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Manage materials, stock, groups, and deduplication
          </p>
        </div>
        <Button variant="secondary" onClick={() => navigate('/admin')}>
          ← Admin Panel
        </Button>
      </div>

      {/* Tabs */}
      <Tabs
        tabs={[
          { id: 'catalog', label: 'Catalog' },
          { id: 'stock', label: 'Stock by Factory' },
          { id: 'groups', label: 'Groups & Subgroups' },
          { id: 'dedup', label: 'Deduplication & Merge' },
        ]}
        activeTab={mainTab}
        onChange={setMainTab}
      />

      {/* Tab content */}
      {mainTab === 'catalog' && <CatalogTab />}
      {mainTab === 'stock' && <StockByFactoryTab />}
      {mainTab === 'groups' && <GroupsSubgroupsTab />}
      {mainTab === 'dedup' && <MaterialDeduplication />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Tab 1: Catalog — material reference data (no factory-specific info)
// ═══════════════════════════════════════════════════════════════════════════

function CatalogTab() {
  // Hierarchy for dynamic tabs & form dropdown
  const { data: hierarchy, isLoading: hierarchyLoading } = useMaterialHierarchy();
  const subgroups = useMemo(() => flatSubgroups(hierarchy), [hierarchy]);

  // Filters
  const [activeType, setActiveType] = useState('all');
  const [search, setSearch] = useState('');

  // Data — aggregate mode (no factory_id)
  const { data, isLoading, isError } = useMaterials({
    material_type: activeType !== 'all' ? activeType : undefined,
    search: search || undefined,
    per_page: 200,
  });
  const items = data?.items ?? [];

  // Suppliers
  const { data: suppliersData } = useSuppliers();
  const suppliers = suppliersData?.items ?? [];

  // Sizes (for stone materials)
  const { data: sizesData } = useSizes();
  const sizes = sizesData?.items ?? [];

  // Mutations
  const createMaterial = useCreateMaterial();
  const updateMaterial = useUpdateMaterial();
  const deleteMaterial = useDeleteMaterial();

  // Dialog state
  const [editDialog, setEditDialog] = useState<{ open: boolean; item: MaterialItem | null }>({
    open: false,
    item: null,
  });
  const [form, setForm] = useState<CatalogForm>(emptyCatalogForm);
  const [formError, setFormError] = useState('');
  const isStoneType = STONE_TYPES.includes(form.material_type);

  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; item: MaterialItem | null }>({
    open: false,
    item: null,
  });
  const [deleteError, setDeleteError] = useState('');

  const [csvOpen, setCsvOpen] = useState(false);
  const csvQueryClient = useQueryClient();

  // ── Edit/create helpers ─────────────────────────────────────────────────

  const openCreate = useCallback(
    (defaultType?: string) => {
      const sg = subgroups.find((s) => s.value === defaultType);
      setForm({
        ...emptyCatalogForm,
        material_type: defaultType ?? '',
        subgroup_id: sg?.subgroupId ?? '',
      });
      setFormError('');
      setEditDialog({ open: true, item: null });
    },
    [subgroups],
  );

  const openEdit = useCallback(
    (item: MaterialItem) => {
      setForm({
        name: item.name,
        short_name: item.short_name ?? '',
        full_name: item.full_name ?? '',
        subgroup_id: item.subgroup_id ?? '',
        material_type: item.material_type ?? '',
        unit: item.unit,
        supplier_id: item.supplier_id ?? '',
        size_id: ((item as unknown as Record<string, unknown>).size_id as string) ?? '',
        balance_override: '',  // blank = don't override
      });
      setFormError('');
      setEditDialog({ open: true, item });
    },
    [],
  );

  const closeEdit = useCallback(() => {
    setEditDialog({ open: false, item: null });
    setFormError('');
  }, []);

  const handleSave = useCallback(async () => {
    if (!form.name.trim()) {
      setFormError('Name is required');
      return;
    }
    if (!form.subgroup_id && !form.material_type) {
      setFormError('Subgroup is required');
      return;
    }
    setFormError('');

    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      short_name: form.short_name.trim() || null,
      full_name: form.full_name.trim() || null,
      material_type: form.material_type,
      subgroup_id: form.subgroup_id || null,
      unit: form.unit,
      supplier_id: form.supplier_id || null,
      size_id: form.size_id || null,
    };
    // Balance override — owner/admin can set balance directly (skips audit).
    // Blank field = don't touch; any parseable number applies.
    if (form.balance_override.trim() !== '') {
      const v = parseFloat(form.balance_override);
      if (Number.isFinite(v) && v >= 0) {
        payload.balance = v;
      }
    }

    try {
      if (editDialog.item) {
        await updateMaterial.mutateAsync({ id: editDialog.item.id, data: payload });
      } else {
        // Create with default 0 balance (stocks auto-created for all factories)
        payload.balance = 0;
        payload.min_balance = 0;
        await createMaterial.mutateAsync(payload);
      }
      closeEdit();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setFormError(detail ?? 'Save failed');
    }
  }, [form, editDialog.item, createMaterial, updateMaterial, closeEdit]);

  // ── Delete ──────────────────────────────────────────────────────────────

  const openDelete = useCallback((item: MaterialItem) => {
    setDeleteDialog({ open: true, item });
    setDeleteError('');
  }, []);

  const handleDelete = useCallback(async () => {
    if (!deleteDialog.item) return;
    setDeleteError('');
    try {
      await deleteMaterial.mutateAsync({ id: deleteDialog.item.id });
      setDeleteDialog({ open: false, item: null });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setDeleteError(detail ?? 'Failed to delete material');
    }
  }, [deleteDialog.item, deleteMaterial]);

  // ── Counts ──────────────────────────────────────────────────────────────

  const countsByType = useMemo(() => {
    const map: Record<string, number> = {};
    items.forEach((m) => {
      map[m.material_type] = (map[m.material_type] ?? 0) + 1;
    });
    return map;
  }, [items]);

  const displayItems = useMemo(() => {
    if (activeType === 'all') return items;
    return items.filter((m) => m.material_type === activeType);
  }, [items, activeType]);

  const saving = createMaterial.isPending || updateMaterial.isPending;

  // ── Dropdown options ────────────────────────────────────────────────────

  const subgroupOptions = useMemo(() => {
    if (!hierarchy) return [];
    const opts: { value: string; label: string }[] = [];
    for (const g of hierarchy) {
      for (const sg of g.subgroups) {
        opts.push({ value: sg.id, label: `${g.name} / ${sg.name}` });
      }
    }
    return opts;
  }, [hierarchy]);

  const handleSubgroupChange = useCallback(
    (sgId: string) => {
      const sg = subgroups.find((s) => s.subgroupId === sgId);
      setForm((prev) => ({
        ...prev,
        subgroup_id: sgId,
        material_type: sg?.value ?? prev.material_type,
      }));
    },
    [subgroups],
  );

  if (hierarchyLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  const typeLabel = (code: string) =>
    subgroups.find((s) => s.value === code)?.label ?? code;
  const typeIcon = (code: string) =>
    subgroups.find((s) => s.value === code)?.icon ?? '';

  return (
    <div className="space-y-5">
      {/* Filters + Add button */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-48 flex-1">
          <Input
            placeholder="Search materials…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Button variant="secondary" onClick={() => setCsvOpen(true)}>Import CSV</Button>
        <Button onClick={() => openCreate(activeType !== 'all' ? activeType : undefined)}>
          + Add Material
        </Button>
      </div>

      {/* Dynamic type tabs */}
      <SubgroupTypeTabs
        subgroups={subgroups}
        activeType={activeType}
        setActiveType={setActiveType}
        countsByType={countsByType}
        totalCount={items.length}
      />

      {/* Content */}
      {isError ? (
        <Card>
          <p className="py-8 text-center text-sm text-red-600">⚠ Error loading materials</p>
        </Card>
      ) : isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      ) : displayItems.length === 0 ? (
        <Card>
          <div className="py-12 text-center">
            <p className="text-gray-400">No materials found</p>
            <Button
              className="mt-4"
              variant="secondary"
              onClick={() => openCreate(activeType !== 'all' ? activeType : undefined)}
            >
              + Add first material
            </Button>
          </div>
        </Card>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-xs font-medium uppercase tracking-wider text-gray-500">
              <tr>
                <th className="px-4 py-3">Code</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Unit</th>
                <th className="px-4 py-3">Supplier</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {displayItems.map((m) => (
                <tr
                  key={m.id}
                  className="bg-white transition-colors hover:bg-gray-50"
                >
                  <td className="px-4 py-3 font-mono text-xs text-indigo-600">{m.material_code ?? '—'}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{m.name}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                      {typeIcon(m.material_type)} {typeLabel(m.material_type)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{m.unit}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {m.supplier_name ?? <span className="text-gray-300">{'—'}</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <Button size="sm" variant="ghost" onClick={() => openEdit(m)}>
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openDelete(m)}
                        className="text-red-500 hover:text-red-700"
                      >
                        Del
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      <Dialog
        open={editDialog.open}
        onClose={closeEdit}
        title={editDialog.item ? `Edit: ${editDialog.item.name}` : 'Add Material'}
        className="w-full max-w-lg"
      >
        <div className="space-y-4">
          <Input
            label="Name (long, as on delivery) *"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. Grey Lava 5×20×1.2"
          />
          <Input
            label="Short name (canonical match key — §29)"
            value={form.short_name}
            onChange={(e) => setForm({ ...form, short_name: e.target.value })}
            placeholder="e.g. Lava Stone 5×20×1.2"
          />
          <Input
            label="Full name (optional)"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            placeholder="e.g. Zirconium Silicate Micronized"
          />
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Subgroup *</label>
              <Select
                options={subgroupOptions}
                value={form.subgroup_id}
                onChange={(e) => handleSubgroupChange(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Unit</label>
              <Select
                options={UNIT_OPTIONS}
                value={form.unit}
                onChange={(e) => setForm({ ...form, unit: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Supplier</label>
            <Select
              options={[
                { value: '', label: '— no supplier —' },
                ...suppliers.map((s) => ({ value: s.id, label: s.name })),
              ]}
              value={form.supplier_id}
              onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
            />
          </div>
          {/* Stone size picker — auto-names material from Size */}
          {isStoneType && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Size (from reference)
              </label>
              <Select
                options={[
                  { value: '', label: '— select size —' },
                  ...sizes.map((s) => ({
                    value: s.id,
                    label: `${s.name}  (${s.width_mm}\u00D7${s.height_mm}${s.thickness_mm ? ` \u00D7 ${s.thickness_mm}` : ''}mm${s.shape && s.shape !== 'rectangle' ? ` ${s.shape}` : ''})`,
                  })),
                ]}
                value={form.size_id}
                onChange={(e) => {
                  const sizeId = e.target.value;
                  const chosen = sizes.find((s) => s.id === sizeId);
                  setForm((prev) => ({
                    ...prev,
                    size_id: sizeId,
                    name: chosen ? stoneName(chosen) : prev.name,
                    unit: 'pcs',
                  }));
                }}
              />
              {form.size_id && (
                <p className="mt-1 text-xs text-gray-500">
                  Auto-name: <span className="font-medium">{stoneName(sizes.find((s) => s.id === form.size_id))}</span>
                </p>
              )}
            </div>
          )}
          {!editDialog.item && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
              Stock will be auto-created for all active factories with balance 0.
            </div>
          )}
          {editDialog.item && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              <div className="mb-1 text-xs font-medium text-amber-900">
                Override balance (owner/admin — skips audit)
              </div>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  value={form.balance_override}
                  onChange={(e) => setForm({ ...form, balance_override: e.target.value })}
                  placeholder={`Current: ${Number(editDialog.item.balance).toFixed(3)} ${editDialog.item.unit}`}
                  className="flex-1"
                />
                <span className="text-xs text-gray-500">{editDialog.item.unit}</span>
              </div>
              <p className="mt-1 text-xs text-amber-700">
                Leave blank to keep current balance. Applies to your primary factory's stock.
              </p>
            </div>
          )}
          {formError && <p className="text-sm text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 border-t pt-3">
            <Button variant="secondary" onClick={closeEdit}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : editDialog.item ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, item: null })}
        title="Delete Material"
        className="w-full max-w-sm"
      >
        {deleteDialog.item && (
          <div className="space-y-4">
            <p className="text-sm text-gray-700">
              Are you sure you want to delete <strong>{deleteDialog.item.name}</strong>?
              This will remove the material and all its related records (stock, transactions, recipes).
              This action cannot be undone.
            </p>
            {deleteError && (
              <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-600">{deleteError}</p>
            )}
            <div className="flex justify-end gap-2 border-t pt-3">
              <Button
                variant="secondary"
                onClick={() => { setDeleteDialog({ open: false, item: null }); setDeleteError(''); }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleDelete}
                disabled={deleteMaterial.isPending}
                className="bg-red-600 hover:bg-red-700 focus:ring-red-500"
              >
                {deleteMaterial.isPending ? 'Deleting…' : 'Delete'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      <CsvImportDialog open={csvOpen} onClose={() => setCsvOpen(false)} {...CSV_CONFIGS.materials} onSuccess={() => csvQueryClient.invalidateQueries({ queryKey: ['materials'] })} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Tab 2: Stock by Factory — balance, min_balance, section, transactions
// ═══════════════════════════════════════════════════════════════════════════

function StockByFactoryTab() {
  const { data: hierarchy, isLoading: hierarchyLoading } = useMaterialHierarchy();
  const subgroups = useMemo(() => flatSubgroups(hierarchy), [hierarchy]);

  // Factories
  const { data: factoriesData } = useFactories();
  const factories = factoriesData?.items ?? [];
  const [factoryId, setFactoryId] = useState('');

  // Filters
  const [activeType, setActiveType] = useState('all');
  const [search, setSearch] = useState('');

  // Data — per-factory mode
  const { data, isLoading, isError } = useMaterials({
    factory_id: factoryId || undefined,
    material_type: activeType !== 'all' ? activeType : undefined,
    search: search || undefined,
    per_page: 200,
  });
  const items = data?.items ?? [];

  // Warehouse sections
  const { data: warehouseSectionsData } = useWarehouseSections({ factory_id: factoryId || undefined });
  const warehouseSections = warehouseSectionsData?.items ?? [];

  // Mutations
  const updateMaterial = useUpdateMaterial();
  const createTransaction = useCreateTransaction();

  // Stock edit dialog
  const [stockDialog, setStockDialog] = useState<{ open: boolean; item: MaterialItem | null }>({
    open: false,
    item: null,
  });
  const [stockForm, setStockForm] = useState<StockForm>(emptyStockForm);
  const [stockError, setStockError] = useState('');

  // Transaction dialog
  const [txDialog, setTxDialog] = useState<{ open: boolean; item: MaterialItem | null }>({
    open: false,
    item: null,
  });
  const [txForm, setTxForm] = useState<TxForm>({ type: 'receive', quantity: '', notes: '' });
  const [txError, setTxError] = useState('');

  // ── Stock edit helpers ────────────────────────────────────────────────

  const openStockEdit = useCallback((item: MaterialItem) => {
    setStockForm({
      balance: String(item.balance),
      min_balance: String(item.min_balance),
      warehouse_section: item.warehouse_section ?? 'raw_materials',
    });
    setStockError('');
    setStockDialog({ open: true, item });
  }, []);

  const closeStockEdit = useCallback(() => {
    setStockDialog({ open: false, item: null });
    setStockError('');
  }, []);

  const handleStockSave = useCallback(async () => {
    if (!stockDialog.item) return;
    setStockError('');
    const payload: Record<string, unknown> = {
      min_balance: parseFloat(stockForm.min_balance) || 0,
      warehouse_section: stockForm.warehouse_section || 'raw_materials',
    };
    try {
      await updateMaterial.mutateAsync({
        id: stockDialog.item.id,
        data: payload,
        factoryId: stockDialog.item.factory_id ?? undefined,
      });
      closeStockEdit();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setStockError(detail ?? 'Save failed');
    }
  }, [stockForm, stockDialog.item, updateMaterial, closeStockEdit]);

  // ── Transaction dialog ──────────────────────────────────────────────────

  const openTx = useCallback((item: MaterialItem) => {
    setTxForm({ type: 'receive', quantity: '', notes: '' });
    setTxError('');
    setTxDialog({ open: true, item });
  }, []);

  const closeTx = useCallback(() => {
    setTxDialog({ open: false, item: null });
    setTxError('');
  }, []);

  const handleTx = useCallback(async () => {
    if (!txDialog.item) return;
    const qty = parseFloat(txForm.quantity);
    if (!qty || qty <= 0) {
      setTxError('Enter a valid quantity');
      return;
    }
    setTxError('');
    try {
      await createTransaction.mutateAsync({
        material_id: txDialog.item.id,
        factory_id: txDialog.item.factory_id ?? '',
        type: txForm.type,
        quantity: qty,
        notes: txForm.notes || undefined,
      });
      closeTx();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setTxError(detail ?? 'Transaction failed');
    }
  }, [txDialog.item, txForm, createTransaction, closeTx]);

  // ── Counts & display ──────────────────────────────────────────────────

  const countsByType = useMemo(() => {
    const map: Record<string, number> = {};
    items.forEach((m) => {
      map[m.material_type] = (map[m.material_type] ?? 0) + 1;
    });
    return map;
  }, [items]);

  const lowStockCount = useMemo(() => items.filter((m) => m.is_low_stock).length, [items]);

  const displayItems = useMemo(() => {
    if (activeType === 'all') return items;
    return items.filter((m) => m.material_type === activeType);
  }, [items, activeType]);

  const txPending = createTransaction.isPending;
  const stockSaving = updateMaterial.isPending;

  const typeLabel = (code: string) =>
    subgroups.find((s) => s.value === code)?.label ?? code;

  if (hierarchyLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Factory selector + search */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="w-56">
          <Select
            options={[
              { value: '', label: '— Select factory —' },
              ...factories.map((f) => ({ value: f.id, label: f.name })),
            ]}
            value={factoryId}
            onChange={(e) => setFactoryId(e.target.value)}
          />
        </div>
        <div className="min-w-48 flex-1">
          <Input
            placeholder="Search materials…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {!factoryId ? (
        <Card>
          <div className="py-12 text-center">
            <p className="text-lg text-gray-400">Select a factory to view stock levels</p>
            <p className="mt-1 text-sm text-gray-300">
              Choose a factory from the dropdown above to see balances and manage transactions
            </p>
          </div>
        </Card>
      ) : (
        <>
          {/* Low stock indicator */}
          {lowStockCount > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2">
              <span className="text-sm font-medium text-red-700">
                ⚠ {lowStockCount} material{lowStockCount > 1 ? 's' : ''} below minimum stock level
              </span>
            </div>
          )}

          {/* Dynamic type tabs */}
          <SubgroupTypeTabs
            subgroups={subgroups}
            activeType={activeType}
            setActiveType={setActiveType}
            countsByType={countsByType}
            totalCount={items.length}
          />

          {/* Content */}
          {isError ? (
            <Card>
              <p className="py-8 text-center text-sm text-red-600">⚠ Error loading materials</p>
            </Card>
          ) : isLoading ? (
            <div className="flex justify-center py-16">
              <Spinner className="h-8 w-8" />
            </div>
          ) : displayItems.length === 0 ? (
            <Card>
              <div className="py-12 text-center">
                <p className="text-gray-400">No materials found for this factory</p>
              </div>
            </Card>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="w-full text-left text-sm">
                <thead className="border-b bg-gray-50 text-xs font-medium uppercase tracking-wider text-gray-500">
                  <tr>
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3 text-right">Balance</th>
                    <th className="px-4 py-3 text-right">Min</th>
                    <th className="px-4 py-3">Unit</th>
                    <th className="px-4 py-3">Section</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {displayItems.map((m) => (
                    <tr
                      key={`${m.id}-${m.factory_id ?? 'all'}`}
                      className={`bg-white transition-colors hover:bg-gray-50 ${m.is_low_stock ? 'bg-red-50 hover:bg-red-50' : ''}`}
                    >
                      <td className="px-4 py-3 font-mono text-xs text-indigo-600">{m.material_code ?? '—'}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">{m.name}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{typeLabel(m.material_type)}</td>
                      <td
                        className={`px-4 py-3 text-right font-mono font-semibold ${m.is_low_stock ? 'text-red-600' : 'text-gray-900'}`}
                      >
                        {Number(m.balance).toFixed(3)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-500">
                        {Number(m.min_balance).toFixed(3)}
                      </td>
                      <td className="px-4 py-3 text-gray-500">{m.unit}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {m.warehouse_section ?? 'raw_materials'}
                      </td>
                      <td className="px-4 py-3">
                        {m.is_low_stock ? (
                          <Badge
                            status="error"
                            label={`Deficit: ${(Number(m.min_balance) - Number(m.balance)).toFixed(1)} ${m.unit}`}
                          />
                        ) : (
                          <Badge status="active" label="OK" />
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <Button size="sm" variant="ghost" onClick={() => openTx(m)}>
                            ±
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => openStockEdit(m)}>
                            Edit
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Stock edit dialog — min_balance, warehouse_section */}
      <Dialog
        open={stockDialog.open}
        onClose={closeStockEdit}
        title={stockDialog.item ? `Stock: ${stockDialog.item.name}` : 'Edit Stock'}
        className="w-full max-w-sm"
      >
        {stockDialog.item && (
          <div className="space-y-4">
            <div className="rounded-lg bg-gray-50 px-4 py-3 text-sm">
              <span className="text-gray-500">Current balance: </span>
              <span className="font-semibold">
                {Number(stockDialog.item.balance).toFixed(3)} {stockDialog.item.unit}
              </span>
            </div>
            <NumericInput
              label="Min Balance"
              value={stockForm.min_balance}
              onChange={(e) => setStockForm({ ...stockForm, min_balance: e.target.value })}
              placeholder="0"
            />
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Warehouse Section</label>
              <Select
                options={warehouseSections.map((ws) => ({ value: ws.code, label: ws.name }))}
                value={stockForm.warehouse_section}
                onChange={(e) => setStockForm({ ...stockForm, warehouse_section: e.target.value })}
              />
            </div>
            {stockError && <p className="text-sm text-red-600">{stockError}</p>}
            <div className="flex justify-end gap-2 border-t pt-3">
              <Button variant="secondary" onClick={closeStockEdit}>Cancel</Button>
              <Button onClick={handleStockSave} disabled={stockSaving}>
                {stockSaving ? 'Saving…' : 'Update'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* Transaction dialog */}
      <Dialog
        open={txDialog.open}
        onClose={closeTx}
        title={txDialog.item ? `Transaction — ${txDialog.item.name}` : 'Transaction'}
        className="w-full max-w-sm"
      >
        {txDialog.item && (
          <div className="space-y-4">
            <div className="rounded-lg bg-gray-50 px-4 py-3 text-sm">
              <span className="text-gray-500">Current balance: </span>
              <span className="font-semibold">
                {txDialog.item.balance} {txDialog.item.unit}
              </span>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Operation</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => setTxForm({ ...txForm, type: 'receive' })}
                  className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                    txForm.type === 'receive'
                      ? 'border-green-500 bg-green-50 text-green-700'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {'↑'} Receive
                </button>
                <button
                  onClick={() => setTxForm({ ...txForm, type: 'manual_write_off' })}
                  className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                    txForm.type === 'manual_write_off'
                      ? 'border-red-500 bg-red-50 text-red-700'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {'↓'} Write-off
                </button>
                <button
                  onClick={() => setTxForm({ ...txForm, type: 'inventory' })}
                  className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                    txForm.type === 'inventory'
                      ? 'border-amber-500 bg-amber-50 text-amber-700'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {'≡'} Inventory
                </button>
              </div>
            </div>
            <NumericInput
              label={`Quantity (${txDialog.item.unit})`}
              value={txForm.quantity}
              onChange={(e) => setTxForm({ ...txForm, quantity: e.target.value })}
              placeholder="0.000"
            />
            <Input
              label="Notes"
              value={txForm.notes}
              onChange={(e) => setTxForm({ ...txForm, notes: e.target.value })}
              placeholder="Optional comment"
            />
            {txError && <p className="text-sm text-red-600">{txError}</p>}
            <div className="flex justify-end gap-2 border-t pt-3">
              <Button variant="secondary" onClick={closeTx}>
                Cancel
              </Button>
              <Button
                onClick={handleTx}
                disabled={txPending}
                className={
                  txForm.type === 'manual_write_off'
                    ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
                    : txForm.type === 'inventory'
                      ? 'bg-amber-600 hover:bg-amber-700 focus:ring-amber-500'
                      : ''
                }
              >
                {txPending
                  ? 'Saving…'
                  : txForm.type === 'receive'
                    ? '↑ Receive'
                    : txForm.type === 'inventory'
                      ? '≡ Inventory'
                      : '↓ Write-off'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Tab 3: Groups & Subgroups Management
// ═══════════════════════════════════════════════════════════════════════════

interface GroupForm {
  name: string;
  code: string;
  description: string;
  icon: string;
  display_order: string;
}

interface SubgroupForm {
  group_id: string;
  name: string;
  code: string;
  description: string;
  icon: string;
  default_lead_time_days: string;
  default_unit: string;
  display_order: string;
}

const emptyGroupForm: GroupForm = {
  name: '',
  code: '',
  description: '',
  icon: '',
  display_order: '0',
};

const emptySubgroupForm: SubgroupForm = {
  group_id: '',
  name: '',
  code: '',
  description: '',
  icon: '',
  default_lead_time_days: '',
  default_unit: 'kg',
  display_order: '0',
};

function GroupsSubgroupsTab() {
  const { data: hierarchy, isLoading } = useMaterialHierarchy(true);
  const createGroup = useCreateMaterialGroup();
  const updateGroup = useUpdateMaterialGroup();
  const createSubgroup = useCreateMaterialSubgroup();
  const updateSubgroup = useUpdateMaterialSubgroup();

  // Group dialog
  const [groupDialog, setGroupDialog] = useState<{
    open: boolean;
    item: MaterialGroup | null;
  }>({ open: false, item: null });
  const [groupForm, setGroupForm] = useState<GroupForm>(emptyGroupForm);
  const [groupError, setGroupError] = useState('');

  // Subgroup dialog
  const [sgDialog, setSgDialog] = useState<{
    open: boolean;
    item: MaterialSubgroup | null;
  }>({ open: false, item: null });
  const [sgForm, setSgForm] = useState<SubgroupForm>(emptySubgroupForm);
  const [sgError, setSgError] = useState('');

  // ── Group CRUD ────────────────────────────────────────────────────────

  const openCreateGroup = useCallback(() => {
    setGroupForm(emptyGroupForm);
    setGroupError('');
    setGroupDialog({ open: true, item: null });
  }, []);

  const openEditGroup = useCallback((g: MaterialGroup) => {
    setGroupForm({
      name: g.name,
      code: g.code,
      description: g.description ?? '',
      icon: g.icon ?? '',
      display_order: String(g.display_order),
    });
    setGroupError('');
    setGroupDialog({ open: true, item: g });
  }, []);

  const handleSaveGroup = useCallback(async () => {
    if (!groupForm.name.trim()) {
      setGroupError('Name is required');
      return;
    }
    if (!groupForm.code.trim()) {
      setGroupError('Code is required');
      return;
    }
    setGroupError('');

    try {
      if (groupDialog.item) {
        await updateGroup.mutateAsync({
          id: groupDialog.item.id,
          data: {
            name: groupForm.name.trim(),
            code: groupForm.code.trim(),
            description: groupForm.description || undefined,
            icon: groupForm.icon || undefined,
            display_order: parseInt(groupForm.display_order) || 0,
          },
        });
      } else {
        await createGroup.mutateAsync({
          name: groupForm.name.trim(),
          code: groupForm.code.trim(),
          description: groupForm.description || undefined,
          icon: groupForm.icon || undefined,
          display_order: parseInt(groupForm.display_order) || 0,
        });
      }
      setGroupDialog({ open: false, item: null });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setGroupError(detail ?? 'Save failed');
    }
  }, [groupForm, groupDialog.item, createGroup, updateGroup]);

  const toggleGroupActive = useCallback(
    async (g: MaterialGroup) => {
      try {
        await updateGroup.mutateAsync({
          id: g.id,
          data: { is_active: !g.is_active },
        });
      } catch {
        // silent
      }
    },
    [updateGroup],
  );

  // ── Subgroup CRUD ─────────────────────────────────────────────────────

  const openCreateSubgroup = useCallback((groupId?: string) => {
    setSgForm({ ...emptySubgroupForm, group_id: groupId ?? '' });
    setSgError('');
    setSgDialog({ open: true, item: null });
  }, []);

  const openEditSubgroup = useCallback((sg: MaterialSubgroup) => {
    setSgForm({
      group_id: sg.group_id,
      name: sg.name,
      code: sg.code,
      description: sg.description ?? '',
      icon: sg.icon ?? '',
      default_lead_time_days: sg.default_lead_time_days != null ? String(sg.default_lead_time_days) : '',
      default_unit: sg.default_unit || 'kg',
      display_order: String(sg.display_order),
    });
    setSgError('');
    setSgDialog({ open: true, item: sg });
  }, []);

  const handleSaveSubgroup = useCallback(async () => {
    if (!sgForm.name.trim()) {
      setSgError('Name is required');
      return;
    }
    if (!sgForm.code.trim()) {
      setSgError('Code is required');
      return;
    }
    if (!sgForm.group_id) {
      setSgError('Group is required');
      return;
    }
    setSgError('');

    try {
      const payload = {
        group_id: sgForm.group_id,
        name: sgForm.name.trim(),
        code: sgForm.code.trim(),
        description: sgForm.description || undefined,
        icon: sgForm.icon || undefined,
        default_lead_time_days: sgForm.default_lead_time_days
          ? parseInt(sgForm.default_lead_time_days)
          : undefined,
        default_unit: sgForm.default_unit || 'kg',
        display_order: parseInt(sgForm.display_order) || 0,
      };

      if (sgDialog.item) {
        await updateSubgroup.mutateAsync({ id: sgDialog.item.id, data: payload });
      } else {
        await createSubgroup.mutateAsync(payload);
      }
      setSgDialog({ open: false, item: null });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setSgError(detail ?? 'Save failed');
    }
  }, [sgForm, sgDialog.item, createSubgroup, updateSubgroup]);

  const toggleSubgroupActive = useCallback(
    async (sg: MaterialSubgroup) => {
      try {
        await updateSubgroup.mutateAsync({
          id: sg.id,
          data: { is_active: !sg.is_active },
        });
      } catch {
        // silent
      }
    },
    [updateSubgroup],
  );

  // ── Group dropdown for subgroup form ──────────────────────────────────
  const groupOptions = useMemo(
    () => (hierarchy ?? []).map((g) => ({ value: g.id, label: g.name })),
    [hierarchy],
  );

  const groupSaving = createGroup.isPending || updateGroup.isPending;
  const sgSaving = createSubgroup.isPending || updateSubgroup.isPending;

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Actions */}
      <div className="flex items-center gap-3">
        <Button onClick={openCreateGroup}>+ Add Group</Button>
        <Button variant="secondary" onClick={() => openCreateSubgroup()}>
          + Add Subgroup
        </Button>
      </div>

      {/* Groups accordion */}
      {!hierarchy || hierarchy.length === 0 ? (
        <Card>
          <div className="py-12 text-center">
            <p className="text-gray-400">No groups yet. Create one to get started.</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {hierarchy.map((g) => (
            <Card key={g.id}>
              {/* Group header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {g.icon && <span className="text-xl">{g.icon}</span>}
                  <div>
                    <h3 className="text-base font-semibold text-gray-900">{g.name}</h3>
                    <p className="text-xs text-gray-400">
                      Code: {g.code} &middot; Order: {g.display_order}
                      {g.description && ` — ${g.description}`}
                    </p>
                  </div>
                  {!g.is_active && (
                    <Badge status="inactive" label="Inactive" />
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => openCreateSubgroup(g.id)}
                  >
                    + Subgroup
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => openEditGroup(g)}>
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => toggleGroupActive(g)}
                  >
                    {g.is_active ? 'Deactivate' : 'Activate'}
                  </Button>
                </div>
              </div>

              {/* Subgroups table */}
              {g.subgroups.length > 0 && (
                <div className="mt-4 overflow-x-auto rounded-lg border border-gray-100">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b bg-gray-50 text-xs font-medium uppercase tracking-wider text-gray-500">
                      <tr>
                        <th className="px-3 py-2">Icon</th>
                        <th className="px-3 py-2">Name</th>
                        <th className="px-3 py-2">Code</th>
                        <th className="px-3 py-2">Default Unit</th>
                        <th className="px-3 py-2">Lead Time</th>
                        <th className="px-3 py-2 text-right">Materials</th>
                        <th className="px-3 py-2">Status</th>
                        <th className="px-3 py-2"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {g.subgroups.map((sg) => (
                        <tr key={sg.id} className="hover:bg-gray-50">
                          <td className="px-3 py-2 text-center">{sg.icon || '—'}</td>
                          <td className="px-3 py-2 font-medium text-gray-900">{sg.name}</td>
                          <td className="px-3 py-2 font-mono text-xs text-gray-500">{sg.code}</td>
                          <td className="px-3 py-2 text-gray-500">{sg.default_unit}</td>
                          <td className="px-3 py-2 text-gray-500">
                            {sg.default_lead_time_days != null ? `${sg.default_lead_time_days}d` : '—'}
                          </td>
                          <td className="px-3 py-2 text-right font-mono text-gray-600">
                            {sg.material_count}
                          </td>
                          <td className="px-3 py-2">
                            {sg.is_active ? (
                              <Badge status="active" label="Active" />
                            ) : (
                              <Badge status="inactive" label="Inactive" />
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <div className="flex items-center gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => openEditSubgroup(sg)}
                              >
                                Edit
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => toggleSubgroupActive(sg)}
                              >
                                {sg.is_active ? 'Off' : 'On'}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Group dialog */}
      <Dialog
        open={groupDialog.open}
        onClose={() => setGroupDialog({ open: false, item: null })}
        title={groupDialog.item ? `Edit Group: ${groupDialog.item.name}` : 'New Material Group'}
        className="w-full max-w-md"
      >
        <div className="space-y-4">
          <Input
            label="Name *"
            value={groupForm.name}
            onChange={(e) => setGroupForm({ ...groupForm, name: e.target.value })}
            placeholder="e.g. Tile Materials"
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Code *"
              value={groupForm.code}
              onChange={(e) => setGroupForm({ ...groupForm, code: e.target.value })}
              placeholder="e.g. tile_materials"
            />
            <Input
              label="Icon"
              value={groupForm.icon}
              onChange={(e) => setGroupForm({ ...groupForm, icon: e.target.value })}
              placeholder="e.g. emoji"
            />
          </div>
          <Input
            label="Description"
            value={groupForm.description}
            onChange={(e) => setGroupForm({ ...groupForm, description: e.target.value })}
          />
          <Input
            label="Display Order"
            type="number"
            value={groupForm.display_order}
            onChange={(e) => setGroupForm({ ...groupForm, display_order: e.target.value })}
          />
          {groupError && <p className="text-sm text-red-600">{groupError}</p>}
          <div className="flex justify-end gap-2 border-t pt-3">
            <Button
              variant="secondary"
              onClick={() => setGroupDialog({ open: false, item: null })}
            >
              Cancel
            </Button>
            <Button onClick={handleSaveGroup} disabled={groupSaving}>
              {groupSaving ? 'Saving…' : groupDialog.item ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Subgroup dialog */}
      <Dialog
        open={sgDialog.open}
        onClose={() => setSgDialog({ open: false, item: null })}
        title={sgDialog.item ? `Edit Subgroup: ${sgDialog.item.name}` : 'New Subgroup'}
        className="w-full max-w-md"
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Group *</label>
            <Select
              options={groupOptions}
              value={sgForm.group_id}
              onChange={(e) => setSgForm({ ...sgForm, group_id: e.target.value })}
            />
          </div>
          <Input
            label="Name *"
            value={sgForm.name}
            onChange={(e) => setSgForm({ ...sgForm, name: e.target.value })}
            placeholder="e.g. Stone"
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Code *"
              value={sgForm.code}
              onChange={(e) => setSgForm({ ...sgForm, code: e.target.value })}
              placeholder="e.g. stone"
            />
            <Input
              label="Icon"
              value={sgForm.icon}
              onChange={(e) => setSgForm({ ...sgForm, icon: e.target.value })}
              placeholder="e.g. emoji"
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Default Unit</label>
              <Select
                options={UNIT_OPTIONS}
                value={sgForm.default_unit}
                onChange={(e) => setSgForm({ ...sgForm, default_unit: e.target.value })}
              />
            </div>
            <Input
              label="Lead Time (days)"
              type="number"
              value={sgForm.default_lead_time_days}
              onChange={(e) =>
                setSgForm({ ...sgForm, default_lead_time_days: e.target.value })
              }
            />
            <Input
              label="Display Order"
              type="number"
              value={sgForm.display_order}
              onChange={(e) => setSgForm({ ...sgForm, display_order: e.target.value })}
            />
          </div>
          <Input
            label="Description"
            value={sgForm.description}
            onChange={(e) => setSgForm({ ...sgForm, description: e.target.value })}
          />
          {sgError && <p className="text-sm text-red-600">{sgError}</p>}
          <div className="flex justify-end gap-2 border-t pt-3">
            <Button
              variant="secondary"
              onClick={() => setSgDialog({ open: false, item: null })}
            >
              Cancel
            </Button>
            <Button onClick={handleSaveSubgroup} disabled={sgSaving}>
              {sgSaving ? 'Saving…' : sgDialog.item ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
