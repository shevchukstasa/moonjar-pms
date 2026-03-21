import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { kilnFiringSchedulesApi, type KilnFiringSchedule } from '@/api/kilnFiringSchedules';
import { kilnsApi } from '@/api/kilns';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/Table';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

/* ── types ──────────────────────────────────────────────────────────── */
interface Kiln {
  id: string;
  name: string;
  factory_id?: string;
  factory_name?: string;
}

interface ScheduleForm {
  kiln_id: string;
  name: string;
  schedule_data_json: string;
  is_default: boolean;
}

const emptyForm: ScheduleForm = {
  kiln_id: '',
  name: '',
  schedule_data_json: '{}',
  is_default: false,
};

/* ── main component ──────────────────────────────────────────────────── */
export default function KilnFiringSchedulesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<KilnFiringSchedule | null>(null);
  const [form, setForm] = useState<ScheduleForm>(emptyForm);
  const [mutationError, setMutationError] = useState('');
  const [filterKilnId, setFilterKilnId] = useState('');

  /* ── queries ─────────────────────────────────────────────────────── */
  const { data, isLoading } = useQuery<{ items: KilnFiringSchedule[]; total: number }>({
    queryKey: ['admin-kiln-firing-schedules'],
    queryFn: () => kilnFiringSchedulesApi.list({ per_page: 200 }),
  });

  const { data: kilnsRaw } = useQuery<{ items: Kiln[] } | Kiln[]>({
    queryKey: ['kilns-for-schedules'],
    queryFn: () => kilnsApi.list({ per_page: 200 }),
  });

  const kilns: Kiln[] = useMemo(() => {
    if (!kilnsRaw) return [];
    if (Array.isArray(kilnsRaw)) return kilnsRaw;
    return kilnsRaw.items ?? [];
  }, [kilnsRaw]);

  const kilnMap = useMemo(() => {
    const m = new Map<string, Kiln>();
    for (const k of kilns) m.set(k.id, k);
    return m;
  }, [kilns]);

  const items = useMemo(() => {
    const list = data?.items ?? [];
    if (!filterKilnId) return list;
    return list.filter((s) => s.kiln_id === filterKilnId);
  }, [data, filterKilnId]);

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
    mutationFn: (payload: { kiln_id: string; name: string; schedule_data?: Record<string, unknown>; is_default?: boolean }) =>
      kilnFiringSchedulesApi.create(payload),
    onSuccess: () => {
      setMutationError('');
      queryClient.invalidateQueries({ queryKey: ['admin-kiln-firing-schedules'] });
      closeDialog();
    },
    onError: (err: unknown) => setMutationError(extractError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<{ kiln_id: string; name: string; schedule_data: Record<string, unknown>; is_default: boolean }> }) =>
      kilnFiringSchedulesApi.update(id, payload),
    onSuccess: () => {
      setMutationError('');
      queryClient.invalidateQueries({ queryKey: ['admin-kiln-firing-schedules'] });
      closeDialog();
    },
    onError: (err: unknown) => setMutationError(extractError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => kilnFiringSchedulesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-kiln-firing-schedules'] });
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
    setForm(emptyForm);
    setDialogOpen(true);
  }, []);

  const openEdit = useCallback((item: KilnFiringSchedule) => {
    setEditItem(item);
    setForm({
      kiln_id: item.kiln_id,
      name: item.name,
      schedule_data_json: JSON.stringify(item.schedule_data, null, 2),
      is_default: item.is_default,
    });
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    setMutationError('');
    if (!form.name.trim() || !form.kiln_id) {
      setMutationError('Name and kiln are required');
      return;
    }
    let scheduleData: Record<string, unknown>;
    try {
      scheduleData = JSON.parse(form.schedule_data_json);
    } catch {
      setMutationError('Schedule data must be valid JSON');
      return;
    }
    const payload = {
      kiln_id: form.kiln_id,
      name: form.name.trim(),
      schedule_data: scheduleData,
      is_default: form.is_default,
    };
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
        { key: 'name', header: 'Name' },
        {
          key: 'kiln',
          header: 'Kiln',
          render: (r: KilnFiringSchedule) => {
            const kiln = kilnMap.get(r.kiln_id);
            return kiln ? (
              <span className="text-sm">{kiln.name}</span>
            ) : (
              <span className="text-xs text-gray-400">{r.kiln_id.slice(0, 8)}...</span>
            );
          },
        },
        {
          key: 'is_default',
          header: 'Default',
          render: (r: KilnFiringSchedule) => (
            <Badge
              status={r.is_default ? 'active' : 'inactive'}
              label={r.is_default ? 'Yes' : 'No'}
            />
          ),
        },
        {
          key: 'schedule_data',
          header: 'Schedule Data',
          render: (r: KilnFiringSchedule) => {
            const keys = Object.keys(r.schedule_data || {});
            return keys.length > 0 ? (
              <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-mono text-gray-600">
                {keys.length} {keys.length === 1 ? 'key' : 'keys'}
              </span>
            ) : (
              <span className="text-gray-400">&mdash;</span>
            );
          },
        },
        {
          key: 'created_at',
          header: 'Created',
          render: (r: KilnFiringSchedule) =>
            r.created_at ? (
              <span className="text-xs text-gray-500">
                {new Date(r.created_at).toLocaleDateString()}
              </span>
            ) : (
              <span className="text-gray-400">&mdash;</span>
            ),
        },
        {
          key: 'actions',
          header: '',
          render: (r: KilnFiringSchedule) => (
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
      [kilnMap, openEdit],
    );

  /* ── render ──────────────────────────────────────────────────────── */
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kiln Firing Schedules</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage firing schedules for kilns
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>
            Back to Admin
          </Button>
          <Button onClick={openCreate}>+ Add Schedule</Button>
        </div>
      </div>

      {/* Filter bar */}
      <Card>
        <div className="flex items-center gap-4 p-4">
          <label className="text-sm font-medium text-gray-700">Filter by Kiln:</label>
          <select
            value={filterKilnId}
            onChange={(e) => setFilterKilnId(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="">All Kilns</option>
            {kilns.map((k) => (
              <option key={k.id} value={k.id}>
                {k.name}{k.factory_name ? ` (${k.factory_name})` : ''}
              </option>
            ))}
          </select>
          <span className="text-sm text-gray-500">
            {items.length} {items.length === 1 ? 'schedule' : 'schedules'}
          </span>
        </div>
      </Card>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : items.length === 0 ? (
        <Card>
          <p className="py-8 text-center text-gray-400">No firing schedules found</p>
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
        title={editItem ? 'Edit Firing Schedule' : 'Add Firing Schedule'}
        className="w-full max-w-2xl"
      >
        <div className="space-y-4">
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. Standard Bisque 1000C"
            required
          />

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Kiln</label>
            <select
              value={form.kiln_id}
              onChange={(e) => setForm({ ...form, kiln_id: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              required
            >
              <option value="">-- Select Kiln --</option>
              {kilns.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.name}{k.factory_name ? ` (${k.factory_name})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Schedule Data (JSON)
            </label>
            <textarea
              value={form.schedule_data_json}
              onChange={(e) => setForm({ ...form, schedule_data_json: e.target.value })}
              rows={6}
              className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none"
              placeholder='{"ramp_stages": [...], "soak_time_min": 60}'
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
                className="rounded"
              />
              Default Schedule
            </label>
          </div>

          {mutationError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
              Error: {mutationError}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={!form.name || !form.kiln_id || saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="Delete Firing Schedule"
      >
        <p className="text-sm text-gray-600">
          Are you sure you want to delete this firing schedule? This action cannot be undone.
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
