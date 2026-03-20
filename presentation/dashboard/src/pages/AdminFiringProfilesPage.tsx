import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { firingProfilesApi, type FiringProfile } from '@/api/firingProfiles';
import apiClient from '@/api/client';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/Table';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

/* ── types ──────────────────────────────────────────────────────────── */
interface TemperatureGroup {
  id: string;
  name: string;
  temperature: number;
  is_active: boolean;
}

interface ProfileForm {
  name: string;
  temperature_group_id: string;
  target_temperature: string;
  total_duration_hours: string;
  ramp_rate: string;
  cooling_type: string;
  is_active: boolean;
}

const COOLING_TYPE_OPTIONS = [
  { value: '', label: '-- None --' },
  { value: 'natural', label: 'Natural' },
  { value: 'forced', label: 'Forced' },
  { value: 'controlled', label: 'Controlled' },
];

const emptyForm: ProfileForm = {
  name: '',
  temperature_group_id: '',
  target_temperature: '',
  total_duration_hours: '',
  ramp_rate: '',
  cooling_type: '',
  is_active: true,
};

/* ── component ──────────────────────────────────────────────────────── */
export default function AdminFiringProfilesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<FiringProfile | null>(null);
  const [form, setForm] = useState<ProfileForm>(emptyForm);
  const [mutationError, setMutationError] = useState('');

  /* ── queries ─────────────────────────────────────────────────────── */
  const { data, isLoading } = useQuery<{ items: FiringProfile[]; total: number }>({
    queryKey: ['admin-firing-profiles'],
    queryFn: () => firingProfilesApi.list(),
  });

  const { data: tempGroupsData } = useQuery<{ items: TemperatureGroup[] }>({
    queryKey: ['temperature-groups'],
    queryFn: () => apiClient.get('/reference/temperature-groups').then((r) => r.data),
  });

  const items = data?.items ?? [];
  const tempGroups = tempGroupsData?.items ?? [];

  /* ── mutations ───────────────────────────────────────────────────── */
  const extractError = (err: unknown): string => {
    const resp = (err as { response?: { data?: { detail?: unknown } } })?.response?.data;
    if (!resp) return String(err);
    if (typeof resp.detail === 'string') return resp.detail;
    if (Array.isArray(resp.detail)) return resp.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('; ');
    return JSON.stringify(resp);
  };

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => firingProfilesApi.create(payload as unknown as Parameters<typeof firingProfilesApi.create>[0]),
    onSuccess: () => {
      setMutationError('');
      queryClient.invalidateQueries({ queryKey: ['admin-firing-profiles'] });
      closeDialog();
    },
    onError: (err: unknown) => setMutationError(extractError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      firingProfilesApi.update(id, payload),
    onSuccess: () => {
      setMutationError('');
      queryClient.invalidateQueries({ queryKey: ['admin-firing-profiles'] });
      closeDialog();
    },
    onError: (err: unknown) => setMutationError(extractError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => firingProfilesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-firing-profiles'] });
      setDeleteId(null);
    },
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

  const openEdit = useCallback((item: FiringProfile) => {
    setEditItem(item);
    setForm({
      name: item.name,
      temperature_group_id: item.temperature_group_id ?? '',
      target_temperature: item.target_temperature != null ? String(item.target_temperature) : '',
      total_duration_hours: item.total_duration_hours != null ? String(item.total_duration_hours) : '',
      ramp_rate: item.ramp_rate != null ? String(item.ramp_rate) : '',
      cooling_type: item.cooling_type ?? '',
      is_active: item.is_active,
    });
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    setMutationError('');
    const payload: Record<string, unknown> = {
      name: form.name,
      temperature_group_id: form.temperature_group_id || null,
      target_temperature: form.target_temperature ? parseInt(form.target_temperature) : null,
      total_duration_hours: form.total_duration_hours ? parseFloat(form.total_duration_hours) : null,
      ramp_rate: form.ramp_rate ? parseFloat(form.ramp_rate) : null,
      cooling_type: form.cooling_type || null,
      is_active: form.is_active,
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
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = useMemo(
    () => [
      { key: 'name', header: 'Name' },
      {
        key: 'temperature_group',
        header: 'Temp Group',
        render: (r: FiringProfile) =>
          r.temperature_group_name ? (
            <Badge status="active" label={r.temperature_group_name} />
          ) : (
            <span className="text-gray-400">&mdash;</span>
          ),
      },
      {
        key: 'target_temperature',
        header: 'Max Temp (\u00B0C)',
        render: (r: FiringProfile) =>
          r.target_temperature != null ? (
            <span className="font-mono text-sm">{r.target_temperature}</span>
          ) : (
            <span className="text-gray-400">&mdash;</span>
          ),
      },
      {
        key: 'total_duration_hours',
        header: 'Duration (h)',
        render: (r: FiringProfile) =>
          r.total_duration_hours != null ? (
            <span className="font-mono text-sm font-bold">{r.total_duration_hours}</span>
          ) : (
            <span className="text-gray-400">&mdash;</span>
          ),
      },
      {
        key: 'ramp_rate',
        header: 'Ramp Rate',
        render: (r: FiringProfile) =>
          r.ramp_rate != null ? (
            <span className="font-mono text-sm">{r.ramp_rate}</span>
          ) : (
            <span className="text-gray-400">&mdash;</span>
          ),
      },
      {
        key: 'cooling_type',
        header: 'Cooling',
        render: (r: FiringProfile) =>
          r.cooling_type ? (
            <span className="text-sm capitalize">{r.cooling_type}</span>
          ) : (
            <span className="text-gray-400">&mdash;</span>
          ),
      },
      {
        key: 'is_active',
        header: 'Status',
        render: (r: FiringProfile) => (
          <Badge
            status={r.is_active ? 'active' : 'inactive'}
            label={r.is_active ? 'Active' : 'Inactive'}
          />
        ),
      },
      {
        key: 'actions',
        header: '',
        render: (r: FiringProfile) => (
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
          <h1 className="text-2xl font-bold text-gray-900">Firing Profiles</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage kiln firing profiles and temperature curves
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>
            Back to Admin
          </Button>
          <Button onClick={openCreate}>+ Add Profile</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : items.length === 0 ? (
        <Card>
          <p className="py-8 text-center text-gray-400">No firing profiles found</p>
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
        title={editItem ? 'Edit Firing Profile' : 'Add Firing Profile'}
        className="w-full max-w-lg"
      >
        <div className="space-y-4">
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />

          {/* Temperature Group selector */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Temperature Group
            </label>
            <select
              value={form.temperature_group_id}
              onChange={(e) => setForm({ ...form, temperature_group_id: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">-- Not assigned --</option>
              {tempGroups
                .filter((g) => g.is_active)
                .map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name} ({g.temperature}&deg;C)
                  </option>
                ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Max Temperature (\u00B0C)"
              type="number"
              step="1"
              placeholder="e.g. 1012"
              value={form.target_temperature}
              onChange={(e) =>
                setForm({ ...form, target_temperature: e.target.value })
              }
            />
            <Input
              label="Total Duration (hours)"
              type="number"
              step="0.5"
              placeholder="e.g. 24"
              value={form.total_duration_hours}
              onChange={(e) =>
                setForm({ ...form, total_duration_hours: e.target.value })
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Ramp Rate (\u00B0C/h)"
              type="number"
              step="0.1"
              placeholder="e.g. 50"
              value={form.ramp_rate}
              onChange={(e) => setForm({ ...form, ramp_rate: e.target.value })}
            />
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Cooling Type
              </label>
              <select
                value={form.cooling_type}
                onChange={(e) =>
                  setForm({ ...form, cooling_type: e.target.value })
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                {COOLING_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) =>
                  setForm({ ...form, is_active: e.target.checked })
                }
                className="rounded"
              />
              Active
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
            <Button onClick={handleSubmit} disabled={!form.name || saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="Delete Firing Profile"
      >
        <p className="text-sm text-gray-600">
          Are you sure you want to delete this firing profile? This action
          cannot be undone.
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
