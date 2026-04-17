import { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { useMaterials, useCreateMaterial, useUpdateMaterial, useCreateTransaction, useMaterialTransactions, type MaterialItem } from '@/hooks/useMaterials';
import apiClient from '@/api/client';
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
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

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
  full_name: string;
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
  full_name: '',
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
  type: 'receive' | 'manual_write_off' | 'inventory';
  quantity: string;
  notes: string;
  /** For inventory audit: the new actual balance (PM enters this instead of delta) */
  newBalance: string;
}

// ── Main page ───────────────────────────────────────────────────────────

export default function ManagerMaterialsPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const isPM = user?.role === 'production_manager';

  // Dynamic hierarchy for type tabs
  const { data: hierarchy, isLoading: hierarchyLoading } = useMaterialHierarchy();
  const subgroups = useMemo(() => flatSubgroups(hierarchy), [hierarchy]);

  // Filters
  const { data: factoriesData } = useFactories();
  const allFactories = factoriesData?.items ?? [];

  // PM sees only their assigned factories
  const userFactoryIds = user?.factories?.map((f) => f.id) ?? [];
  const factories = isPM && userFactoryIds.length > 0
    ? allFactories.filter((f) => userFactoryIds.includes(f.id))
    : allFactories;

  // PM with one factory → auto-select, no dropdown
  const [factoryId, setFactoryId] = useState('');
  const effectiveFactoryId = useMemo(() => {
    if (isPM && factories.length === 1 && !factoryId) return factories[0].id;
    return factoryId;
  }, [isPM, factories, factoryId]);

  const [activeType, setActiveType] = useState('all');
  const [search, setSearch] = useState('');

  // Data
  const { data, isLoading, isError } = useMaterials({
    factory_id: effectiveFactoryId || undefined,
    material_type: activeType !== 'all' ? activeType : undefined,
    search: search || undefined,
    per_page: 200,
  });
  const items = data?.items ?? [];

  // Suppliers
  const { data: suppliersData } = useSuppliers();
  const suppliers = suppliersData?.items ?? [];

  // Warehouse Sections
  const { data: warehouseSectionsData } = useWarehouseSections({ factory_id: effectiveFactoryId || undefined });
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
  const [txForm, setTxForm] = useState<TxForm>({ type: 'receive', quantity: '', notes: '', newBalance: '' });
  const [txError, setTxError] = useState('');

  // Transaction history dialog
  const [historyDialog, setHistoryDialog] = useState<{ open: boolean; item: MaterialItem | null }>({ open: false, item: null });
  const { data: txHistoryData, isLoading: txHistoryLoading } = useMaterialTransactions(historyDialog.item?.id);
  const txHistoryItems = txHistoryData?.items ?? [];

  // OCR delivery scan dialog
  interface OcrMatchedItem {
    ocr_name: string;
    quantity: number;
    unit: string;
    matched: boolean;
    matched_material_id: string | null;
    matched_material_name: string | null;
    confidence: number | null;
    // editable overrides
    _qty: string;
    _material_id: string;
    _included: boolean;
  }
  const [ocrDialog, setOcrDialog] = useState(false);
  const [ocrStage, setOcrStage] = useState<'upload' | 'loading' | 'confirm' | 'saving'>('upload');
  const [ocrItems, setOcrItems] = useState<OcrMatchedItem[]>([]);
  const [ocrMeta, setOcrMeta] = useState<{ supplier?: string; delivery_date?: string; reference?: string }>({});
  const [ocrError, setOcrError] = useState('');
  const [ocrFactoryId, setOcrFactoryId] = useState(effectiveFactoryId);
  const ocrFileRef = { current: null as HTMLInputElement | null };

  const handleOcrFile = useCallback(async (file: File) => {
    if (!file) return;
    setOcrError('');
    setOcrStage('loading');
    try {
      const fd = new FormData();
      fd.append('file', file);
      const resp = await apiClient.post('/delivery/process-photo', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const data = resp.data;
      const mapped: OcrMatchedItem[] = (data.items ?? []).map((it: Record<string, unknown>) => ({
        ocr_name: String(it.name ?? it.ocr_name ?? ''),
        quantity: Number(it.quantity ?? 0),
        unit: String(it.unit ?? 'kg'),
        matched: Boolean(it.matched),
        matched_material_id: (it.matched_material_id as string) ?? null,
        matched_material_name: (it.matched_material_name as string) ?? null,
        confidence: it.confidence != null ? Number(it.confidence) : null,
        _qty: String(it.quantity ?? ''),
        _material_id: (it.matched_material_id as string) ?? '',
        _included: Boolean(it.matched),
      }));
      setOcrItems(mapped);
      setOcrMeta({
        supplier: data.supplier ?? '',
        delivery_date: data.delivery_date ?? '',
        reference: data.reference_number ?? '',
      });
      setOcrStage('confirm');
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setOcrError(detail ?? 'OCR processing failed. Check file format.');
      setOcrStage('upload');
    }
  }, []);

  const ocrQc = useQueryClient();
  const handleOcrConfirm = useCallback(async () => {
    const included = ocrItems.filter((it) => it._included && it._material_id && parseFloat(it._qty) > 0);
    if (included.length === 0) { setOcrError('Select at least one item with a material and quantity.'); return; }
    setOcrError('');
    setOcrStage('saving');
    try {
      for (const it of included) {
        await apiClient.post('/materials/transactions', {
          material_id: it._material_id,
          factory_id: ocrFactoryId || effectiveFactoryId,
          type: 'receive',
          quantity: parseFloat(it._qty),
          notes: `Delivery scan: ${it.ocr_name}${ocrMeta.reference ? ` | Ref: ${ocrMeta.reference}` : ''}${ocrMeta.supplier ? ` | ${ocrMeta.supplier}` : ''}`,
        });
      }
      ocrQc.invalidateQueries({ queryKey: ['materials'] });
      setOcrDialog(false);
      setOcrStage('upload');
      setOcrItems([]);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setOcrError(detail ?? 'Failed to save transactions.');
      setOcrStage('confirm');
    }
  }, [ocrItems, ocrFactoryId, effectiveFactoryId, ocrMeta, ocrQc]);

  // Delete material (owner/admin only)
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const matQc = useQueryClient();
  const canDelete = user?.role === 'owner' || user?.role === 'administrator';
  const deleteMut = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/materials/${id}`).then((r) => r.data),
    onSuccess: () => { matQc.invalidateQueries({ queryKey: ['materials'] }); setDeleteId(null); },
  });

  // ── Edit/create dialog ──────────────────────────────────────────────────

  const openCreate = useCallback((defaultType?: string) => {
    const sg = subgroups.find((s) => s.value === defaultType);
    setForm({
      ...emptyForm,
      material_type: defaultType ?? '',
      subgroup_id: sg?.subgroupId ?? '',
      factory_id: effectiveFactoryId,
    });
    setFormError('');
    setEditDialog({ open: true, item: null });
  }, [effectiveFactoryId, subgroups]);

  const openEdit = useCallback((item: MaterialItem) => {
    setForm({
      name: item.name,
      full_name: item.full_name ?? '',
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
  const isAggregateMode = !effectiveFactoryId;

  const handleSave = useCallback(async () => {
    if (!isPM && !form.name.trim()) { setFormError('Name is required'); return; }
    if (!form.subgroup_id && !form.material_type) { setFormError('Type is required'); return; }
    setFormError('');

    const isEditing = !!editDialog.item;

    if (isPM && isEditing) {
      // PM can only update: subgroup, warehouse_section, min_balance, supplier
      const payload: Record<string, unknown> = {
        subgroup_id: form.subgroup_id || null,
        material_type: form.material_type,
        min_balance: parseFloat(form.min_balance) || 0,
        supplier_id: form.supplier_id || null,
        warehouse_section: form.warehouse_section || 'raw_materials',
      };
      try {
        await updateMaterial.mutateAsync({ id: editDialog.item!.id, data: payload, factoryId: effectiveFactoryId || undefined });
        closeEdit();
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setFormError(detail ?? 'Save failed');
      }
    } else {
      // Full save (create or non-PM edit)
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        full_name: form.full_name.trim() || null,
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
        if (isEditing) {
          await updateMaterial.mutateAsync({ id: editDialog.item!.id, data: payload, factoryId: effectiveFactoryId || undefined });
        } else {
          await createMaterial.mutateAsync(payload);
        }
        closeEdit();
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setFormError(detail ?? 'Save failed');
      }
    }
  }, [form, editDialog.item, isPM, createMaterial, updateMaterial, closeEdit]);

  // ── Transaction dialog ──────────────────────────────────────────────────

  const openTx = useCallback((item: MaterialItem, mode: 'receive' | 'inventory' | 'manual_write_off' = 'receive') => {
    setTxForm({
      type: mode,
      quantity: '',
      notes: '',
      newBalance: mode === 'inventory' ? String(item.balance) : '',
    });
    setTxError('');
    setTxDialog({ open: true, item });
  }, []);

  // Auto-open Receive dialog when URL has ?receive=<material_id>
  // (used when navigating from Material Reservations modal on a position)
  const [searchParams, setSearchParams] = useSearchParams();
  useEffect(() => {
    const mid = searchParams.get('receive');
    if (!mid || !items.length) return;
    const target = items.find((i) => i.id === mid);
    if (target) {
      openTx(target, 'receive');
      // Clear the query param so dialog doesn't reopen on re-render
      searchParams.delete('receive');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, items, openTx, setSearchParams]);

  const closeTx = useCallback(() => {
    setTxDialog({ open: false, item: null });
    setTxError('');
  }, []);

  const openHistory = useCallback((item: MaterialItem) => {
    setHistoryDialog({ open: true, item });
  }, []);

  const closeHistory = useCallback(() => {
    setHistoryDialog({ open: false, item: null });
  }, []);

  const handleTx = useCallback(async () => {
    if (!txDialog.item) return;

    if (txForm.type === 'inventory' && isPM) {
      // Inventory audit for PM: calculate delta from new balance
      const newBal = parseFloat(txForm.newBalance);
      if (isNaN(newBal) || newBal < 0) { setTxError('Enter a valid new balance'); return; }
      if (!txForm.notes.trim()) { setTxError('Reason is required for inventory audit'); return; }

      const currentBalance = Number(txDialog.item.balance);
      const delta = newBal - currentBalance;
      if (delta === 0) { setTxError('New balance is the same as current'); return; }

      setTxError('');
      try {
        await createTransaction.mutateAsync({
          material_id: txDialog.item.id,
          factory_id: txDialog.item.factory_id ?? '',
          type: 'inventory',
          quantity: delta,
          notes: `[Inventory Audit] ${txForm.notes.trim()} | Previous: ${currentBalance}, New: ${newBal}`,
        });
        closeTx();
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setTxError(detail ?? 'Transaction failed');
      }
      return;
    }

    // Standard transaction (receive / write-off / inventory for non-PM)
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
  }, [txDialog.item, txForm, isPM, createTransaction, closeTx]);

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

  // PM sees only assigned factories, others see all
  const showFactoryFilter = !isPM || factories.length > 1;
  const factoryOptions = isPM
    ? factories.map((f) => ({ value: f.id, label: f.name }))
    : [{ value: '', label: 'All factories' }, ...factories.map((f) => ({ value: f.id, label: f.name }))];

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
            {isPM ? 'Inventory management — receive, audit, and track materials' : 'Inventory of raw materials, packaging, and consumables'}
            {lowStockCount > 0 && (
              <span className="ml-2 inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                {'⚠'} {lowStockCount} low stock
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => navigate('/manager')}>{'←'} Dashboard</Button>
          {isPM && (
            <Button
              variant="secondary"
              onClick={() => { setOcrDialog(true); setOcrStage('upload'); setOcrItems([]); setOcrError(''); setOcrMeta({}); setOcrFactoryId(effectiveFactoryId); }}
            >
              📷 Scan Delivery
            </Button>
          )}
          <Button onClick={() => openCreate(activeType !== 'all' ? activeType : undefined)}>
            + Add Material
          </Button>
        </div>
      </div>

      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-3">
        {showFactoryFilter && (
          <div className="w-56">
            <Select
              options={factoryOptions}
              value={effectiveFactoryId}
              onChange={(e) => setFactoryId(e.target.value)}
            />
          </div>
        )}
        <div className="flex-1 min-w-48">
          <Input
            placeholder="Search materials…"
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
          <p className="py-8 text-center text-sm text-red-600">{'⚠'} Error loading materials</p>
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
          isPM={isPM}
          hideNames={false}
          canDelete={canDelete}
          onEdit={openEdit}
          onReceive={(item) => openTx(item, 'receive')}
          onInventoryAudit={(item) => openTx(item, 'inventory')}
          onTransaction={isPM ? undefined : (item) => openTx(item, 'receive')}
          onHistory={openHistory}
          onDelete={(item) => setDeleteId(item.id)}
        />
      )}

      {/* Create / Edit dialog */}
      <Dialog
        open={editDialog.open}
        onClose={closeEdit}
        title={editDialog.item
          ? `Edit: ${isPM ? (editDialog.item.material_code ?? editDialog.item.name) : editDialog.item.name}`
          : 'Add Material'}
        className="w-full max-w-lg"
      >
        <div className="space-y-4">
          {/* Name — hidden for PM on edit, visible for create */}
          {(!isPM || !editDialog.item) && (
            <>
              <Input
                label="Name (short) *"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Zircosil"
              />
              <Input
                label="Full name"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="e.g. Zirconium Silicate Micronized"
              />
            </>
          )}

          <div className="grid grid-cols-2 gap-4">
            {/* Factory — PM cannot change, others can */}
            {!isPM && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Factory</label>
                <Select
                  options={[
                    { value: '', label: 'All factories (auto)' },
                    ...allFactories.map((f) => ({ value: f.id, label: f.name })),
                  ]}
                  value={form.factory_id}
                  onChange={(e) => setForm({ ...form, factory_id: e.target.value })}
                />
              </div>
            )}
            <div className={isPM ? 'col-span-2' : ''}>
              <label className="mb-1 block text-sm font-medium text-gray-700">Subgroup *</label>
              <Select
                options={subgroupOptions}
                value={form.subgroup_id}
                onChange={(e) => handleSubgroupChange(e.target.value)}
              />
            </div>
          </div>

          {!editDialog.item && !form.factory_id && !isPM && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
              Stock will be auto-created for all active factories with the specified balance and min balance.
            </div>
          )}

          <div className={`grid gap-4 ${isPM && editDialog.item ? 'grid-cols-1' : 'grid-cols-3'}`}>
            {/* Unit — only on create or for non-PM */}
            {(!isPM || !editDialog.item) && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Unit</label>
                <Select
                  options={UNIT_OPTIONS}
                  value={form.unit}
                  onChange={(e) => setForm({ ...form, unit: e.target.value })}
                />
              </div>
            )}
            {/* Balance — only for create (non-PM edit and PM cannot edit balance directly) */}
            {!editDialog.item && (
              <NumericInput
                label="Initial Balance"
                value={form.balance}
                onChange={(e) => setForm({ ...form, balance: e.target.value })}
                placeholder="0"
              />
            )}
            {/* PM editing: show balance as read-only info */}
            {isPM && editDialog.item && (
              <div className="rounded-lg bg-gray-50 px-4 py-3">
                <span className="text-sm text-gray-500">Current balance: </span>
                <span className="font-semibold text-gray-900">{Number(editDialog.item.balance).toFixed(3)} {editDialog.item.unit}</span>
                <p className="mt-1 text-xs text-gray-400">To change balance, use Inventory Audit</p>
              </div>
            )}
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
              options={[{ value: '', label: '— no supplier —' }, ...suppliers.map((s) => ({ value: s.id, label: s.name }))]}
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
              {saving ? 'Saving…' : editDialog.item ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Transaction dialog */}
      <Dialog
        open={txDialog.open}
        onClose={closeTx}
        title={txDialog.item
          ? (txForm.type === 'inventory' && isPM
            ? `Inventory Audit — ${isPM ? (txDialog.item.material_code ?? txDialog.item.name) : txDialog.item.name}`
            : `Transaction — ${isPM ? (txDialog.item.material_code ?? txDialog.item.name) : txDialog.item.name}`)
          : 'Transaction'}
        className="w-full max-w-sm"
      >
        {txDialog.item && (
          <div className="space-y-4">
            <div className="rounded-lg bg-gray-50 px-4 py-3 text-sm">
              <span className="text-gray-500">Current balance: </span>
              <span className="font-semibold">{txDialog.item.balance} {txDialog.item.unit}</span>
            </div>

            {/* Operation selector */}
            {isPM ? (
              /* PM sees only Receive and Inventory Audit */
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Operation</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setTxForm({ ...txForm, type: 'receive', newBalance: '' })}
                    className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                      txForm.type === 'receive'
                        ? 'border-green-500 bg-green-50 text-green-700'
                        : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {'↑'} Receive
                  </button>
                  <button
                    onClick={() => setTxForm({ ...txForm, type: 'inventory', newBalance: String(txDialog.item!.balance) })}
                    className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                      txForm.type === 'inventory'
                        ? 'border-amber-500 bg-amber-50 text-amber-700'
                        : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {'≡'} Inventory Audit
                  </button>
                </div>
              </div>
            ) : (
              /* Non-PM sees all 3 options */
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
            )}

            {/* PM Inventory Audit: show new balance input + mandatory reason */}
            {txForm.type === 'inventory' && isPM ? (
              <>
                <NumericInput
                  label={`New actual balance (${txDialog.item.unit})`}
                  value={txForm.newBalance}
                  onChange={(e) => setTxForm({ ...txForm, newBalance: e.target.value })}
                  placeholder="Enter actual balance after count"
                />
                {txForm.newBalance && !isNaN(parseFloat(txForm.newBalance)) && (
                  <div className={`rounded-lg px-3 py-2 text-sm ${
                    parseFloat(txForm.newBalance) - Number(txDialog.item.balance) > 0
                      ? 'bg-green-50 text-green-700'
                      : parseFloat(txForm.newBalance) - Number(txDialog.item.balance) < 0
                        ? 'bg-red-50 text-red-700'
                        : 'bg-gray-50 text-gray-500'
                  }`}>
                    Difference: {(parseFloat(txForm.newBalance) - Number(txDialog.item.balance) > 0 ? '+' : '')}
                    {(parseFloat(txForm.newBalance) - Number(txDialog.item.balance)).toFixed(3)} {txDialog.item.unit}
                  </div>
                )}
                <div>
                  <Input
                    label="Reason *"
                    value={txForm.notes}
                    onChange={(e) => setTxForm({ ...txForm, notes: e.target.value })}
                    placeholder="Why does the balance differ? (required)"
                  />
                  <p className="mt-1 text-xs text-gray-400">
                    Explain the reason for the discrepancy (e.g., spillage, measurement error, etc.)
                  </p>
                </div>
              </>
            ) : (
              <>
                <NumericInput
                  label={`Quantity (${txDialog.item.unit})`}
                  value={txForm.quantity}
                  onChange={(e) => setTxForm({ ...txForm, quantity: e.target.value })}
                  placeholder="0.000"
                />
                <Input
                  label={txForm.type === 'manual_write_off' ? 'Reason *' : 'Notes'}
                  value={txForm.notes}
                  onChange={(e) => setTxForm({ ...txForm, notes: e.target.value })}
                  placeholder={txForm.type === 'manual_write_off' ? 'Reason for write-off (required)' : 'Optional comment'}
                />
              </>
            )}

            {txError && <p className="text-sm text-red-600">{txError}</p>}
            <div className="flex justify-end gap-2 border-t pt-3">
              <Button variant="secondary" onClick={closeTx}>Cancel</Button>
              <Button
                onClick={handleTx}
                disabled={txPending}
                className={
                  txForm.type === 'manual_write_off' ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500' :
                  txForm.type === 'inventory' ? 'bg-amber-600 hover:bg-amber-700 focus:ring-amber-500' : ''
                }
              >
                {txPending ? 'Saving…' :
                  txForm.type === 'receive' ? '↑ Receive' :
                  txForm.type === 'inventory' && isPM ? '≡ Confirm Audit' :
                  txForm.type === 'inventory' ? '≡ Inventory' :
                  '↓ Write-off'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* Transaction History dialog */}
      <Dialog
        open={historyDialog.open}
        onClose={closeHistory}
        title={historyDialog.item
          ? `Transaction History — ${isPM ? (historyDialog.item.material_code ?? historyDialog.item.name) : historyDialog.item.name}`
          : 'Transaction History'}
        className="w-full max-w-2xl"
      >
        {txHistoryLoading ? (
          <div className="flex justify-center py-8"><Spinner className="h-6 w-6" /></div>
        ) : txHistoryItems.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-400">No transactions found</p>
        ) : (
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 border-b bg-gray-50 text-xs font-medium uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2 text-right">Qty</th>
                  <th className="px-3 py-2">By</th>
                  <th className="px-3 py-2">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {txHistoryItems.map((tx) => (
                  <tr key={tx.id} className="bg-white hover:bg-gray-50">
                    <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">
                      {tx.created_at ? new Date(tx.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        tx.type === 'receive' ? 'bg-green-100 text-green-700' :
                        tx.type === 'consume' || tx.type === 'manual_write_off' ? 'bg-red-100 text-red-700' :
                        tx.type === 'reserve' || tx.type === 'unreserve' ? 'bg-blue-100 text-blue-700' :
                        tx.type === 'inventory' ? 'bg-amber-100 text-amber-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {tx.type === 'inventory' ? 'audit' : tx.type.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className={`px-3 py-2 text-right font-mono text-sm ${
                      tx.type === 'receive' ? 'text-green-600' :
                      tx.type === 'consume' || tx.type === 'manual_write_off' ? 'text-red-600' :
                      'text-gray-900'
                    }`}>
                      {tx.type === 'receive' ? '+' : tx.type === 'consume' || tx.type === 'manual_write_off' ? '-' : ''}{Number(tx.quantity).toFixed(3)}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500">{tx.created_by_name ?? '—'}</td>
                    <td className="px-3 py-2 text-xs text-gray-500 max-w-48 truncate" title={tx.notes ?? ''}>
                      {tx.notes ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="mt-4 flex justify-end border-t pt-3">
          <Button variant="secondary" onClick={closeHistory}>Close</Button>
        </div>
      </Dialog>

      <ConfirmDialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={() => deleteId && deleteMut.mutate(deleteId)}
        title="Delete Material"
        message="Are you sure you want to delete this material? This action cannot be undone."
      />

      {/* OCR Delivery Scan Dialog */}
      <Dialog
        open={ocrDialog}
        onClose={() => { if (ocrStage !== 'loading' && ocrStage !== 'saving') { setOcrDialog(false); setOcrStage('upload'); setOcrItems([]); }}}
        title="📷 Scan Delivery Note"
        className="w-full max-w-3xl"
      >
        {ocrStage === 'upload' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">Upload a photo of the delivery note. AI will recognize materials and quantities automatically.</p>
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 p-10 transition-colors hover:border-blue-400 hover:bg-blue-50">
              <span className="text-4xl mb-3">📄</span>
              <span className="text-sm font-medium text-gray-700">Click to select photo</span>
              <span className="mt-1 text-xs text-gray-400">JPEG, PNG, WebP supported</span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleOcrFile(f); }}
              />
            </label>
            {ocrError && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{ocrError}</p>}
            <div className="flex justify-end">
              <Button variant="secondary" onClick={() => setOcrDialog(false)}>Cancel</Button>
            </div>
          </div>
        )}

        {ocrStage === 'loading' && (
          <div className="flex flex-col items-center gap-4 py-12">
            <Spinner className="h-10 w-10" />
            <p className="text-sm text-gray-500">Analyzing delivery note with AI…</p>
            <p className="text-xs text-gray-400">This takes 5–15 seconds</p>
          </div>
        )}

        {(ocrStage === 'confirm' || ocrStage === 'saving') && (
          <div className="space-y-4">
            {/* Meta info */}
            <div className="rounded-lg bg-gray-50 px-4 py-3 text-sm flex flex-wrap gap-4">
              {ocrMeta.supplier && <span><span className="font-medium text-gray-600">Supplier:</span> {ocrMeta.supplier}</span>}
              {ocrMeta.delivery_date && <span><span className="font-medium text-gray-600">Date:</span> {ocrMeta.delivery_date}</span>}
              {ocrMeta.reference && <span><span className="font-medium text-gray-600">Ref:</span> {ocrMeta.reference}</span>}
            </div>

            {/* Factory selector */}
            {showFactoryFilter && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-600">Post to factory:</span>
                <select
                  value={ocrFactoryId}
                  onChange={(e) => setOcrFactoryId(e.target.value)}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                >
                  {factories.map((f: { id: string; name: string }) => <option key={f.id} value={f.id}>{f.name}</option>)}
                </select>
              </div>
            )}

            {/* Items table */}
            <div className="max-h-96 overflow-y-auto rounded-lg border border-gray-200">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-50 text-xs font-medium uppercase tracking-wider text-gray-500">
                  <tr>
                    <th className="w-8 px-3 py-2 text-center">✓</th>
                    <th className="px-3 py-2 text-left">From document</th>
                    <th className="px-3 py-2 text-left">Matched material</th>
                    <th className="px-3 py-2 text-right w-28">Quantity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {ocrItems.map((it, idx) => (
                    <tr key={idx} className={it._included ? 'bg-white' : 'bg-gray-50 opacity-60'}>
                      <td className="px-3 py-2 text-center">
                        <input
                          type="checkbox"
                          checked={it._included}
                          onChange={(e) => setOcrItems((prev) => prev.map((x, i) => i === idx ? { ...x, _included: e.target.checked } : x))}
                          className="h-4 w-4 rounded border-gray-300 text-blue-600"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <span className="text-gray-800">{it.ocr_name}</span>
                        {it.confidence != null && (
                          <span className={`ml-2 text-xs ${it.confidence >= 0.8 ? 'text-green-500' : it.confidence >= 0.5 ? 'text-amber-500' : 'text-red-500'}`}>
                            {Math.round(it.confidence * 100)}%
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <select
                          value={it._material_id}
                          onChange={(e) => setOcrItems((prev) => prev.map((x, i) => i === idx ? { ...x, _material_id: e.target.value, _included: !!e.target.value } : x))}
                          className="w-full rounded border border-gray-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                        >
                          <option value="">— not matched —</option>
                          {items.map((m) => (
                            <option key={m.id} value={m.id}>{m.name} ({m.unit})</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          min="0"
                          step="0.001"
                          value={it._qty}
                          onChange={(e) => setOcrItems((prev) => prev.map((x, i) => i === idx ? { ...x, _qty: e.target.value } : x))}
                          className="w-full rounded border border-gray-200 px-2 py-1 text-right text-xs focus:border-blue-400 focus:outline-none"
                        />
                        <span className="text-xs text-gray-400"> {it.unit}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-xs text-gray-400">
              {ocrItems.filter((x) => x._included).length} of {ocrItems.length} items selected.
              Confirm to post as &ldquo;receive&rdquo; transactions.
            </p>

            {ocrError && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{ocrError}</p>}

            <div className="flex justify-between border-t pt-3">
              <Button variant="secondary" onClick={() => setOcrStage('upload')} disabled={ocrStage === 'saving'}>
                ← Re-scan
              </Button>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => setOcrDialog(false)} disabled={ocrStage === 'saving'}>Cancel</Button>
                <Button onClick={handleOcrConfirm} disabled={ocrStage === 'saving'}>
                  {ocrStage === 'saving' ? 'Saving…' : `✓ Confirm Receipt (${ocrItems.filter((x) => x._included && x._material_id && parseFloat(x._qty) > 0).length} items)`}
                </Button>
              </div>
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
  isPM?: boolean;
  hideNames?: boolean;
  canDelete?: boolean;
  onEdit: (item: MaterialItem) => void;
  onReceive?: (item: MaterialItem) => void;
  onInventoryAudit?: (item: MaterialItem) => void;
  onTransaction?: (item: MaterialItem) => void;
  onHistory: (item: MaterialItem) => void;
  onDelete?: (item: MaterialItem) => void;
}

function MaterialsTable({ items, subgroups, isAggregate, isPM, hideNames, canDelete, onEdit, onReceive, onInventoryAudit, onTransaction, onHistory, onDelete }: MaterialsTableProps) {
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
            <th className="px-4 py-3 text-right">Total</th>
            <th className="px-4 py-3 text-right text-blue-600">Reserved</th>
            <th className="px-4 py-3 text-right text-emerald-600">Available</th>
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
              <td className="px-4 py-3 font-mono text-xs text-indigo-600">{m.material_code ?? '—'}</td>
              {!hideNames && (
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{m.name}</div>
                  {m.full_name && <div className="text-xs text-gray-400">{m.full_name}</div>}
                </td>
              )}
              <td className="px-4 py-3">
                <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                  {typeIcon(m.material_type)} {typeLabel(m.material_type)}
                </span>
              </td>
              <td className="px-4 py-3 text-right font-mono text-gray-500">
                {Number(m.balance).toFixed(3)}
              </td>
              <td className="px-4 py-3 text-right font-mono text-blue-600">
                {(m.reserved_qty ?? 0) > 0 ? Number(m.reserved_qty).toFixed(3) : <span className="text-gray-300">—</span>}
              </td>
              <td className={`px-4 py-3 text-right font-mono font-semibold ${m.is_low_stock ? 'text-red-600' : 'text-emerald-700'}`}>
                {Number(m.available_qty ?? m.balance).toFixed(3)}
              </td>
              <td className="px-4 py-3 text-right font-mono text-gray-500">
                {Number(m.min_balance).toFixed(3)}
              </td>
              <td className="px-4 py-3 text-gray-500">{m.unit}</td>
              {!hideNames && (
                <td className="px-4 py-3 text-gray-500">{m.supplier_name ?? <span className="text-gray-300">{'—'}</span>}</td>
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
                  <Badge status="error" label={`Deficit: ${(Number(m.min_balance) - Number(m.available_qty ?? m.balance)).toFixed(1)} ${m.unit}`} />
                ) : (
                  <Badge status="active" label="OK" />
                )}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1">
                  {isPM ? (
                    /* PM: separate Receive and Audit buttons */
                    isAggregate ? (
                      <span className="text-xs text-gray-400">Select factory</span>
                    ) : (
                      <>
                        <Button size="sm" variant="ghost" onClick={() => onReceive?.(m)} title="Receive material">
                          {'↑'}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => onInventoryAudit?.(m)} title="Inventory audit">
                          {'≡'}
                        </Button>
                      </>
                    )
                  ) : (
                    /* Non-PM: single transaction button */
                    isAggregate ? (
                      <Button size="sm" variant="ghost" disabled title="Select a factory to manage transactions">
                        {'\u00B1'}
                      </Button>
                    ) : (
                      <Button size="sm" variant="ghost" onClick={() => onTransaction?.(m)}>
                        {'\u00B1'}
                      </Button>
                    )
                  )}
                  <Button size="sm" variant="ghost" onClick={() => onHistory(m)} title="Transaction history">
                    Hst
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => onEdit(m)}>
                    Edit
                  </Button>
                  {canDelete && onDelete && (
                    <Button size="sm" variant="ghost" className="text-red-600 hover:bg-red-50 hover:text-red-700" onClick={() => onDelete(m)}>
                      Del
                    </Button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
