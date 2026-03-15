import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useMaterials, useCreateMaterial, useUpdateMaterial, useCreateTransaction, type MaterialItem } from '@/hooks/useMaterials';
import { useMaterialHierarchy, type MaterialGroup } from '@/hooks/useMaterialGroups';
import { useFactories } from '@/hooks/useFactories';
import { useSuppliers } from '@/hooks/useSuppliers';
import { useWarehouseSections } from '@/hooks/useWarehouseSections';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { NumericInput } from '@/components/ui/NumericInput';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

// ── Constants ────────────────────────────────────────────────────────────

const UNIT_OPTIONS = [
  { value: 'kg',  label: 'kg' },
  { value: 'g',   label: 'g' },
  { value: 'l',   label: 'L' },
  { value: 'pcs', label: 'pcs' },
  { value: 'm',   label: 'm' },
  { value: 'm2',  label: 'm\u00B2' },
];

/** Build a flat list of subgroups from hierarchy */
function flatSubgroups(hierarchy: MaterialGroup[] | undefined) {
  if (!hierarchy) return [];
  const result: { value: string; label: string; subgroupId: string; icon: string }[] = [];
  for (const g of hierarchy) {
    for (const sg of g.subgroups) {
      result.push({ value: sg.code, label: sg.name, subgroupId: sg.id, icon: sg.icon || '' });
    }
  }
  return result;
}

// ── Interfaces ───────────────────────────────────────────────────────────

interface MaterialForm {
  name: string;
  factory_id: string;
  subgroup_id: string;
  material_type: string;
  unit: string;
  balance: string;
  min_balance: string;
  supplier_id: string;
  warehouse_section: string;
}

const emptyForm: MaterialForm = {
  name: '',
  factory_id: '',
  subgroup_id: '',
  material_type: '',
  unit: 'kg',
  balance: '0',
  min_balance: '0',
  supplier_id: '',
  warehouse_section: 'raw_materials',
};

interface TxForm {
  type: 'receive' | 'manual_write_off';
  quantity: string;
  notes: string;
}

// ── Main page ───────────────────────────────────────────────────────────

