import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/Table';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';
import { CsvImportDialog } from '@/components/admin/CsvImportDialog';
import { CSV_CONFIGS } from '@/config/csvImportConfigs';

interface CollectionItem {
  id: string;
  name: string;
  created_at: string;
}

const API = '/reference/collections';

export default function AdminCollectionsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<CollectionItem | null>(null);
  const [name, setName] = useState('');
  const [csvOpen, setCsvOpen] = useState(false);

  const { data, isLoading } = useQuery<CollectionItem[]>({
    queryKey: ['ref-collections'],
    queryFn: () => apiClient.get(API).then((r) => r.data),
  });

  const items = data ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: { name: string }) => apiClient.post(API, payload).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-collections'] }); closeDialog(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { name: string } }) => apiClient.put(`${API}/${id}`, payload).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-collections'] }); closeDialog(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`${API}/${id}`).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-collections'] }); setDeleteId(null); },
  });

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setEditItem(null);
    setName('');
  }, []);

  const openCreate = useCallback(() => {
    setEditItem(null);
    setName('');
    setDialogOpen(true);
  }, []);

  const openEdit = useCallback((item: CollectionItem) => {
    setEditItem(item);
    setName(item.name);
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, payload: { name } });
    } else {
      createMutation.mutate({ name });
    }
  }, [name, editItem, createMutation, updateMutation]);

  const saving = createMutation.isPending || updateMutation.isPending;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = useMemo(
    () => [
      { key: 'name', header: 'Name' },
      {
        key: 'created_at',
        header: 'Created',
        render: (c: CollectionItem) => new Date(c.created_at).toLocaleDateString(),
      },
      {
        key: 'actions',
        header: '',
        render: (c: CollectionItem) => (
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={() => openEdit(c)}>Edit</Button>
            <Button variant="ghost" size="sm" className="text-red-600" onClick={() => setDeleteId(c.id)}>Delete</Button>
          </div>
        ),
      },
    ],
    [openEdit],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Collections</h1>
          <p className="mt-1 text-sm text-gray-500">Manage product collections</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>Back to Admin</Button>
          <Button variant="secondary" onClick={() => setCsvOpen(true)}>Import CSV</Button>
          <Button onClick={openCreate}>+ Add Collection</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 ? (
        <Card><p className="py-8 text-center text-gray-400">No collections found</p></Card>
      ) : (
        <DataTable columns={columns} data={items as unknown as Record<string, unknown>[]} />
      )}

      <Dialog open={dialogOpen} onClose={closeDialog} title={editItem ? 'Edit Collection' : 'Add Collection'} className="w-full max-w-sm">
        <div className="space-y-4">
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} required />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={!name || saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      <CsvImportDialog open={csvOpen} onClose={() => setCsvOpen(false)} {...CSV_CONFIGS.collections} onSuccess={() => queryClient.invalidateQueries({ queryKey: ['ref-collections'] })} />

      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Collection">
        <p className="text-sm text-gray-600">Are you sure you want to delete this collection? This action cannot be undone.</p>
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
