import { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, FlaskConical, Copy } from 'lucide-react';
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
import { CsvImportDialog } from '@/components/admin/CsvImportDialog';
import { CSV_CONFIGS } from '@/config/csvImportConfigs';

/* ── ingredient group labels (by material_type) ─────────────────────── */
const INGREDIENT_GROUPS: { type: string; label: string; emoji: string }[] = [
  { type: 'frit',            label: 'Frits',               emoji: '🔷' },
  { type: 'pigment',         label: 'Pigments',            emoji: '🎨' },
  { type: 'oxide_carbonate', label: 'Oxides / Carbonates', emoji: '⚗️' },
  { type: 'other_bulk',      label: 'Other Dry',           emoji: '📦' },
];

/* ── types ──────────────────────────────────────────────────────────── */
interface RecipeForm {
  name: string;
  color_collection: string;
  recipe_type: string;
  engobe_type: string;
  client_name: string;
  specific_gravity: string;
  consumption_spray_ml_per_sqm: string;
  consumption_brush_ml_per_sqm: string;
  is_default: boolean;
  is_active: boolean;
}

interface IngredientRow {
  material_id: string;
  quantity: string;
  spray_rate: string;
  brush_rate: string;
  splash_rate: string;
  silk_screen_rate: string;
}

const RECIPE_TYPE_OPTIONS = [
  { value: 'product', label: 'Product' },
  { value: 'glaze', label: 'Glaze' },
  { value: 'engobe', label: 'Engobe' },
];

const ENGOBE_TYPE_OPTIONS = [
  { value: 'standard', label: 'Main Engobe (основной)' },
  { value: 'shelf_coating', label: 'Kiln Shelf Engobe (для полок)' },
  { value: 'hole_filler', label: 'Pore Filler Engobe (для заделки пор)' },
];

