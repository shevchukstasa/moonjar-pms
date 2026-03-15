import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  useConsumptionRules,
  useCreateConsumptionRule,
  useUpdateConsumptionRule,
  useDeleteConsumptionRule,
} from '@/hooks/useConsumptionRules';
import { useSizes } from '@/hooks/useSizes';
import type { ConsumptionRuleItem, ConsumptionRuleInput } from '@/api/consumptionRules';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

/* ── Constants ──────────────────────────────────────────────────────── */

const RECIPE_TYPES = [
  { value: '', label: '— Any —' },
  { value: 'glaze', label: 'Glaze' },
  { value: 'engobe', label: 'Engobe' },
];

const APPLICATION_METHODS = [
  { value: '', label: '— Any —' },
  { value: 'spray', label: 'Spray' },
  { value: 'brush', label: 'Brush' },
  { value: 'dip', label: 'Dip' },
];

const PRODUCT_TYPES = [
  { value: '', label: '— Any —' },
  { value: 'tile', label: 'Tile' },
  { value: 'sink', label: 'Sink' },
  { value: 'custom_product', label: 'Custom Product' },
];

const SHAPES = [
  { value: '', label: '— Any —' },
  { value: 'rectangle', label: 'Rectangle' },
  { value: 'square', label: 'Square' },
  { value: 'circle', label: 'Circle' },
  { value: 'hexagon', label: 'Hexagon' },
  { value: 'irregular', label: 'Irregular' },
];

/* ── Form interface ─────────────────────────────────────────────── */

interface RuleForm {
  rule_number: string;
  name: string;
  description: string;
  collection: string;
  color_collection: string;
  product_type: string;
  size_id: string;
  shape: string;
  thickness_mm_min: string;
  thickness_mm_max: string;
  place_of_application: string;
  recipe_type: string;
  application_method: string;
  consumption_ml_per_sqm: string;
  coats: string;
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
  shape: '',
  thickness_mm_min: '',
  thickness_mm_max: '',
  place_of_application: '',
  recipe_type: '',
  application_method: '',
  consumption_ml_per_sqm: '',
  coats: '1',
  specific_gravity_override: '',
  priority: '0',
  is_active: true,
  notes: '',
};

/* ── Component ──────────────────────────────────────────────────── */

export default function ConsumptionRulesPage() {
  const navigate = useNavigate();
  const { data: rules, isLoading } = useConsumptionRules(true);
  const { data: sizesData } = useSizes();
  const sizes = sizesData?.items ?? [];
  const createMutation = useCreateConsumptionRule();
  const updateMutation = useUpdateConsumptionRule();
  const deleteMutation = useDeleteConsumptionRule();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editItem, setEditItem] = useState<ConsumptionRuleItem | null>(null);
  const [form, setForm] = useState<RuleForm>(emptyForm);
  const [formError, setFormError] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<ConsumptionRuleItem | null>(null);

  /* ── Helpers ───────────────────────────────────────────────────── */

  const openCreate = useCallback(() => {
    setEditItem(null);
    const nextNum = rules && rules.length > 0
      ? Math.max(...rules.map((r) => r.rule_number)) + 1
      : 1;
    setForm({ ...emptyForm, rule_number: String(nextNum) });
    setFormError('');
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
      is_active: item.is_active,
      notes: item.notes ?? '',
    });
    setFormError('');
    setDialogOpen(true);
  }, []);

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setEditItem(null);
    setForm(emptyForm);
    setFormError('');
  }, []);

  const handleSave = useCallback(async () => {
    if (!form.name.trim()) { setFormError('Name is required'); return; }
    if (!form.consumption_ml_per_sqm) { setFormError('Consumption ml/m² is required'); return; }
    setFormError('');

    const payload: ConsumptionRuleInput = {
      rule_number: parseInt(form.rule_number) || 0,
      name: form.name.trim(),
      description: form.description || null,
      collection: form.collection || null,
      color_collection: form.color_collection || null,
      product_type: form.product_type || null,
      size_id: form.size_id || null,
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
    };

    try {
      if (editItem) {
        await updateMutation.mutateAsync({ id: editItem.id, data: payload });
      } else {
        await createMutation.mutateAsync(payload);
      }
      closeDialog();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Save failed');
    }
  }, [form, editItem, createMutation, updateMutation, closeDialog]);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(deleteTarget.id);
      setDeleteTarget(null);
    } catch { /* ignore */ }
  }, [deleteTarget, deleteMutation]);

  const saving = createMutation.isPending || updateMutation.isPending;

  /* ── Render ────────────────────────────────────────────────────── */

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
                options={PRODUCT_TYPES}
                value={form.product_type}
                onChange={(e) => setForm({ ...form, product_type: e.target.value })}
              />
              <Select
                label="Application Method"
                options={APPLICATION_METHODS}
                value={form.application_method}
                onChange={(e) => setForm({ ...form, application_method: e.target.value })}
              />
            </div>
            <div className="mt-3 grid grid-cols-3 gap-3">
              <Select
                label="Size"
                options={[
                  { value: '', label: '— Any —' },
                  ...sizes.map((s) => ({
                    value: s.id,
                    label: `${s.name} (${s.width_mm}×${s.height_mm})`,
                  })),
                ]}
                value={form.size_id}
                onChange={(e) => setForm({ ...form, size_id: e.target.value })}
              />
              <Select
                label="Shape"
                options={SHAPES}
                value={form.shape}
                onChange={(e) => setForm({ ...form, shape: e.target.value })}
              />
              <Input
                label="Place of Application"
                value={form.place_of_application}
                onChange={(e) => setForm({ ...form, place_of_application: e.target.value })}
                placeholder="e.g. top, bottom, edges"
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
              <Input
                label="Collection"
                value={form.collection}
                onChange={(e) => setForm({ ...form, collection: e.target.value })}
                placeholder="e.g. Natural"
              />
            </div>
            <div className="mt-3">
              <Input
                label="Color Collection"
                value={form.color_collection}
                onChange={(e) => setForm({ ...form, color_collection: e.target.value })}
                placeholder="e.g. Earth Tones"
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
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
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
