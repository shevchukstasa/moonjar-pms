import { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  useConsumptionRules,
  useCreateConsumptionRule,
  useUpdateConsumptionRule,
  useDeleteConsumptionRule,
} from '@/hooks/useConsumptionRules';
import { useSizes } from '@/hooks/useSizes';
import type { ConsumptionRuleItem, ConsumptionRuleInput } from '@/api/consumptionRules';
import { referenceApi } from '@/api/reference';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

/* ── Constants (only for recipe_type which is truly static) ──── */

const RECIPE_TYPES = [
  { value: '', label: '— Any —' },
  { value: 'glaze', label: 'Glaze' },
  { value: 'engobe', label: 'Engobe' },
  { value: 'both', label: 'Both (Engobe + Glaze)' },
];

/* ── Multi-select chip component ──────────────────────────────── */

function MultiSelectChips({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  selected: string[];
  onChange: (values: string[]) => void;
}) {
  const [search, setSearch] = useState('');
  const filtered = useMemo(() => {
    if (!search) return options;
    const q = search.toLowerCase();
    return options.filter((o) => o.label.toLowerCase().includes(q));
  }, [options, search]);

  const toggle = (val: string) => {
    if (selected.includes(val)) {
      onChange(selected.filter((v) => v !== val));
    } else {
      onChange([...selected, val]);
    }
  };

  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      {/* Selected chips */}
      {selected.length > 0 && (
        <div className="mb-1 flex flex-wrap gap-1">
          {selected.map((val) => {
            const opt = options.find((o) => o.value === val);
            return (
              <span
                key={val}
                className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800"
              >
                {opt?.label ?? val}
                <button
                  type="button"
                  onClick={() => toggle(val)}
                  className="ml-0.5 text-blue-600 hover:text-blue-900"
                >
                  &times;
                </button>
              </span>
            );
          })}
        </div>
      )}
      {/* Search + options */}
      {options.length > 6 && (
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="mb-1 w-full rounded border border-gray-300 px-2 py-1 text-xs"
        />
      )}
      <div className="max-h-32 overflow-y-auto rounded border border-gray-200 bg-white">
        {filtered.length === 0 ? (
          <div className="px-2 py-1 text-xs text-gray-400">No options</div>
        ) : (
          filtered.map((o) => (
            <label
              key={o.value}
              className="flex cursor-pointer items-center gap-2 px-2 py-1 text-xs hover:bg-gray-50"
            >
              <input
                type="checkbox"
                checked={selected.includes(o.value)}
                onChange={() => toggle(o.value)}
                className="rounded"
              />
              {o.label}
            </label>
          ))
        )}
      </div>
    </div>
  );
}

/* ── Form interface ─────────────────────────────────────────── */

interface RuleForm {
  rule_number: string;
  name: string;
  description: string;
  collection: string;
  color_collection: string;
  product_type: string;
  size_id: string;
  size_ids: string[];  // for multi-select (creates separate rules per size)
  shape: string;
  thickness_mm_min: string;
  thickness_mm_max: string;
  place_of_application: string;
  recipe_type: string;
  application_method: string;
  consumption_ml_per_sqm: string;
  engobe_ml_per_sqm: string;  // used when recipe_type='both'
  coats: string;
  engobe_coats: string;
  specific_gravity_override: string;
  priority: string;
  is_active: boolean;
  notes: string;
}

const emptyForm: RuleForm = {
  rule_number: '',
  name: '',
  description: '',
  collection: '',
  color_collection: '',
  product_type: '',
  size_id: '',
  size_ids: [],
  shape: '',
  thickness_mm_min: '',
  thickness_mm_max: '',
  place_of_application: '',
  recipe_type: '',
  application_method: '',
  consumption_ml_per_sqm: '',
  engobe_ml_per_sqm: '',
  coats: '1',
  engobe_coats: '1',
  specific_gravity_override: '',
  priority: '0',
  is_active: true,
  notes: '',
};

/* ── Component ──────────────────────────────────────────────── */

