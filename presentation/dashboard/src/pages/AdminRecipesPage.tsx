import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, FlaskConical } from 'lucide-react';
import { recipesApi, type RecipeItem, type RecipeMaterialItem, type RecipeMaterialBulkItem, type TemperatureGroupInfo } from '@/api/recipes';
import { Thermometer } from 'lucide-react';
import { materialsApi, type MaterialItem } from '@/api/materials';
import apiClient from '@/api/client';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/Table';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

/* ── ingredient group labels (by material_type) ─────────────────────── */
const INGREDIENT_GROUPS: { type: string; label: string; emoji: string }[] = [
  { type: 'frit',            label: 'Frits',               emoji: '\uD83D\uDD37' },
  { type: 'pigment',         label: 'Pigments',            emoji: '\uD83C\uDFA8' },
  { type: 'oxide_carbonate', label: 'Oxides / Carbonates', emoji: '\u2697\uFE0F' },
  { type: 'other_bulk',      label: 'Other Dry',           emoji: '\uD83D\uDCE6' },
];

/* ── types ──────────────────────────────────────────────────────────── */
interface RecipeForm {
  name: string;
  collection: string;
  color: string;
  application_type: string;
  specific_gravity: string;
  is_active: boolean;
}

interface IngredientRow {
  material_id: string;
  quantity: string;
}

const emptyForm: RecipeForm = {
  name: '',
  collection: '',
  color: '',
  application_type: '',
  specific_gravity: '',
  is_active: true,
};

