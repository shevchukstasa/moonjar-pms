import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recipesApi } from '@/api/recipes';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/Table';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

interface Recipe {
  id: string;
  name: string;
  collection: string | null;
  color: string | null;
  size: string | null;
  application_type: string | null;
  place_of_application: string | null;
  finishing_type: string | null;
  thickness_mm: number;
  description: string | null;
  is_active: boolean;
}

interface RecipeForm {
  name: string;
  collection: string;
  color: string;
  size: string;
  application_type: string;
  place_of_application: string;
  finishing_type: string;
  thickness_mm: string;
  description: string;
  is_active: boolean;
}

const emptyForm: RecipeForm = {
  name: '',
  collection: '',
  color: '',
  size: '',
  application_type: '',
  place_of_application: '',
  finishing_type: '',
  thickness_mm: '11.0',
  description: '',
  is_active: true,
};

export default function AdminRecipesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<Recipe | null>(null);
  const [form, setForm] = useState<RecipeForm>(emptyForm);

  const { data, isLoading } = useQuery<{ items: Recipe[]; total: number }>({
    queryKey: ['admin-recipes'],
    queryFn: () => recipesApi.list(),
  });

  const items = data?.items ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => recipesApi.create(payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-recipes'] }); closeDialog(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => recipesApi.update(id, payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-recipes'] }); closeDialog(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => recipesApi.remove(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-recipes'] }); setDeleteId(null); },
  });

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setEditItem(null);
    setForm(emptyForm);
  }, []);

  const openCreate = useCallback(() => {
    setEditItem(null);
    setForm(emptyForm);
    setDialogOpen(true);
  }, []);

  const openEdit = useCallback((item: Recipe) => {
    setEditItem(item);
    setForm({
      name: item.name,
      collection: item.collection ?? '',
      color: item.color ?? '',
      size: item.size ?? '',
      application_type: item.application_type ?? '',
      place_of_application: item.place_of_application ?? '',
      finishing_type: item.finishing_type ?? '',
      thickness_mm: String(item.thickness_mm),
      description: item.description ?? '',
      is_active: item.is_active,
    });
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    const payload: Record<string, unknown> = {
      name: form.name,
      collection: form.collection || null,
      color: form.color || null,
      size: form.size || null,
      application_type: form.application_type || null,
      place_of_application: form.place_of_application || null,
      finishing_type: form.finishing_type || null,
      thickness_mm: parseFloat(form.thickness_mm) || 11.0,
      description: form.description || null,
      is_active: form.is_active,
    };
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  }, [form, editItem, createMutation, updateMutation]);

  const saving = createMutation.isPending || updateMutation.isPending;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = useMemo(
    () => [
      { key: 'name', header: 'Name' },
      { key: 'collection', header: 'Collection', render: (r: Recipe) => r.collection || <span className="text-gray-400">&mdash;</span> },
      { key: 'color', header: 'Color', render: (r: Recipe) => r.color || <span className="text-gray-400">&mdash;</span> },
      { key: 'size', header: 'Size', render: (r: Recipe) => r.size || <span className="text-gray-400">&mdash;</span> },
      { key: 'thickness_mm', header: 'Thickness', render: (r: Recipe) => `${r.thickness_mm} mm` },
      {
        key: 'is_active',
        header: 'Status',
        render: (r: Recipe) => <Badge status={r.is_active ? 'active' : 'inactive'} label={r.is_active ? 'Active' : 'Inactive'} />,
      },
      {
        key: 'actions',
        header: '',
        render: (r: Recipe) => (
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={() => openEdit(r)}>Edit</Button>
            <Button variant="ghost" size="sm" className="text-red-600" onClick={() => setDeleteId(r.id)}>Delete</Button>
          </div>
        ),
      },
    ],
    [openEdit],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
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

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 ? (
        <Card><p className="py-8 text-center text-gray-400">No recipes found</p></Card>
      ) : (
        <DataTable columns={columns} data={items as unknown as Record<string, unknown>[]} />
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={closeDialog} title={editItem ? 'Edit Recipe' : 'Add Recipe'} className="w-full max-w-lg">
        <div className="space-y-4">
          <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Collection" value={form.collection} onChange={(e) => setForm({ ...form, collection: e.target.value })} />
            <Input label="Color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Size" value={form.size} onChange={(e) => setForm({ ...form, size: e.target.value })} />
            <Input label="Thickness (mm)" type="number" step="0.1" value={form.thickness_mm} onChange={(e) => setForm({ ...form, thickness_mm: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Application Type" value={form.application_type} onChange={(e) => setForm({ ...form, application_type: e.target.value })} />
            <Input label="Place of Application" value={form.place_of_application} onChange={(e) => setForm({ ...form, place_of_application: e.target.value })} />
          </div>
          <Input label="Finishing Type" value={form.finishing_type} onChange={(e) => setForm({ ...form, finishing_type: e.target.value })} />
          <Input label="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
            Active
          </label>
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