export default function ConsumptionRulesPage() {
  const navigate = useNavigate();
  const { data: rules, isLoading } = useConsumptionRules(true);
  const { data: sizesData } = useSizes();
  const sizes = sizesData?.items ?? [];
  const createMutation = useCreateConsumptionRule();
  const updateMutation = useUpdateConsumptionRule();
  const deleteMutation = useDeleteConsumptionRule();

  // Load reference data from DB
  const { data: refData } = useQuery({
    queryKey: ['reference', 'all'],
    queryFn: referenceApi.getAll,
  });
  const { data: appMethods } = useQuery({
    queryKey: ['reference', 'application-methods'],
    queryFn: referenceApi.getApplicationMethods,
  });
  const { data: collectionsData } = useQuery({
    queryKey: ['reference', 'collections'],
    queryFn: referenceApi.getCollections,
  });

  // Build dropdown options from DB
  const productTypeOptions = useMemo(() => [
    { value: '', label: '— Any —' },
    ...(refData?.product_types?.map((t) => ({ value: t.value, label: t.label })) ?? []),
  ], [refData]);

  const shapeOptions = useMemo(() => [
    { value: '', label: '— Any —' },
    ...(refData?.shape_types?.map((t) => ({ value: t.value, label: t.label })) ?? []),
  ], [refData]);

  const applicationMethodOptions = useMemo(() => [
    { value: '', label: '— Any —' },
    ...(appMethods?.map((m) => ({ value: m.code, label: `${m.name} (${m.code.toUpperCase()})` })) ?? []),
  ], [appMethods]);

  const collectionOptions = useMemo(() => [
    { value: '', label: '— Any —' },
    ...(collectionsData?.map((c) => ({ value: c.value, label: c.label })) ?? []),
  ], [collectionsData]);

  const colorCollectionOptions = useMemo(() => {
    // Get unique color_collection values from existing rules + reference
    const vals = new Set<string>();
    rules?.forEach((r) => { if (r.color_collection) vals.add(r.color_collection); });
    return [
      { value: '', label: '— Any —' },
      ...Array.from(vals).sort().map((v) => ({ value: v, label: v })),
      { value: 'Collection 2025/2026', label: 'Collection 2025/2026' },
      { value: 'Custom', label: 'Custom' },
    ];
  }, [rules]);

  const placeOfApplicationOptions = useMemo(() => [
    { value: '', label: '— Any —' },
    { value: 'face_only', label: 'Face only' },
    { value: 'edges_1', label: 'Edges (1 side)' },
    { value: 'edges_2', label: 'Edges (2 sides)' },
    { value: 'all_edges', label: 'All edges' },
    { value: 'with_back', label: 'With back' },
  ], []);

  const sizeOptions = useMemo(() =>
    sizes.map((s) => ({
      value: s.id,
      label: `${s.name} (${s.width_mm}×${s.height_mm})`,
    })),
  [sizes]);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editItem, setEditItem] = useState<ConsumptionRuleItem | null>(null);
  const [form, setForm] = useState<RuleForm>(emptyForm);
  const [formError, setFormError] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<ConsumptionRuleItem | null>(null);
  const [multiSizeMode, setMultiSizeMode] = useState(false);

  /* ── Helpers ───────────────────────────────────────────────── */

  const openCreate = useCallback(() => {
    setEditItem(null);
    const nextNum = rules && rules.length > 0
      ? Math.max(...rules.map((r) => r.rule_number)) + 1
      : 1;
    setForm({ ...emptyForm, rule_number: String(nextNum) });
    setFormError('');
    setMultiSizeMode(false);
    setDialogOpen(true);
  }, [rules]);

  const openEdit = useCallback((item: ConsumptionRuleItem) => {
    setEditItem(item);
    setForm({
      rule_number: String(item.rule_number),
      name: item.name,
      description: item.description ?? '',
      collection: item.collection ?? '',
      color_collection: item.color_collection ?? '',
      product_type: item.product_type ?? '',
      size_id: item.size_id ?? '',
      size_ids: item.size_id ? [item.size_id] : [],
      shape: item.shape ?? '',
      thickness_mm_min: item.thickness_mm_min != null ? String(item.thickness_mm_min) : '',
      thickness_mm_max: item.thickness_mm_max != null ? String(item.thickness_mm_max) : '',
      place_of_application: item.place_of_application ?? '',
      recipe_type: item.recipe_type ?? '',
      application_method: item.application_method ?? '',
      consumption_ml_per_sqm: String(item.consumption_ml_per_sqm),
      coats: String(item.coats),
      specific_gravity_override: item.specific_gravity_override != null ? String(item.specific_gravity_override) : '',
      priority: String(item.priority),
      engobe_ml_per_sqm: '',
      engobe_coats: '1',
      is_active: item.is_active,
      notes: item.notes ?? '',
    });
    setFormError('');
    setMultiSizeMode(false);
    setDialogOpen(true);
  }, []);

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setEditItem(null);
    setForm(emptyForm);
    setFormError('');
    setMultiSizeMode(false);
  }, []);

  const buildPayload = useCallback((sizeId: string | null): ConsumptionRuleInput => ({
    rule_number: parseInt(form.rule_number) || 0,
    name: form.name.trim(),
    description: form.description || null,
    collection: form.collection || null,
    color_collection: form.color_collection || null,
    product_type: form.product_type || null,
    size_id: sizeId || null,
    shape: form.shape || null,
    thickness_mm_min: form.thickness_mm_min ? parseFloat(form.thickness_mm_min) : null,
    thickness_mm_max: form.thickness_mm_max ? parseFloat(form.thickness_mm_max) : null,
    place_of_application: form.place_of_application || null,
    recipe_type: form.recipe_type || null,
    application_method: form.application_method || null,
    consumption_ml_per_sqm: parseFloat(form.consumption_ml_per_sqm),
    coats: parseInt(form.coats) || 1,
    specific_gravity_override: form.specific_gravity_override ? parseFloat(form.specific_gravity_override) : null,
    priority: parseInt(form.priority) || 0,
    is_active: form.is_active,
    notes: form.notes || null,
  }), [form]);

  const handleSave = useCallback(async () => {
    if (!form.name.trim()) { setFormError('Name is required'); return; }
    if (!form.consumption_ml_per_sqm) { setFormError('Consumption ml/m² is required'); return; }
    setFormError('');

    try {
      if (editItem) {
        // Edit mode: single rule update
        const payload = buildPayload(form.size_id || null);
        await updateMutation.mutateAsync({ id: editItem.id, data: payload });
      } else if (multiSizeMode && form.size_ids.length > 0) {
        // Multi-size mode: create one rule per size
        let num = parseInt(form.rule_number) || 0;
        for (const sid of form.size_ids) {
          const sizeName = sizes.find((s) => s.id === sid)?.name ?? '';
          const payload = buildPayload(sid);
          payload.rule_number = num++;
          payload.name = form.size_ids.length > 1
            ? `${form.name.trim()} — ${sizeName}`
            : form.name.trim();
          await createMutation.mutateAsync(payload);
        }
      } else {
        // Single size or no size
        const payload = buildPayload(form.size_id || null);
        await createMutation.mutateAsync(payload);
      }
      closeDialog();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Save failed');
    }
  }, [form, editItem, multiSizeMode, sizes, createMutation, updateMutation, closeDialog, buildPayload]);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(deleteTarget.id);
      setDeleteTarget(null);
    } catch { /* ignore */ }
  }, [deleteTarget, deleteMutation]);

  const saving = createMutation.isPending || updateMutation.isPending;

  /* ── Render ────────────────────────────────────────────────── */

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Consumption Rules</h1>
          <p className="mt-1 text-sm text-gray-500">
            Define how glaze and engobe consumption (ml/m²) is calculated based on product characteristics
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>
            Back to Admin
          </Button>
          <Button onClick={openCreate}>+ Add Rule</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : !rules || rules.length === 0 ? (
        <Card>
          <p className="py-8 text-center text-gray-400">
            No consumption rules defined yet. Click &quot;+ Add Rule&quot; to create one.
          </p>
        </Card>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Recipe Type</th>
                <th className="px-3 py-2">Product</th>
                <th className="px-3 py-2">Size / Shape</th>
                <th className="px-3 py-2">Thickness (mm)</th>
                <th className="px-3 py-2">Application</th>
                <th className="px-3 py-2">Place</th>
                <th className="px-3 py-2 text-right">ml/m²</th>
                <th className="px-3 py-2 text-right">Coats</th>
                <th className="px-3 py-2 text-right">SG Override</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-gray-500">{r.rule_number}</td>
                  <td className="px-3 py-2">
                    <div className="font-medium text-gray-900">{r.name}</div>
                    {r.description && (
                      <div className="text-xs text-gray-400 line-clamp-1">{r.description}</div>
                    )}
                  </td>
                  <td className="px-3 py-2 capitalize">{r.recipe_type || '—'}</td>
                  <td className="px-3 py-2">{r.product_type || '—'}</td>
                  <td className="px-3 py-2">
                    <div>{r.size_name || '—'}</div>
                    {r.shape && <div className="text-xs text-gray-400">{r.shape}</div>}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {r.thickness_mm_min != null || r.thickness_mm_max != null
                      ? `${r.thickness_mm_min ?? '—'}–${r.thickness_mm_max ?? '—'}`
                      : '—'}
                  </td>
                  <td className="px-3 py-2 capitalize">{r.application_method || '—'}</td>
                  <td className="px-3 py-2">{r.place_of_application || '—'}</td>
                  <td className="px-3 py-2 text-right font-mono font-semibold text-blue-700">
                    {r.consumption_ml_per_sqm}
                  </td>
                  <td className="px-3 py-2 text-right">{r.coats}</td>
                  <td className="px-3 py-2 text-right font-mono">
                    {r.specific_gravity_override ?? '—'}
                  </td>
                  <td className="px-3 py-2">
                    <Badge
                      status={r.is_active ? 'active' : 'inactive'}
                      label={r.is_active ? 'Active' : 'Off'}
                    />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(r)}>
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-600"
                        onClick={() => setDeleteTarget(r)}
                      >
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Create / Edit Dialog ─────────────────────────────────── */}
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        title={editItem ? 'Edit Consumption Rule' : 'Add Consumption Rule'}
        className="w-full max-w-2xl"
      >
        <div className="max-h-[75vh] space-y-4 overflow-y-auto pr-1">
          {/* Row 1: Rule # + Name */}
          <div className="grid grid-cols-4 gap-4">
            <Input
              label="Rule #"
              type="number"
              value={form.rule_number}
              onChange={(e) => setForm({ ...form, rule_number: e.target.value })}
              required
            />
            <div className="col-span-3">
              <Input
                label="Name *"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Glaze spray — standard tile 30x60"
              />
            </div>
          </div>

          {/* Row 2: Description */}
          <Input
            label="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="When this rule applies..."
          />

          {/* Row 3: Matching criteria */}
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Matching Criteria
            </h3>
            <div className="grid grid-cols-3 gap-3">
              <Select
                label="Recipe Type"
                options={RECIPE_TYPES}
                value={form.recipe_type}
                onChange={(e) => setForm({ ...form, recipe_type: e.target.value })}
              />
              <Select
                label="Product Type"
                options={productTypeOptions}
                value={form.product_type}
                onChange={(e) => setForm({ ...form, product_type: e.target.value })}
              />
              <Select
                label="Application Method"
                options={applicationMethodOptions}
                value={form.application_method}
                onChange={(e) => setForm({ ...form, application_method: e.target.value })}
              />
            </div>
            <div className="mt-3 grid grid-cols-3 gap-3">
              {/* Size: single or multi select */}
              <div>
                {!editItem && (
                  <label className="mb-1 flex items-center gap-2 text-xs text-gray-500">
                    <input
                      type="checkbox"
                      checked={multiSizeMode}
                      onChange={(e) => setMultiSizeMode(e.target.checked)}
                      className="rounded"
                    />
                    Multi-size (creates rule per size)
                  </label>
                )}
                {multiSizeMode && !editItem ? (
                  <MultiSelectChips
                    label="Sizes"
                    options={sizeOptions}
                    selected={form.size_ids}
                    onChange={(ids) => setForm({ ...form, size_ids: ids })}
                  />
                ) : (
                  <Select
                    label="Size"
                    options={[
                      { value: '', label: '— Any —' },
                      ...sizeOptions,
                    ]}
                    value={form.size_id}
                    onChange={(e) => setForm({ ...form, size_id: e.target.value })}
                  />
                )}
              </div>
              <Select
                label="Shape"
                options={shapeOptions}
                value={form.shape}
                onChange={(e) => setForm({ ...form, shape: e.target.value })}
              />
              <Select
                label="Place of Application"
                options={placeOfApplicationOptions}
                value={form.place_of_application}
                onChange={(e) => setForm({ ...form, place_of_application: e.target.value })}
              />
            </div>
            <div className="mt-3 grid grid-cols-3 gap-3">
              <Input
                label="Thickness Min (mm)"
                type="number"
                step="0.1"
                value={form.thickness_mm_min}
                onChange={(e) => setForm({ ...form, thickness_mm_min: e.target.value })}
              />
              <Input
                label="Thickness Max (mm)"
                type="number"
                step="0.1"
                value={form.thickness_mm_max}
                onChange={(e) => setForm({ ...form, thickness_mm_max: e.target.value })}
              />
              <Select
                label="Collection"
                options={collectionOptions}
                value={form.collection}
                onChange={(e) => setForm({ ...form, collection: e.target.value })}
              />
            </div>
            <div className="mt-3">
              <Select
                label="Color Collection"
                options={colorCollectionOptions}
                value={form.color_collection}
                onChange={(e) => setForm({ ...form, color_collection: e.target.value })}
              />
            </div>
          </div>

          {/* Row 4: Consumption values */}
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-blue-600">
              Consumption Calculation
            </h3>
            <div className="grid grid-cols-3 gap-3">
              <Input
                label="ml per m² *"
                type="number"
                step="0.01"
                value={form.consumption_ml_per_sqm}
                onChange={(e) => setForm({ ...form, consumption_ml_per_sqm: e.target.value })}
                placeholder="e.g. 850"
              />
              <Input
                label="Coats"
                type="number"
                min="1"
                value={form.coats}
                onChange={(e) => setForm({ ...form, coats: e.target.value })}
              />
              <Input
                label="SG Override"
                type="number"
                step="0.001"
                value={form.specific_gravity_override}
                onChange={(e) =>
                  setForm({ ...form, specific_gravity_override: e.target.value })
                }
                placeholder="Leave empty to use recipe SG"
              />
            </div>
          </div>

          {/* Multi-size info banner */}
          {multiSizeMode && form.size_ids.length > 1 && !editItem && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
              Will create <strong>{form.size_ids.length} separate rules</strong> — one for each selected size.
              Each rule name will have the size appended (e.g. &quot;{form.name} — 10x10&quot;).
            </div>
          )}

          {/* Row 5: Priority + Active + Notes */}
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Priority"
              type="number"
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
            />
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  className="rounded"
                />
                Active
              </label>
            </div>
          </div>
          <Input
            label="Notes"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="Additional notes..."
          />

          {formError && <p className="text-sm text-red-600">{formError}</p>}

          <div className="flex justify-end gap-2 border-t pt-3">
            <Button variant="secondary" onClick={closeDialog}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving
                ? 'Saving...'
                : editItem
                  ? 'Update'
                  : multiSizeMode && form.size_ids.length > 1
                    ? `Create ${form.size_ids.length} Rules`
                    : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* ── Delete Confirmation ──────────────────────────────────── */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete Consumption Rule"
        className="w-full max-w-sm"
      >
        {deleteTarget && (
          <div className="space-y-4">
            <p className="text-sm text-gray-700">
              Are you sure you want to delete rule #{deleteTarget.rule_number}{' '}
              <strong>{deleteTarget.name}</strong>?
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDeleteTarget(null)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
