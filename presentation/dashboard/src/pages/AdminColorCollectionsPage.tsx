import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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

interface ColorCollectionItem {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

interface FormData {
  name: string;
  description: string;
}

const API = '/reference/color-collections';

export default function AdminColorCollectionsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<ColorCollectionItem | null>(null);
  const [form, setForm] = useState<FormData>({ name: '', description: '' });
  const [csvOpen, setCsvOpen] = useState(false);

  const { data, isLoading } = useQuery<ColorCollectionItem[]>({
    queryKey: ['ref-color-collections'],
    queryFn: () => apiClient.get(API, { params: { include_inactive: true } }).then((r) => r.data),
  });

  const items = data ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: FormData) => apiClient.post(API, payload).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-color-collections'] }); closeDialog(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<FormData> & { is_active?: boolean } }) =>
      apiClient.put(`${API}/${id}`, payload).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-color-collections'] }); closeDialog(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`${API}/${id}`).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-color-collections'] }); setDeleteId(null); },
  });

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setEditItem(null);
    setForm({ name: '', description: '' });
  }, []);

  const openCreate = useCallback(() => {
    setEditItem(null);
    setForm({ name: '', description: '' });
    setDialogOpen(true);
  }, []);

  const openEdit = useCallback((item: ColorCollectionItem) => {
    setEditItem(item);
    setForm({ name: item.name, description: item.description || '' });
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    const payload = { name: form.name, description: form.description || undefined };
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, payload });
    } else {
      createMutation.mutate(payload as FormData);
    }
  }, [form, editItem, createMutation, updateMutation]);

  const toggleActive = useCallback((item: ColorCollectionItem) => {
    updateMutation.mutate({ id: item.id, payload: { is_active: !item.is_active } });
  }, [updateMutation]);

  const saving = createMutation.isPending || updateMutation.isPending;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = useMemo(
    () => [
      { key: 'name', header: 'Name' },
      {
        key: 'description',
        header: 'Description',
        render: (c: ColorCollectionItem) => c.description || <span className="text-gray-400">&mdash;</span>,
      },
      {
        key: 'is_active',
        header: 'Status',
        render: (c: ColorCollectionItem) =>
          c.is_active ? <Badge status="active" label="Active" /> : <Badge status="inactive" label="Inactive" />,
      },
      {
        key: 'created_at',
        header: 'Created',
        render: (c: ColorCollectionItem) => new Date(c.created_at).toLocaleDateString(),
      },
      {
        key: 'actions',
        header: '',
        render: (c: ColorCollectionItem) => (
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={() => openEdit(c)}>Edit</Button>
            <Button
              variant="ghost"
              size="sm"
              className={c.is_active ? 'text-orange-600' : 'text-green-600'}
              onClick={() => toggleActive(c)}
            >
              {c.is_active ? 'Deactivate' : 'Activate'}
            </Button>
            <Button variant="ghost" size="sm" className="text-red-600" onClick={() => setDeleteId(c.id)}>Delete</Button>
          </div>
        ),
      },
    ],
    [openEdit, toggleActive],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Color Collections</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage color collections for glaze recipes (separate from product collections)
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>Back to Admin</Button>
          <Button variant="secondary" onClick={() => setCsvOpen(true)}>Import CSV</Button>
          <Button onClick={openCreate}>+ Add Color Collection</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 ? (
        <Card><p className="py-8 text-center text-gray-400">No color collections found</p></Card>
      ) : (
        <DataTable columns={columns} data={items as unknown as Record<string, unknown>[]} />
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onClose={closeDialog} title={editItem ? 'Edit Color Collection' : 'Add Color Collection'} className="w-full max-w-sm">
        <div className="space-y-4">
          <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Season 2025/2026" required />
          <Input label="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional description" />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={!form.name || saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      <CsvImportDialog open={csvOpen} onClose={() => setCsvOpen(false)} {...CSV_CONFIGS.color_collections} onSuccess={() => queryClient.invalidateQueries({ queryKey: ['ref-color-collections'] })} />

      {/* Delete Confirmation */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Color Collection">
        <p className="text-sm text-gray-600">
          Are you sure you want to delete this color collection? Recipes that reference it will keep
          their text value but won't be linked to this collection anymore.
        </p>
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