export default function ManagerMaterialsPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  // Dynamic hierarchy for type tabs
  const { data: hierarchy, isLoading: hierarchyLoading } = useMaterialHierarchy();
  const subgroups = useMemo(() => flatSubgroups(hierarchy), [hierarchy]);

  // Filters
  const { data: factoriesData } = useFactories();
  const factories = factoriesData?.items ?? [];
  const [factoryId, setFactoryId] = useState('');
  const [activeType, setActiveType] = useState('all');
  const [search, setSearch] = useState('');

  // Data
  const { data, isLoading, isError } = useMaterials({
    factory_id: factoryId || undefined,
    material_type: activeType !== 'all' ? activeType : undefined,
    search: search || undefined,
    per_page: 200,
  });
  const items = data?.items ?? [];

  // Suppliers
  const { data: suppliersData } = useSuppliers();
  const suppliers = suppliersData?.items ?? [];

  // Warehouse Sections
  const { data: warehouseSectionsData } = useWarehouseSections({ factory_id: factoryId || undefined });
  const warehouseSections = warehouseSectionsData?.items ?? [];

  // Mutations
  const createMaterial = useCreateMaterial();
  const updateMaterial = useUpdateMaterial();
  const createTransaction = useCreateTransaction();

  // Dialog state
  const [editDialog, setEditDialog] = useState<{ open: boolean; item: MaterialItem | null }>({ open: false, item: null });
  const [form, setForm] = useState<MaterialForm>(emptyForm);
  const [formError, setFormError] = useState('');

  const [txDialog, setTxDialog] = useState<{ open: boolean; item: MaterialItem | null }>({ open: false, item: null });
  const [txForm, setTxForm] = useState<TxForm>({ type: 'receive', quantity: '', notes: '' });
  const [txError, setTxError] = useState('');

  // ── Edit/create dialog ──────────────────────────────────────────────────

  const openCreate = useCallback((defaultType?: string) => {
    const sg = subgroups.find((s) => s.value === defaultType);
    setForm({
      ...emptyForm,
      material_type: defaultType ?? '',
      subgroup_id: sg?.subgroupId ?? '',
      factory_id: factoryId,
    });
    setFormError('');
    setEditDialog({ open: true, item: null });
  }, [factoryId, subgroups]);

  const openEdit = useCallback((item: MaterialItem) => {
    setForm({
      name: item.name,
      factory_id: item.factory_id ?? '',
      subgroup_id: item.subgroup_id ?? '',
      material_type: item.material_type ?? '',
      unit: item.unit,
      balance: String(item.balance),
      min_balance: String(item.min_balance),
      supplier_id: item.supplier_id ?? '',
      warehouse_section: item.warehouse_section ?? 'raw_materials',
    });
    setFormError('');
    setEditDialog({ open: true, item });
  }, []);

  const closeEdit = useCallback(() => {
    setEditDialog({ open: false, item: null });
    setFormError('');
  }, []);

  // Are we in aggregate mode (no specific factory selected)?
  const isAggregateMode = !factoryId;

  const handleSave = useCallback(async () => {
    if (!form.name.trim()) { setFormError('Name is required'); return; }
    if (!form.subgroup_id && !form.material_type) { setFormError('Type is required'); return; }
    setFormError('');

    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      material_type: form.material_type,
      subgroup_id: form.subgroup_id || null,
      unit: form.unit,
      balance: parseFloat(form.balance) || 0,
      min_balance: parseFloat(form.min_balance) || 0,
      supplier_id: form.supplier_id || null,
      warehouse_section: form.warehouse_section || 'raw_materials',
    };
    if (form.factory_id) {
      payload.factory_id = form.factory_id;
    }

    try {
      if (editDialog.item) {
        await updateMaterial.mutateAsync({ id: editDialog.item.id, data: payload });
      } else {
        await createMaterial.mutateAsync(payload);
      }
      closeEdit();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Save failed');
    }
  }, [form, editDialog.item, createMaterial, updateMaterial, closeEdit]);

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
    if (!qty || qty <= 0) { setTxError('Enter a valid quantity'); return; }
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
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setTxError(detail ?? 'Transaction failed');
    }
  }, [txDialog.item, txForm, createTransaction, closeTx]);

  // ── Counts ──────────────────────────────────────────────────────────────

  const countsByType = useMemo(() => {
    const map: Record<string, number> = {};
    items.forEach((m) => { map[m.material_type] = (map[m.material_type] ?? 0) + 1; });
    return map;
  }, [items]);

  const lowStockCount = useMemo(() => items.filter((m) => m.is_low_stock).length, [items]);

  const displayItems = useMemo(() => {
    if (activeType === 'all') return items;
    return items.filter((m) => m.material_type === activeType);
  }, [items, activeType]);

  const saving = createMaterial.isPending || updateMaterial.isPending;
  const txPending = createTransaction.isPending;

  const factoryOptions = [
    { value: '', label: 'All factories' },
    ...factories.map((f) => ({ value: f.id, label: f.name })),
  ];

  // Grouped subgroup options for the form
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

  const handleSubgroupChange = useCallback((sgId: string) => {
    const sg = subgroups.find((s) => s.subgroupId === sgId);
    setForm((prev) => ({
      ...prev,
      subgroup_id: sgId,
      material_type: sg?.value ?? prev.material_type,
    }));
  }, [subgroups]);

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Materials</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Inventory of raw materials, packaging, and consumables
            {lowStockCount > 0 && (
              <span className="ml-2 inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                ⚠ {lowStockCount} low stock
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => navigate('/manager')}>← Dashboard</Button>
          <Button onClick={() => openCreate(activeType !== 'all' ? activeType : undefined)}>
            + Add Material
          </Button>
        </div>
      </div>

      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="w-56">
          <Select
            options={factoryOptions}
            value={factoryId}
            onChange={(e) => setFactoryId(e.target.value)}
          />
        </div>
        <div className="flex-1 min-w-48">
          <Input
            placeholder="Search materials\u2026"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Dynamic type tabs */}
      {hierarchyLoading ? (
        <div className="flex justify-center py-4"><Spinner className="h-5 w-5" /></div>
      ) : (
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
            {items.length > 0 && (
              <span className="ml-1.5 rounded-full bg-gray-200 px-1.5 py-0.5 text-xs">{items.length}</span>
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
                  <span className="ml-1.5 rounded-full bg-gray-200 px-1.5 py-0.5 text-xs">{count}</span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Content */}
      {isError ? (
        <Card>
          <p className="py-8 text-center text-sm text-red-600">⚠ Error loading materials</p>
        </Card>
      ) : isLoading ? (
        <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
      ) : displayItems.length === 0 ? (
        <Card>
          <div className="py-12 text-center">
            <p className="text-gray-400">No materials found</p>
            <Button className="mt-4" variant="secondary" onClick={() => openCreate(activeType !== 'all' ? activeType : undefined)}>
              + Add first material
            </Button>
          </div>
        </Card>
      ) : (
        <MaterialsTable
          items={displayItems}
          subgroups={subgroups}
          isAggregate={isAggregateMode}
          hideNames={user?.role === 'production_manager'}
          onEdit={openEdit}
          onTransaction={openTx}
        />
      )}

      {/* Create / Edit dialog */}
      <Dialog
        open={editDialog.open}
        onClose={closeEdit}
        title={editDialog.item
          ? `Edit: ${user?.role === 'production_manager' ? (editDialog.item.material_code ?? editDialog.item.name) : editDialog.item.name}`
          : 'Add Material'}
        className="w-full max-w-lg"
      >
        <div className="space-y-4">
          {user?.role !== 'production_manager' && (
            <Input
              label="Name *"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Zinc Oxide ZnO"
            />
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Factory</label>
              <Select
                options={[
                  { value: '', label: 'All factories (auto)' },
                  ...factories.map((f) => ({ value: f.id, label: f.name })),
                ]}
                value={form.factory_id}
                onChange={(e) => setForm({ ...form, factory_id: e.target.value })}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Subgroup *</label>
              <Select
                options={subgroupOptions}
                value={form.subgroup_id}
                onChange={(e) => handleSubgroupChange(e.target.value)}
              />
            </div>
          </div>
          {!editDialog.item && !form.factory_id && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
              Stock will be auto-created for all active factories with the specified balance and min balance.
            </div>
          )}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Unit</label>
              <Select
                options={UNIT_OPTIONS}
                value={form.unit}
                onChange={(e) => setForm({ ...form, unit: e.target.value })}
              />
            </div>
            <NumericInput
              label="Balance"
              value={form.balance}
              onChange={(e) => setForm({ ...form, balance: e.target.value })}
              placeholder="0"
            />
            <NumericInput
              label="Min Balance"
              value={form.min_balance}
              onChange={(e) => setForm({ ...form, min_balance: e.target.value })}
              placeholder="0"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Supplier</label>
            <Select
              options={[{ value: '', label: '\u2014 no supplier \u2014' }, ...suppliers.map((s) => ({ value: s.id, label: s.name }))]}
              value={form.supplier_id}
              onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Warehouse Section</label>
            <Select
              options={warehouseSections.map((ws) => ({ value: ws.code, label: ws.name }))}
              value={form.warehouse_section}
              onChange={(e) => setForm({ ...form, warehouse_section: e.target.value })}
            />
          </div>
          {formError && <p className="text-sm text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 border-t pt-3">
            <Button variant="secondary" onClick={closeEdit}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Saving\u2026' : editDialog.item ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Transaction dialog */}
      <Dialog
        open={txDialog.open}
        onClose={closeTx}
        title={txDialog.item
          ? `Transaction \u2014 ${user?.role === 'production_manager' ? (txDialog.item.material_code ?? txDialog.item.name) : txDialog.item.name}`
          : 'Transaction'}
        className="w-full max-w-sm"
      >
        {txDialog.item && (
          <div className="space-y-4">
            <div className="rounded-lg bg-gray-50 px-4 py-3 text-sm">
              <span className="text-gray-500">Current balance: </span>
              <span className="font-semibold">{txDialog.item.balance} {txDialog.item.unit}</span>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Operation</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setTxForm({ ...txForm, type: 'receive' })}
                  className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                    txForm.type === 'receive'
                      ? 'border-green-500 bg-green-50 text-green-700'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  ↑ Receive
                </button>
                <button
                  onClick={() => setTxForm({ ...txForm, type: 'manual_write_off' })}
                  className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                    txForm.type === 'manual_write_off'
                      ? 'border-red-500 bg-red-50 text-red-700'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  ↓ Write-off
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
              <Button variant="secondary" onClick={closeTx}>Cancel</Button>
              <Button
                onClick={handleTx}
                disabled={txPending}
                className={txForm.type === 'manual_write_off' ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500' : ''}
              >
                {txPending ? 'Saving\u2026' : txForm.type === 'receive' ? '↑ Receive' : '↓ Write-off'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}

// ── Materials table ──────────────────────────────────────────────────────

interface MaterialsTableProps {
  items: MaterialItem[];
  subgroups: { value: string; label: string; icon: string }[];
  isAggregate?: boolean;
  hideNames?: boolean;
  onEdit: (item: MaterialItem) => void;
  onTransaction: (item: MaterialItem) => void;
}

function MaterialsTable({ items, subgroups, isAggregate, hideNames, onEdit, onTransaction }: MaterialsTableProps) {
  const typeLabel = (code: string) => subgroups.find((s) => s.value === code)?.label ?? code;
  const typeIcon = (code: string) => subgroups.find((s) => s.value === code)?.icon ?? '';

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full text-left text-sm">
        <thead className="border-b bg-gray-50 text-xs font-medium uppercase tracking-wider text-gray-500">
          <tr>
            <th className="px-4 py-3">Code</th>
            {!hideNames && <th className="px-4 py-3">Name</th>}
            <th className="px-4 py-3">Type</th>
            <th className="px-4 py-3 text-right">Balance</th>
            <th className="px-4 py-3 text-right">Min</th>
            <th className="px-4 py-3">Unit</th>
            {!hideNames && <th className="px-4 py-3">Supplier</th>}
            {isAggregate && <th className="px-4 py-3 text-center">Factories</th>}
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {items.map((m) => (
            <tr key={`${m.id}-${m.factory_id ?? 'all'}`} className={`bg-white transition-colors hover:bg-gray-50 ${m.is_low_stock ? 'bg-red-50 hover:bg-red-50' : ''}`}>
              <td className="px-4 py-3 font-mono text-xs text-indigo-600">{m.material_code ?? '\u2014'}</td>
              {!hideNames && <td className="px-4 py-3 font-medium text-gray-900">{m.name}</td>}
              <td className="px-4 py-3">
                <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                  {typeIcon(m.material_type)} {typeLabel(m.material_type)}
                </span>
              </td>
              <td className={`px-4 py-3 text-right font-mono font-semibold ${m.is_low_stock ? 'text-red-600' : 'text-gray-900'}`}>
                {Number(m.balance).toFixed(3)}
              </td>
              <td className="px-4 py-3 text-right font-mono text-gray-500">
                {Number(m.min_balance).toFixed(3)}
              </td>
              <td className="px-4 py-3 text-gray-500">{m.unit}</td>
              {!hideNames && (
                <td className="px-4 py-3 text-gray-500">{m.supplier_name ?? <span className="text-gray-300">{'\u2014'}</span>}</td>
              )}
              {isAggregate && (
                <td className="px-4 py-3 text-center">
                  <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                    {m.factory_count ?? 0}
                  </span>
                </td>
              )}
              <td className="px-4 py-3">
                {m.is_low_stock ? (
                  <Badge status="error" label={`Deficit: ${(Number(m.min_balance) - Number(m.balance)).toFixed(1)} ${m.unit}`} />
                ) : (
                  <Badge status="active" label="OK" />
                )}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1">
                  {isAggregate ? (
                    <Button size="sm" variant="ghost" disabled title="Select a factory to manage transactions">
                      ±
                    </Button>
                  ) : (
                    <Button size="sm" variant="ghost" onClick={() => onTransaction(m)}>
                      ±
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" onClick={() => onEdit(m)}>
                    Edit
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
