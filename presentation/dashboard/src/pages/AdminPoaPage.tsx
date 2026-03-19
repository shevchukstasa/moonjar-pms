import { formatDate } from "@/lib/format";
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

interface PoaItem {
  id: string;
  code: string;
  name: string;
  created_at: string;
}

interface PoaForm {
  code: string;
  name: string;
}

const emptyForm: PoaForm = { code: '', name: '' };
const API = '/reference/places-of-application';

export default function AdminPoaPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<PoaItem | null>(null);
  const [form, setForm] = useState<PoaForm>(emptyForm);
  const [csvOpen, setCsvOpen] = useState(false);

  const { data, isLoading } = useQuery<PoaItem[]>({
    queryKey: ['ref-places-of-application'],
    queryFn: () => apiClient.get(API).then((r) => r.data),
  });

  const items = data ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: PoaForm) => apiClient.post(API, payload).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-places-of-application'] }); closeDialog(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: PoaForm }) => apiClient.put(`${API}/${id}`, payload).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-places-of-application'] }); closeDialog(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`${API}/${id}`).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-places-of-application'] }); setDeleteId(null); },
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

  const openEdit = useCallback((item: PoaItem) => {
    setEditItem(item);
    setForm({ code: item.code, name: item.name });
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, payload: form });
    } else {
      createMutation.mutate(form);
    }
  }, [form, editItem, createMutation, updateMutation]);

  const saving = createMutation.isPending || updateMutation.isPending;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = useMemo(
    () => [
      { key: 'code', header: 'Code' },
      { key: 'name', header: 'Name' },
      {
        key: 'created_at',
        header: 'Created',
        render: (item: PoaItem) => formatDate(item.created_at),
      },
      {
        key: 'actions',
        header: '',
        render: (item: PoaItem) => (
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={() => openEdit(item)}>Edit</Button>
            <Button variant="ghost" size="sm" className="text-red-600" onClick={() => setDeleteId(item.id)}>Delete</Button>
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
          <h1 className="text-2xl font-bold text-gray-900">Places of Application</h1>
          <p className="mt-1 text-sm text-gray-500">Manage application placement options (face only, edges, all edges, with back, etc.)</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>Back to Admin</Button>
          <Button variant="secondary" onClick={() => setCsvOpen(true)}>Import CSV</Button>
          <Button onClick={openCreate}>+ Add Place</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 ? (
        <Card><p className="py-8 text-center text-gray-400">No places of application found</p></Card>
      ) : (
        <DataTable columns={columns} data={items as unknown as Record<string, unknown>[]} />
      )}

      <Dialog open={dialogOpen} onClose={closeDialog} title={editItem ? 'Edit Place of Application' : 'Add Place of Application'} className="w-full max-w-sm">
        <div className="space-y-4">
          <Input label="Code" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="e.g. face_only, edges_1" required />
          <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={!form.code || !form.name || saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      <CsvImportDialog open={csvOpen} onClose={() => setCsvOpen(false)} {...CSV_CONFIGS.places_of_application} onSuccess={() => queryClient.invalidateQueries({ queryKey: ['ref-places-of-application'] })} />

      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Place of Application">
        <p className="text-sm text-gray-600">Are you sure you want to delete this place of application? This action cannot be undone.</p>
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
