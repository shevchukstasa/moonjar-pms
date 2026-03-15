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

interface ColorItem {
  id: string;
  name: string;
  code: string | null;
  is_basic: boolean;
  created_at: string;
}

interface ColorForm {
  name: string;
  code: string;
  is_basic: boolean;
}

const emptyForm: ColorForm = { name: '', code: '', is_basic: false };
const API = '/reference/colors';

export default function AdminColorsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<ColorItem | null>(null);
  const [form, setForm] = useState<ColorForm>(emptyForm);
  const [csvOpen, setCsvOpen] = useState(false);

  const { data, isLoading } = useQuery<ColorItem[]>({
    queryKey: ['ref-colors'],
    queryFn: () => apiClient.get(API).then((r) => r.data),
  });

  const items = data ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => apiClient.post(API, payload).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-colors'] }); closeDialog(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => apiClient.put(`${API}/${id}`, payload).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-colors'] }); closeDialog(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`${API}/${id}`).then((r) => r.data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ref-colors'] }); setDeleteId(null); },
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

  const openEdit = useCallback((item: ColorItem) => {
    setEditItem(item);
    setForm({ name: item.name, code: item.code ?? '', is_basic: item.is_basic });
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    const payload: Record<string, unknown> = {
      name: form.name,
      code: form.code || null,
      is_basic: form.is_basic,
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
      { key: 'code', header: 'Code', render: (c: ColorItem) => c.code || <span className="text-gray-400">&mdash;</span> },
      {
        key: 'is_basic',
        header: 'Basic',
        render: (c: ColorItem) => c.is_basic ? <Badge status="active" label="Basic" /> : <span className="text-gray-400">No</span>,
      },
      {
        key: 'created_at',
        header: 'Created',
        render: (c: ColorItem) => new Date(c.created_at).toLocaleDateString(),
      },
      {
        key: 'actions',
        header: '',
        render: (c: ColorItem) => (
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
          <h1 className="text-2xl font-bold text-gray-900">Colors</h1>
          <p className="mt-1 text-sm text-gray-500">Manage product colors and base color flags</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>Back to Admin</Button>
          <Button variant="secondary" onClick={() => setCsvOpen(true)}>Import CSV</Button>
          <Button onClick={openCreate}>+ Add Color</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 ? (
        <Card><p className="py-8 text-center text-gray-400">No colors found</p></Card>
      ) : (
        <DataTable columns={columns} data={items as unknown as Record<string, unknown>[]} />
      )}

      <Dialog open={dialogOpen} onClose={closeDialog} title={editItem ? 'Edit Color' : 'Add Color'} className="w-full max-w-sm">
        <div className="space-y-4">
          <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <Input label="Code" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="e.g. #FF5500" />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_basic} onChange={(e) => setForm({ ...form, is_basic: e.target.checked })} className="rounded" />
            Basic color (used for surplus routing)
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={!form.name || saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      <CsvImportDialog open={csvOpen} onClose={() => setCsvOpen(false)} {...CSV_CONFIGS.colors} onSuccess={() => queryClient.invalidateQueries({ queryKey: ['ref-colors'] })} />

      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Color">
        <p className="text-sm text-gray-600">Are you sure you want to delete this color? This action cannot be undone.</p>
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