const emptyForm: RecipeForm = {
  name: '',
  color_collection: '',
  recipe_type: 'product',
  engobe_type: '',
  client_name: '',
  specific_gravity: '',
  consumption_spray_ml_per_sqm: '',
  consumption_brush_ml_per_sqm: '',
  is_default: false,
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
  const [mutationError, setMutationError] = useState('');
  const [savingMaterials, setSavingMaterials] = useState(false);
  const [csvOpen, setCsvOpen] = useState(false);
  const [cloneFromId, setCloneFromId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false);
  const [returnPositionId, setReturnPositionId] = useState<string | null>(null);

  // Auto-open create dialog from URL params (e.g. from Force Unblock)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('create') === 'true') {
      setForm({
        ...emptyForm,
        name: params.get('name') || '',
        color_collection: params.get('collection') || '',
        recipe_type: 'glaze',
      });
      setReturnPositionId(params.get('position_id') || null);
      setDialogOpen(true);
      // Clean URL without reload
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  /* ── queries ───────────────────────────────────────────────────────── */
  const { data, isLoading } = useQuery<{ items: RecipeItem[]; total: number }>({
    queryKey: ['admin-recipes'],
    queryFn: () => recipesApi.list(),
  });

  const { data: materialsData } = useQuery<{ items: MaterialItem[] }>({
    queryKey: ['materials-catalog'],
    queryFn: () => materialsApi.list({ per_page: 200 }),
  });

  // Color collections for glaze recipes
  const { data: colorCollections } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['ref-color-collections'],
    queryFn: () => apiClient.get('/reference/color-collections').then((r) => r.data),
  });

  // Temperature groups for recipe assignment
  interface TempGroupOption { id: string; name: string; temperature: number; thermocouple: string | null; control_device: string | null; }
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
        const item: RecipeMaterialBulkItem = { material_id: row.material_id, quantity_per_unit: qty, unit: 'g_per_100g' };
        if (row.spray_rate) item.spray_rate = parseFloat(row.spray_rate);
        if (row.brush_rate) item.brush_rate = parseFloat(row.brush_rate);
        if (row.splash_rate) item.splash_rate = parseFloat(row.splash_rate);
        if (row.silk_screen_rate) item.silk_screen_rate = parseFloat(row.silk_screen_rate);
        mats.push(item);
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
      try {
        await recipesApi.bulkUpdateMaterials(recipeId, mats);
      } catch (e) {
        console.error('Failed to save ingredients:', e);
      } finally {
        setSavingMaterials(false);
      }
    }
  }, [ingredients, waterGrams, allMaterials]);

  const extractError = (err: unknown): string => {
    const resp = (err as { response?: { data?: { detail?: unknown } } })?.response?.data;
    if (!resp) return String(err);
    if (typeof resp.detail === 'string') return resp.detail;
    if (Array.isArray(resp.detail)) return resp.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('; ');
    return JSON.stringify(resp);
  };

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => recipesApi.create(payload),
    onSuccess: async (newRecipe: RecipeItem) => {
      setMutationError('');
      // Save ingredients + temp group — errors should NOT block dialog close
      try { await saveIngredients(newRecipe.id); } catch (e) { console.error('saveIngredients failed:', e); }
      try { await saveTempGroupAssignment(newRecipe.id, []); } catch (e) { console.error('saveTempGroup failed:', e); }

      // If came from Force Unblock — bind recipe to position + unblock
      if (returnPositionId) {
        try {
          const { default: apiClient } = await import('../api/client');
          await apiClient.patch(`/positions/${returnPositionId}`, { recipe_id: newRecipe.id });
          await apiClient.post(`/positions/${returnPositionId}/force-unblock`, {
            notes: `New recipe created & assigned: ${newRecipe.name}`,
          });
          setReturnPositionId(null);
          navigate('/?tab=blocking');
        } catch (e) {
          console.error('Auto-assign recipe to position failed:', e);
          setMutationError(
            `Recipe created, but failed to assign to position: ${extractError(e)}. ` +
            `You can manually assign it from the position details.`
          );
        }
      }

      queryClient.invalidateQueries({ queryKey: ['admin-recipes'] });
      closeDialog();
    },
    onError: (err: unknown) => {
      setMutationError(extractError(err));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      recipesApi.update(id, payload),
    onSuccess: async () => {
      setMutationError('');
      if (editItem) {
        try { await saveIngredients(editItem.id); } catch (e) { console.error('saveIngredients failed:', e); }
        try { await saveTempGroupAssignment(editItem.id, editItem.temperature_groups || []); } catch (e) { console.error('saveTempGroup failed:', e); }
      }
      queryClient.invalidateQueries({ queryKey: ['admin-recipes'] });
      closeDialog();
    },
    onError: (err: unknown) => {
      setMutationError(extractError(err));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => recipesApi.remove(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-recipes'] }); setDeleteId(null); },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) => recipesApi.bulkDelete(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-recipes'] });
      setSelectedIds(new Set());
      setBulkDeleteConfirm(false);
    },
  });

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedIds((prev) => prev.size === items.length ? new Set() : new Set(items.map((r) => r.id)));
  }, [items]);

  /* ── dialog helpers ────────────────────────────────────────────────── */
  const closeDialog = useCallback(() => {
    setDialogOpen(false); setEditItem(null); setForm(emptyForm); setIngredients([]); setWaterGrams(''); setCloneFromId(null); setMutationError('');
  }, []);

  const openCreate = useCallback(() => {
    setEditItem(null); setForm(emptyForm); setIngredients([]); setWaterGrams(''); setSelectedTempGroupId(''); setCloneFromId(null); setDialogOpen(true);
  }, []);

  const openEdit = useCallback(async (item: RecipeItem) => {
    setEditItem(item);
    setCloneFromId(null);
    setForm({
      name: item.name,
      color_collection: item.color_collection ?? '',
      recipe_type: item.recipe_type || 'product',
      engobe_type: item.engobe_type ?? '',
      client_name: item.client_name ?? '',
      specific_gravity: item.specific_gravity != null ? String(item.specific_gravity) : '',
      consumption_spray_ml_per_sqm: item.consumption_spray_ml_per_sqm != null ? String(item.consumption_spray_ml_per_sqm) : '',
      consumption_brush_ml_per_sqm: item.consumption_brush_ml_per_sqm != null ? String(item.consumption_brush_ml_per_sqm) : '',
      is_default: item.is_default ?? false,
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
        else { rows.push({ material_id: m.material_id, quantity: String(m.quantity_per_unit), spray_rate: m.spray_rate != null ? String(m.spray_rate) : '', brush_rate: m.brush_rate != null ? String(m.brush_rate) : '', splash_rate: m.splash_rate != null ? String(m.splash_rate) : '', silk_screen_rate: m.silk_screen_rate != null ? String(m.silk_screen_rate) : '' }); }
      }
      setIngredients(rows);
      setWaterGrams(water);
    } catch { setIngredients([]); setWaterGrams(''); }
    setDialogOpen(true);
  }, []);

  /** Clone: open create dialog pre-filled from an existing recipe */
  const openClone = useCallback(async (item: RecipeItem) => {
    setEditItem(null); // it's a CREATE, not edit
    setCloneFromId(item.id);
    setForm({
      name: `${item.name} (copy)`,
      color_collection: item.color_collection ?? '',
      recipe_type: item.recipe_type || 'product',
      engobe_type: item.engobe_type ?? '',
      client_name: item.client_name ?? '',
      specific_gravity: item.specific_gravity != null ? String(item.specific_gravity) : '',
      consumption_spray_ml_per_sqm: item.consumption_spray_ml_per_sqm != null ? String(item.consumption_spray_ml_per_sqm) : '',
      consumption_brush_ml_per_sqm: item.consumption_brush_ml_per_sqm != null ? String(item.consumption_brush_ml_per_sqm) : '',
      is_default: false,
      is_active: true,
    });
    // Load original ingredients
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
        else { rows.push({ material_id: m.material_id, quantity: String(m.quantity_per_unit), spray_rate: m.spray_rate != null ? String(m.spray_rate) : '', brush_rate: m.brush_rate != null ? String(m.brush_rate) : '', splash_rate: m.splash_rate != null ? String(m.splash_rate) : '', silk_screen_rate: m.silk_screen_rate != null ? String(m.silk_screen_rate) : '' }); }
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

  const handleSubmit = useCallback(() => {
    setMutationError('');
    const payload: Record<string, unknown> = {
      name: form.name,
      color_collection: form.color_collection || null,
      recipe_type: form.recipe_type || 'product',
      engobe_type: form.recipe_type === 'engobe' ? (form.engobe_type || null) : null,
      client_name: form.client_name || null,
      specific_gravity: form.specific_gravity ? parseFloat(form.specific_gravity) : null,
      consumption_spray_ml_per_sqm: form.consumption_spray_ml_per_sqm ? parseFloat(form.consumption_spray_ml_per_sqm) : null,
      consumption_brush_ml_per_sqm: form.consumption_brush_ml_per_sqm ? parseFloat(form.consumption_brush_ml_per_sqm) : null,
      is_default: form.is_default,
      is_active: form.is_active,
    };
    if (cloneFromId && !editItem) {
      payload.clone_from_id = cloneFromId;
    }
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  }, [form, editItem, cloneFromId, createMutation, updateMutation]);

  const addIngredient = useCallback(() => {
    setIngredients((prev) => [...prev, { material_id: '', quantity: '', spray_rate: '', brush_rate: '', splash_rate: '', silk_screen_rate: '' }]);
  }, []);

  const removeIngredient = useCallback((idx: number) => {
    setIngredients((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const updateIngredient = useCallback(
    (idx: number, field: keyof IngredientRow, value: string) => {
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
      { key: '_select', header: '', render: (r: RecipeItem) => (
        <input type="checkbox" checked={selectedIds.has(r.id)} onChange={() => toggleSelect(r.id)} className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer" />
      )},
      { key: 'name', header: 'Name' },
      { key: 'recipe_type', header: 'Type', render: (r: RecipeItem) => {
        const labels: Record<string, string> = { product: 'Product', glaze: 'Glaze', engobe: 'Engobe' };
        const engobeLabels: Record<string, string> = { standard: 'Main', shelf_coating: 'Shelf Coating', hole_filler: 'Pore Filler' };
        return (
          <div className="flex flex-col gap-0.5">
            <span className="text-sm">{labels[r.recipe_type] || r.recipe_type}</span>
            {r.recipe_type === 'engobe' && r.engobe_type && (
              <span className="text-xs text-orange-600 font-medium">{engobeLabels[r.engobe_type] || r.engobe_type}</span>
            )}
          </div>
        );
      }},
      { key: 'color_collection', header: 'Color Collection', render: (r: RecipeItem) => r.color_collection || <span className="text-gray-400">&mdash;</span> },
      { key: 'client_name', header: 'Client', render: (r: RecipeItem) => r.client_name || <span className="text-gray-400">&mdash;</span> },
      { key: 'specific_gravity', header: 'SG', render: (r: RecipeItem) => r.specific_gravity != null ? r.specific_gravity : <span className="text-gray-400">&mdash;</span> },
      { key: 'consumption_spray', header: 'Spray ml/m²', render: (r: RecipeItem) => r.consumption_spray_ml_per_sqm != null ? <span className="font-mono text-sm">{r.consumption_spray_ml_per_sqm}</span> : <span className="text-gray-400">&mdash;</span> },
      { key: 'consumption_brush', header: 'Brush ml/m²', render: (r: RecipeItem) => r.consumption_brush_ml_per_sqm != null ? <span className="font-mono text-sm">{r.consumption_brush_ml_per_sqm}</span> : <span className="text-gray-400">&mdash;</span> },
      { key: 'temperature_groups', header: 'Temp Group', render: (r: RecipeItem) => {
        const groups = r.temperature_groups ?? [];
        if (groups.length === 0) return <span className="text-gray-400">&mdash;</span>;
        return (
          <div className="flex flex-col gap-0.5">
            {groups.map((g: TemperatureGroupInfo) => (
              <span key={g.id} className="inline-flex items-center gap-1 text-xs" title={g.description ?? `${g.temperature}°C`}>
                <Thermometer className="h-3 w-3 text-orange-500" />
                <span className="font-medium">{g.name}</span>
                <span className="text-gray-400">({g.temperature}°C)</span>
              </span>
            ))}
          </div>
        );
      }},
      { key: 'ingredients_count', header: 'Ingredients', render: (r: RecipeItem) => (
        <span className="inline-flex items-center gap-1 text-sm"><FlaskConical className="h-3.5 w-3.5 text-gray-400" />{r.ingredients_count ?? 0}</span>
      )},
      { key: 'is_default', header: 'Default', render: (r: RecipeItem) => r.is_default ? <Badge status="active" label="Default" /> : null },
      { key: 'is_active', header: 'Status', render: (r: RecipeItem) => <Badge status={r.is_active ? 'active' : 'inactive'} label={r.is_active ? 'Active' : 'Inactive'} /> },
      { key: 'actions', header: '', render: (r: RecipeItem) => (
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" onClick={() => openEdit(r)}>Edit</Button>
          <Button variant="ghost" size="sm" className="text-blue-600" onClick={() => openClone(r)} title="Clone recipe">
            <Copy className="mr-1 h-3.5 w-3.5" /> Clone
          </Button>
          <Button variant="ghost" size="sm" className="text-red-600" onClick={() => setDeleteId(r.id)}>Delete</Button>
        </div>
      )},
    ],
    [openEdit, openClone, selectedIds, toggleSelect],
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
          <Button variant="secondary" onClick={() => setCsvOpen(true)}>Import CSV</Button>
          <Button onClick={openCreate}>+ Add Recipe</Button>
        </div>
      </div>

      {/* Bulk selection controls */}
      {items.length > 0 && (
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={selectedIds.size === items.length && items.length > 0}
              onChange={toggleSelectAll}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Select all ({items.length})
          </label>
          {selectedIds.size > 0 && (
            <>
              <span className="text-sm font-medium text-blue-600">{selectedIds.size} selected</span>
              <Button variant="danger" size="sm" onClick={() => setBulkDeleteConfirm(true)}>
                <Trash2 className="mr-1 h-3.5 w-3.5" /> Delete Selected
              </Button>
            </>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 ? (
        <Card><p className="py-8 text-center text-gray-400">No recipes found</p></Card>
      ) : (
        <DataTable columns={columns} data={items as unknown as Record<string, unknown>[]} />
      )}

      {/* ── Create / Edit Dialog ──────────────────────────────────────── */}
      <Dialog open={dialogOpen} onClose={closeDialog} title={editItem ? 'Edit Recipe' : cloneFromId ? 'Clone Recipe' : 'Add Recipe'} className="w-full max-w-2xl">
        <div className="max-h-[75vh] space-y-5 overflow-y-auto pr-1">
          {cloneFromId && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
              Cloning from existing recipe. Ingredients and firing stages will be copied.
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <Input label="Client Name" placeholder="e.g. PT Bali Stone" value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Color Collection</label>
              <select
                value={form.color_collection}
                onChange={(e) => setForm({ ...form, color_collection: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                <option value="">— None —</option>
                {(colorCollections ?? []).map((cc) => (
                  <option key={cc.id} value={cc.name}>{cc.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Recipe Type</label>
              <select
                value={form.recipe_type}
                onChange={(e) => setForm({ ...form, recipe_type: e.target.value, engobe_type: '' })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                {RECIPE_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            {form.recipe_type === 'engobe' && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Engobe Category</label>
                <select
                  value={form.engobe_type}
                  onChange={(e) => setForm({ ...form, engobe_type: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                >
                  <option value="">-- Select category --</option>
                  {ENGOBE_TYPE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Input label="Specific Gravity (SG)" type="number" step="0.001" placeholder="e.g. 1.450" value={form.specific_gravity} onChange={(e) => setForm({ ...form, specific_gravity: e.target.value })} />
            <Input label={"Spray (ml/m²)"} type="number" step="0.01" placeholder="e.g. 850" value={form.consumption_spray_ml_per_sqm} onChange={(e) => setForm({ ...form, consumption_spray_ml_per_sqm: e.target.value })} />
            <Input label={"Brush (ml/m²)"} type="number" step="0.01" placeholder="e.g. 1200" value={form.consumption_brush_ml_per_sqm} onChange={(e) => setForm({ ...form, consumption_brush_ml_per_sqm: e.target.value })} />
          </div>
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
              Active
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} className="rounded" />
              Default recipe
              <span className="text-xs text-gray-400">(auto-picked when this type is used)</span>
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
                  {g.name} ({g.temperature}°C)
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
              <div className="mb-1 text-xs font-medium text-gray-500">{'💧'} Water</div>
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

          {mutationError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
              Error: {mutationError}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={!form.name || saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      <CsvImportDialog open={csvOpen} onClose={() => setCsvOpen(false)} {...CSV_CONFIGS.recipes} onSuccess={() => queryClient.invalidateQueries({ queryKey: ['admin-recipes'] })} />

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

      {/* Bulk Delete Confirmation */}
      <Dialog open={bulkDeleteConfirm} onClose={() => setBulkDeleteConfirm(false)} title="Delete Selected Recipes">
        <p className="text-sm text-gray-600">
          Are you sure you want to delete <span className="font-bold text-red-600">{selectedIds.size}</span> recipe{selectedIds.size !== 1 ? 's' : ''}?
          This will also remove all their ingredients and temperature group assignments. This action cannot be undone.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setBulkDeleteConfirm(false)}>Cancel</Button>
          <Button variant="danger" onClick={() => bulkDeleteMutation.mutate(Array.from(selectedIds))} disabled={bulkDeleteMutation.isPending}>
            {bulkDeleteMutation.isPending ? 'Deleting...' : `Delete ${selectedIds.size} Recipe${selectedIds.size !== 1 ? 's' : ''}`}
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
  onChange: (field: keyof IngredientRow, value: string) => void;
  onRemove: () => void;
}) {
  const [showRates, setShowRates] = useState(false);
  return (
    <div className="mb-1.5">
      <div className="flex items-center gap-2">
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
        <button type="button" onClick={() => setShowRates(!showRates)} className="rounded p-1 text-gray-400 hover:bg-blue-50 hover:text-blue-600" title="Per-method rates">
          {showRates ? '▲' : '▼'}
        </button>
        <button type="button" onClick={onRemove} className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600">
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
      {showRates && (
        <div className="mt-1 ml-4 flex flex-wrap gap-2">
          <div className="flex items-center gap-1">
            <label className="text-xs text-gray-500 w-12">Spray</label>
            <input type="number" step="0.01" placeholder="ml/m\u00B2" value={row.spray_rate} onChange={(e) => onChange('spray_rate', e.target.value)} className="w-20 rounded border border-gray-200 px-1.5 py-1 text-xs text-right" />
          </div>
          <div className="flex items-center gap-1">
            <label className="text-xs text-gray-500 w-12">Brush</label>
            <input type="number" step="0.01" placeholder="ml/m\u00B2" value={row.brush_rate} onChange={(e) => onChange('brush_rate', e.target.value)} className="w-20 rounded border border-gray-200 px-1.5 py-1 text-xs text-right" />
          </div>
          <div className="flex items-center gap-1">
            <label className="text-xs text-gray-500 w-12">Splash</label>
            <input type="number" step="0.01" placeholder="ml/m\u00B2" value={row.splash_rate} onChange={(e) => onChange('splash_rate', e.target.value)} className="w-20 rounded border border-gray-200 px-1.5 py-1 text-xs text-right" />
          </div>
          <div className="flex items-center gap-1">
            <label className="text-xs text-gray-500 w-16">Silkscreen</label>
            <input type="number" step="0.01" placeholder="ml/m\u00B2" value={row.silk_screen_rate} onChange={(e) => onChange('silk_screen_rate', e.target.value)} className="w-20 rounded border border-gray-200 px-1.5 py-1 text-xs text-right" />
          </div>
        </div>
      )}
    </div>
  );
}