/* ── component ──────────────────────────────────────────────────────── */
export default function AdminRecipesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<RecipeItem | null>(null);
  const [form, setForm] = useState<RecipeForm>(emptyForm);
  const [ingredients, setIngredients] = useState<IngredientRow[]>([]);
  const [waterGrams, setWaterGrams] = useState('');
  const [savingMaterials, setSavingMaterials] = useState(false);

  /* ── queries ───────────────────────────────────────────────────────── */
  const { data, isLoading } = useQuery<{ items: RecipeItem[]; total: number }>({
    queryKey: ['admin-recipes'],
    queryFn: () => recipesApi.list(),
  });

  const { data: materialsData } = useQuery<{ items: MaterialItem[] }>({
    queryKey: ['materials-catalog'],
    queryFn: () => materialsApi.list({ per_page: 200 }),
  });

  // Temperature groups for recipe assignment
  interface TempGroupOption { id: string; name: string; min_temperature: number; max_temperature: number; thermocouple: string | null; control_device: string | null; }
  const { data: tempGroups } = useQuery<TempGroupOption[]>({
    queryKey: ['temperature-groups'],
    queryFn: () => apiClient.get('/reference/temperature-groups').then((r) => r.data),
  });
  const [selectedTempGroupId, setSelectedTempGroupId] = useState<string>('');

  const allMaterials = materialsData?.items ?? [];
  const materialsByType = useMemo(() => {
    const map: Record<string, MaterialItem[]> = {};
    for (const m of allMaterials) {
      if (!map[m.material_type]) map[m.material_type] = [];
      map[m.material_type].push(m);
    }
    return map;
  }, [allMaterials]);

  const items = data?.items ?? [];

  /* ── mutations ─────────────────────────────────────────────────────── */
  const saveIngredients = useCallback(async (recipeId: string) => {
    const mats: RecipeMaterialBulkItem[] = [];
    for (const row of ingredients) {
      const qty = parseFloat(row.quantity);
      if (row.material_id && qty > 0) {
        mats.push({ material_id: row.material_id, quantity_per_unit: qty, unit: 'g_per_100g' });
      }
    }
    const waterQty = parseFloat(waterGrams);
    if (waterQty > 0) {
      const waterMat = allMaterials.find((m) => m.name.toLowerCase() === 'water');
      if (waterMat) {
        mats.push({ material_id: waterMat.id, quantity_per_unit: waterQty, unit: 'g_per_100g', notes: 'water' });
      }
    }
    if (mats.length > 0) {
      setSavingMaterials(true);
      try { await recipesApi.bulkUpdateMaterials(recipeId, mats); } finally { setSavingMaterials(false); }
    }
  }, [ingredients, waterGrams, allMaterials]);

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => recipesApi.create(payload),
    onSuccess: async (newRecipe: RecipeItem) => {
      await saveIngredients(newRecipe.id);
      queryClient.invalidateQueries({ queryKey: ['admin-recipes'] });
      closeDialog();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      recipesApi.update(id, payload),
    onSuccess: async () => {
      if (editItem) await saveIngredients(editItem.id);
      queryClient.invalidateQueries({ queryKey: ['admin-recipes'] });
      closeDialog();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => recipesApi.remove(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-recipes'] }); setDeleteId(null); },
  });

  /* ── dialog helpers ────────────────────────────────────────────────── */
  const closeDialog = useCallback(() => {
    setDialogOpen(false); setEditItem(null); setForm(emptyForm); setIngredients([]); setWaterGrams('');
  }, []);

  const openCreate = useCallback(() => {
    setEditItem(null); setForm(emptyForm); setIngredients([]); setWaterGrams(''); setSelectedTempGroupId(''); setDialogOpen(true);
  }, []);

  const openEdit = useCallback(async (item: RecipeItem) => {
    setEditItem(item);
    setForm({
      name: item.name,
      collection: item.collection ?? '',
      color: item.color ?? '',
      application_type: item.application_type ?? '',
      specific_gravity: item.specific_gravity != null ? String(item.specific_gravity) : '',
      is_active: item.is_active,
    });
    // Set current temperature group
    if (item.temperature_groups && item.temperature_groups.length > 0) {
      setSelectedTempGroupId(item.temperature_groups[0].id);
    } else {
      setSelectedTempGroupId('');
    }
    try {
      const mats: RecipeMaterialItem[] = await recipesApi.listMaterials(item.id);
      const rows: IngredientRow[] = [];
      let water = '';
      for (const m of mats) {
        if (m.material_name?.toLowerCase() === 'water') { water = String(m.quantity_per_unit); }
        else { rows.push({ material_id: m.material_id, quantity: String(m.quantity_per_unit) }); }
      }
      setIngredients(rows);
      setWaterGrams(water);
    } catch { setIngredients([]); setWaterGrams(''); }
    setDialogOpen(true);
  }, []);

  /** Save/update temperature group assignment for a recipe */
  const saveTempGroupAssignment = useCallback(async (recipeId: string, prevGroups: TemperatureGroupInfo[]) => {
    // Remove existing assignments
    for (const g of prevGroups) {
      try {
        await apiClient.delete(`/reference/temperature-groups/${g.id}/recipes/${recipeId}`);
      } catch { /* ignore if already removed */ }
    }
    // Add new assignment
    if (selectedTempGroupId) {
      try {
        await apiClient.post(`/reference/temperature-groups/${selectedTempGroupId}/recipes`, {
          recipe_id: recipeId,
          is_default: true,
        });
      } catch { /* ignore duplicate */ }
    }
  }, [selectedTempGroupId]);

  const handleSubmit = useCallback(async () => {
    const payload: Record<string, unknown> = {
      name: form.name,
      collection: form.collection || null,
      color: form.color || null,
      application_type: form.application_type || null,
      specific_gravity: form.specific_gravity ? parseFloat(form.specific_gravity) : null,
      is_active: form.is_active,
    };
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, payload });
      await saveTempGroupAssignment(editItem.id, editItem.temperature_groups || []);
    } else {
      createMutation.mutate(payload);
    }
  }, [form, editItem, createMutation, updateMutation, saveTempGroupAssignment]);

  const addIngredient = useCallback(() => {
    setIngredients((prev) => [...prev, { material_id: '', quantity: '' }]);
  }, []);

  const removeIngredient = useCallback((idx: number) => {
    setIngredients((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const updateIngredient = useCallback(
    (idx: number, field: 'material_id' | 'quantity', value: string) => {
      setIngredients((prev) => prev.map((row, i) => (i === idx ? { ...row, [field]: value } : row)));
    }, []
  );

  /* ── computed ───────────────────────────────────────────────────────── */
  const dryTotal = useMemo(() => ingredients.reduce((s, r) => s + (parseFloat(r.quantity) || 0), 0), [ingredients]);
  const totalWithWater = dryTotal + (parseFloat(waterGrams) || 0);
  const sg = form.specific_gravity ? parseFloat(form.specific_gravity) : null;
  const mlPer100g = sg && sg > 0 ? Math.round((totalWithWater / sg) * 100) / 100 : null;
  const saving = createMutation.isPending || updateMutation.isPending || savingMaterials;

  /* ── table columns ─────────────────────────────────────────────────── */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = useMemo(
    () => [
      { key: 'name', header: 'Name' },
      { key: 'collection', header: 'Collection', render: (r: RecipeItem) => r.collection || <span className="text-gray-400">&mdash;</span> },
      { key: 'color', header: 'Color', render: (r: RecipeItem) => r.color || <span className="text-gray-400">&mdash;</span> },
      { key: 'specific_gravity', header: 'SG', render: (r: RecipeItem) => r.specific_gravity != null ? r.specific_gravity : <span className="text-gray-400">&mdash;</span> },
      { key: 'temperature_groups', header: 'Temp Group', render: (r: RecipeItem) => {
        const groups = r.temperature_groups ?? [];
        if (groups.length === 0) return <span className="text-gray-400">&mdash;</span>;
        return (
          <div className="flex flex-col gap-0.5">
            {groups.map((g: TemperatureGroupInfo) => (
              <span key={g.id} className="inline-flex items-center gap-1 text-xs" title={g.description ?? `${g.min_temperature}–${g.max_temperature}°C`}>
                <Thermometer className="h-3 w-3 text-orange-500" />
                <span className="font-medium">{g.name}</span>
                <span className="text-gray-400">({g.min_temperature}–{g.max_temperature}°C)</span>
              </span>
            ))}
          </div>
        );
      }},
      { key: 'ingredients_count', header: 'Ingredients', render: (r: RecipeItem) => (
        <span className="inline-flex items-center gap-1 text-sm"><FlaskConical className="h-3.5 w-3.5 text-gray-400" />{r.ingredients_count ?? 0}</span>
      )},
      { key: 'is_active', header: 'Status', render: (r: RecipeItem) => <Badge status={r.is_active ? 'active' : 'inactive'} label={r.is_active ? 'Active' : 'Inactive'} /> },
      { key: 'actions', header: '', render: (r: RecipeItem) => (
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" onClick={() => openEdit(r)}>Edit</Button>
          <Button variant="ghost" size="sm" className="text-red-600" onClick={() => setDeleteId(r.id)}>Delete</Button>
        </div>
      )},
    ],
    [openEdit],
  );

  /* ── render ─────────────────────────────────────────────────────────── */
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recipes</h1>
          <p className="mt-1 text-sm text-gray-500">Manage product recipes and formulations</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>Back to Admin</Button>
          <Button onClick={openCreate}>+ Add Recipe</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 ? (
        <Card><p className="py-8 text-center text-gray-400">No recipes found</p></Card>
      ) : (
        <DataTable columns={columns} data={items as unknown as Record<string, unknown>[]} />
      )}

      {/* ── Create / Edit Dialog ──────────────────────────────────────── */}
      <Dialog open={dialogOpen} onClose={closeDialog} title={editItem ? 'Edit Recipe' : 'Add Recipe'} className="w-full max-w-2xl">
        <div className="max-h-[75vh] space-y-5 overflow-y-auto pr-1">
          <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <div className="grid grid-cols-3 gap-4">
            <Input label="Collection" value={form.collection} onChange={(e) => setForm({ ...form, collection: e.target.value })} />
            <Input label="Color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
            <Input label="Application Type" value={form.application_type} onChange={(e) => setForm({ ...form, application_type: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Specific Gravity (SG)" type="number" step="0.001" placeholder="e.g. 1.450" value={form.specific_gravity} onChange={(e) => setForm({ ...form, specific_gravity: e.target.value })} />
            <label className="flex items-center gap-2 self-end pb-2 text-sm">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
              Active
            </label>
          </div>

          {/* ── Temperature Group Selector ──────────────────────────────── */}
          <div>
            <label className="mb-1 flex items-center gap-1.5 text-sm font-medium text-gray-700">
              <Thermometer className="h-4 w-4 text-orange-500" /> Temperature Group
            </label>
            <select
              value={selectedTempGroupId}
              onChange={(e) => setSelectedTempGroupId(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">-- Not assigned --</option>
              {(tempGroups || []).map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name} ({g.min_temperature}–{g.max_temperature}°C)
                </option>
              ))}
            </select>
          </div>

          {/* ── Ingredients ────────────────────────────────────────────── */}
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-700">Ingredients (per 100 g frit base)</h3>
              <Button variant="secondary" size="sm" onClick={addIngredient}><Plus className="mr-1 h-3.5 w-3.5" /> Add</Button>
            </div>

            {ingredients.length === 0 && (
              <p className="py-3 text-center text-xs text-gray-400">No ingredients yet. Click &quot;Add&quot; to start.</p>
            )}

            {/* Grouped rows */}
            {INGREDIENT_GROUPS.map((group) => {
              const groupIdxs = ingredients
                .map((row, idx) => ({ row, idx }))
                .filter(({ row }) => {
                  const mat = allMaterials.find((m) => m.id === row.material_id);
                  return mat?.material_type === group.type;
                });
              if (groupIdxs.length === 0) return null;
              return (
                <div key={group.type} className="mb-3">
                  <div className="mb-1 text-xs font-medium text-gray-500">{group.emoji} {group.label}</div>
                  {groupIdxs.map(({ idx }) => (
                    <IngredientRowEditor
                      key={idx}
                      row={ingredients[idx]}
                      materials={materialsByType[group.type] || []}
                      allMaterials={allMaterials}
                      onChange={(f, v) => updateIngredient(idx, f, v)}
                      onRemove={() => removeIngredient(idx)}
                    />
                  ))}
                </div>
              );
            })}

            {/* Ungrouped rows */}
            {ingredients.map((row, idx) => {
              if (!row.material_id) return (
                <IngredientRowEditor
                  key={idx}
                  row={row}
                  materials={allMaterials}
                  allMaterials={allMaterials}
                  onChange={(f, v) => updateIngredient(idx, f, v)}
                  onRemove={() => removeIngredient(idx)}
                />
              );
              const mat = allMaterials.find((m) => m.id === row.material_id);
              if (!mat || INGREDIENT_GROUPS.some((g) => g.type === mat.material_type)) return null;
              return (
                <IngredientRowEditor
                  key={idx}
                  row={row}
                  materials={allMaterials}
                  allMaterials={allMaterials}
                  onChange={(f, v) => updateIngredient(idx, f, v)}
                  onRemove={() => removeIngredient(idx)}
                />
              );
            })}

            {/* Water */}
            <div className="mt-3 border-t border-gray-200 pt-3">
              <div className="mb-1 text-xs font-medium text-gray-500">{'\uD83D\uDCA7'} Water</div>
              <div className="flex items-center gap-2">
                <input type="number" step="0.1" placeholder="grams" value={waterGrams} onChange={(e) => setWaterGrams(e.target.value)} className="w-28 rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                <span className="text-xs text-gray-400">g per 100 g frit</span>
              </div>
            </div>

            {/* Totals */}
            <div className="mt-3 flex gap-6 border-t border-gray-200 pt-3 text-xs text-gray-600">
              <div>Dry total: <span className="font-semibold">{dryTotal.toFixed(2)} g</span></div>
              <div>Total + water: <span className="font-semibold">{totalWithWater.toFixed(2)} g</span></div>
              {mlPer100g != null && <div>Volume (SG {form.specific_gravity}): <span className="font-semibold">{mlPer100g} ml</span></div>}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={!form.name || saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Recipe">
        <p className="text-sm text-gray-600">Are you sure you want to delete this recipe? This action cannot be undone.</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => deleteId && deleteMutation.mutate(deleteId)} disabled={deleteMutation.isPending}>
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

/* ── IngredientRowEditor sub-component ─────────────────────────────── */
function IngredientRowEditor({ row, materials, allMaterials, onChange, onRemove }: {
  row: IngredientRow;
  materials: MaterialItem[];
  allMaterials: MaterialItem[];
  onChange: (field: 'material_id' | 'quantity', value: string) => void;
  onRemove: () => void;
}) {
  return (
    <div className="mb-1.5 flex items-center gap-2">
      <select
        value={row.material_id}
        onChange={(e) => onChange('material_id', e.target.value)}
        className="min-w-0 flex-1 rounded-md border border-gray-300 px-2 py-1.5 text-sm"
      >
        <option value="">Select material...</option>
        {materials.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        {row.material_id && !materials.find((m) => m.id === row.material_id) && (
          <option value={row.material_id}>{allMaterials.find((m) => m.id === row.material_id)?.name ?? row.material_id}</option>
        )}
      </select>
      <input
        type="number" step="0.0001" placeholder="g"
        value={row.quantity}
        onChange={(e) => onChange('quantity', e.target.value)}
        className="w-24 rounded-md border border-gray-300 px-2 py-1.5 text-right text-sm"
      />
      <span className="text-xs text-gray-400">g</span>
      <button type="button" onClick={onRemove} className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600">
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
