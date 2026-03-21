import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { stagesApi, type ProductionStage } from '@/api/stages';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/Table';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';

/* ── types ──────────────────────────────────────────────────────────── */
interface StageForm {
  name: string;
  order: string;
}

const emptyForm: StageForm = { name: '', order: '' };

/* ── main component ──────────────────────────────────────────────────── */
export default function AdminStagesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<ProductionStage | null>(null);
  const [form, setForm] = useState<StageForm>(emptyForm);
  const [mutationError, setMutationError] = useState('');

  /* ── queries ─────────────────────────────────────────────────────── */
  const { data, isLoading } = useQuery<{ items: ProductionStage[]; total: number }>({
    queryKey: ['admin-stages'],
    queryFn: () => stagesApi.list({ per_page: 200 }),
  });

  const items = useMemo(() => {
    const list = data?.items ?? [];
    return [...list].sort((a, b) => a.order - b.order);
  }, [data]);

  /* ── mutations ───────────────────────────────────────────────────── */
  const extractError = (err: unknown): string => {
    const resp = (err as { response?: { data?: { detail?: unknown } } })?.response?.data;
    if (!resp) return String(err);
    if (typeof resp.detail === 'string') return resp.detail;
    if (Array.isArray(resp.detail))
      return resp.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('; ');
    return JSON.stringify(resp);
  };

  const createMutation = useMutation({
    mutationFn: (payload: { name: string; order: number }) => stagesApi.create(payload),
    onSuccess: () => {
      setMutationError('');
      queryClient.invalidateQueries({ queryKey: ['admin-stages'] });
      closeDialog();
    },
    onError: (err: unknown) => setMutationError(extractError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<{ name: string; order: number }> }) =>
      stagesApi.update(id, payload),
    onSuccess: () => {
      setMutationError('');
      queryClient.invalidateQueries({ queryKey: ['admin-stages'] });
      closeDialog();
    },
    onError: (err: unknown) => setMutationError(extractError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => stagesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-stages'] });
      setDeleteId(null);
    },
    onError: (err: unknown) => setMutationError(extractError(err)),
  });

  /* ── dialog helpers ──────────────────────────────────────────────── */
  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setEditItem(null);
    setForm(emptyForm);
    setMutationError('');
  }, []);

  const openCreate = useCallback(() => {
    setEditItem(null);
    // Default next order = max existing + 1
    const maxOrder = items.length > 0 ? Math.max(...items.map((i) => i.order)) : 0;
    setForm({ name: '', order: String(maxOrder + 1) });
    setDialogOpen(true);
  }, [items]);

  const openEdit = useCallback((item: ProductionStage) => {
    setEditItem(item);
    setForm({ name: item.name, order: String(item.order) });
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    setMutationError('');
    const order = parseInt(form.order, 10);
    if (!form.name.trim() || isNaN(order)) {
      setMutationError('Name and sequence number are required');
      return;
    }
    const payload = { name: form.name.trim(), order };
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  }, [form, editItem, createMutation, updateMutation]);

  const saving = createMutation.isPending || updateMutation.isPending;

  /* ── table columns ───────────────────────────────────────────────── */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] =
    useMemo(
      () => [
        {
          key: 'order',
          header: 'Sequence',
          render: (r: ProductionStage) => (
            <span className="font-mono text-sm font-bold text-gray-700">{r.order}</span>
          ),
        },
        { key: 'name', header: 'Name' },
        {
          key: 'actions',
          header: '',
          render: (r: ProductionStage) => (
            <div className="flex gap-1">
              <Button variant="ghost" size="sm" onClick={() => openEdit(r)}>
                Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-red-600"
                onClick={() => setDeleteId(r.id)}
              >
                Delete
              </Button>
            </div>
          ),
        },
      ],
      [openEdit],
    );

  /* ── render ──────────────────────────────────────────────────────── */
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Production Stages</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage production stages and their sequence order
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>
            Back to Admin
          </Button>
          <Button onClick={openCreate}>+ Add Stage</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : items.length === 0 ? (
        <Card>
          <p className="py-8 text-center text-gray-400">No production stages found</p>
        </Card>
      ) : (
        <DataTable
          columns={columns}
          data={items as unknown as Record<string, unknown>[]}
        />
      )}

      {/* ── Create / Edit Dialog ──────────────────────────────────────── */}
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        title={editItem ? 'Edit Stage' : 'Add Stage'}
      >
        <div className="space-y-4">
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. Forming, Drying, Bisque Firing..."
            required
          />
          <Input
            label="Sequence Number"
            type="number"
            value={form.order}
            onChange={(e) => setForm({ ...form, order: e.target.value })}
            placeholder="1"
            required
          />

          {mutationError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
              Error: {mutationError}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={!form.name || !form.order || saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="Delete Stage"
      >
        <p className="text-sm text-gray-600">
          Are you sure you want to delete this production stage? This action cannot be undone.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteId && deleteMutation.mutate(deleteId)}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
