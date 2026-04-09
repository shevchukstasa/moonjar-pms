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

interface Typology {
  id: string;
  name: string;
  factory_id?: string | null;
  factory_name?: string | null;
  product_types?: string[];
  min_size_cm?: number | null;
  max_size_cm?: number | null;
}

/** One interval in the heating or cooling curve */
interface TempStage {
  start_temp: number;
  end_temp: number;
  rate: number; // °C/h
}

interface ProfileForm {
  name: string;
  temperature_group_id: string;
  typology_id: string;
  total_duration_hours: string;
  is_active: boolean;
  heating_stages: TempStage[];
  cooling_stages: TempStage[];
}

const emptyForm: ProfileForm = {
  name: '',
  temperature_group_id: '',
  typology_id: '',
  total_duration_hours: '',
  is_active: true,
  heating_stages: [{ start_temp: 20, end_temp: 1000, rate: 100 }],
  cooling_stages: [{ start_temp: 1000, end_temp: 20, rate: 50 }],
};

/** Parse stages from backend JSONB into heating/cooling arrays */
function parseStages(stages: unknown[]): { heating: TempStage[]; cooling: TempStage[] } {
  const heating: TempStage[] = [];
  const cooling: TempStage[] = [];
  if (!Array.isArray(stages) || stages.length === 0) {
    return { heating: [], cooling: [] };
  }
  for (const s of stages) {
    const st = s as { type?: string; start_temp?: number; end_temp?: number; rate?: number };
    const stage: TempStage = {
      start_temp: st.start_temp ?? 0,
      end_temp: st.end_temp ?? 0,
      rate: st.rate ?? 0,
    };
    if (st.type === 'cooling') {
      cooling.push(stage);
    } else {
      heating.push(stage);
    }
  }
  return { heating, cooling };
}

/** Convert heating/cooling arrays to backend JSONB format */
function toStagesJson(heating: TempStage[], cooling: TempStage[]): object[] {
  const result: object[] = [];
  for (const s of heating) {
    result.push({ type: 'heating', start_temp: s.start_temp, end_temp: s.end_temp, rate: s.rate });
  }
  for (const s of cooling) {
    result.push({ type: 'cooling', start_temp: s.start_temp, end_temp: s.end_temp, rate: s.rate });
  }
  return result;
}

/** Calculate max temp from stages */
function calcMaxTemp(heating: TempStage[], cooling: TempStage[]): number {
  let max = 0;
  for (const s of [...heating, ...cooling]) {
    max = Math.max(max, s.start_temp, s.end_temp);
  }
  return max;
}

/** Calculate total duration from stages (hours) */
function calcTotalDuration(heating: TempStage[], cooling: TempStage[]): number {
  let total = 0;
  for (const s of [...heating, ...cooling]) {
    if (s.rate > 0) {
      total += Math.abs(s.end_temp - s.start_temp) / s.rate;
    }
  }
  return Math.round(total * 10) / 10; // round to 1 decimal
}

/* ── StageEditor sub-component ─────────────────────────────────────── */
function StageEditor({
  label,
  stages,
  onChange,
  color,
}: {
  label: string;
  stages: TempStage[];
  onChange: (stages: TempStage[]) => void;
  color: 'red' | 'blue';
}) {
  const borderColor = color === 'red' ? 'border-red-200' : 'border-blue-200';
  const bgColor = color === 'red' ? 'bg-red-50' : 'bg-blue-50';
  const textColor = color === 'red' ? 'text-red-700' : 'text-blue-700';
  const arrowIcon = color === 'red' ? '↑' : '↓';

  const updateStage = (idx: number, field: keyof TempStage, value: number) => {
    const next = [...stages];
    next[idx] = { ...next[idx], [field]: value };
    // Auto-chain: if end_temp changed and there's a next stage, update its start_temp
    if (field === 'end_temp' && idx < next.length - 1) {
      next[idx + 1] = { ...next[idx + 1], start_temp: value };
    }
    // Auto-chain: if start_temp changed and there's a prev stage, this is manual override
    onChange(next);
  };

  const addStage = () => {
    const lastEnd = stages.length > 0 ? stages[stages.length - 1].end_temp : (color === 'red' ? 20 : 1000);
    const newEnd = color === 'red' ? lastEnd + 200 : Math.max(lastEnd - 200, 20);
    onChange([...stages, { start_temp: lastEnd, end_temp: newEnd, rate: color === 'red' ? 100 : 50 }]);
  };

  const removeStage = (idx: number) => {
    const next = stages.filter((_, i) => i !== idx);
    // Re-chain start temps
    for (let i = 1; i < next.length; i++) {
      next[i] = { ...next[i], start_temp: next[i - 1].end_temp };
    }
    onChange(next);
  };

  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} p-3`}>
      <div className="mb-2 flex items-center justify-between">
        <h4 className={`text-sm font-semibold ${textColor}`}>
          {arrowIcon} {label} ({stages.length} {stages.length === 1 ? 'interval' : 'intervals'})
        </h4>
        <button
          type="button"
          onClick={addStage}
          className={`rounded px-2 py-0.5 text-xs font-medium ${textColor} hover:bg-white/50`}
        >
          + Add Interval
        </button>
      </div>

      {stages.length === 0 && (
        <p className="py-2 text-center text-xs text-gray-400">No intervals defined</p>
      )}

      {stages.map((stage, idx) => (
        <div key={idx} className="mb-2 flex items-center gap-2">
          <div className="flex items-center gap-1">
            <input
              type="number"
              value={stage.start_temp}
              onChange={(e) => updateStage(idx, 'start_temp', parseFloat(e.target.value) || 0)}
              disabled={idx > 0} // auto-chained from previous
              className={`w-20 rounded border px-2 py-1 text-center text-sm font-mono ${
                idx > 0 ? 'bg-gray-100 text-gray-500' : 'bg-white'
              }`}
              title="Start °C"
            />
            <span className="text-gray-400">→</span>
            <input
              type="number"
              value={stage.end_temp}
              onChange={(e) => updateStage(idx, 'end_temp', parseFloat(e.target.value) || 0)}
              className="w-20 rounded border bg-white px-2 py-1 text-center text-sm font-mono"
              title="End °C"
            />
            <span className="text-xs text-gray-400">°C</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">@</span>
            <input
              type="number"
              value={stage.rate}
              onChange={(e) => updateStage(idx, 'rate', parseFloat(e.target.value) || 0)}
              className="w-20 rounded border bg-white px-2 py-1 text-center text-sm font-mono"
              title="Rate °C/h"
            />
            <span className="text-xs text-gray-400">°C/h</span>
          </div>
          {/* Calculated duration */}
          <span className="ml-1 text-xs text-gray-400">
            {stage.rate > 0
              ? `≈${(Math.abs(stage.end_temp - stage.start_temp) / stage.rate).toFixed(1)}h`
              : ''}
          </span>
          {stages.length > 1 && (
            <button
              type="button"
              onClick={() => removeStage(idx)}
              className="ml-auto text-sm text-red-400 hover:text-red-600"
              title="Remove interval"
            >
              ✕
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

/* ── main component ──────────────────────────────────────────────────── */
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

  const { data: tempGroupsRaw } = useQuery<TemperatureGroup[]>({
    queryKey: ['temperature-groups'],
    queryFn: () => apiClient.get('/reference/temperature-groups').then((r) => {
      const d = r.data;
      return Array.isArray(d) ? d : (d?.items ?? []);
    }),
  });

  const { data: typologiesRaw } = useQuery<Typology[]>({
    queryKey: ['tps-typologies-all'],
    queryFn: () => apiClient.get('/tps/typologies').then((r) => r.data?.items ?? []),
  });

  const items = data?.items ?? [];
  const tempGroups = tempGroupsRaw ?? [];
  const typologies = typologiesRaw ?? [];

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
    mutationFn: (payload: Record<string, unknown>) =>
      firingProfilesApi.create(
        payload as unknown as Parameters<typeof firingProfilesApi.create>[0],
      ),
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
    const { heating, cooling } = parseStages((item as unknown as Record<string, unknown>).stages as unknown[] ?? []);
    setEditItem(item);
    setForm({
      name: item.name,
      temperature_group_id: item.temperature_group_id ?? '',
      typology_id: item.typology_id ?? '',
      total_duration_hours:
        item.total_duration_hours != null ? String(item.total_duration_hours) : '',
      is_active: item.is_active,
      heating_stages: heating.length > 0 ? heating : [{ start_temp: 20, end_temp: item.target_temperature ?? 1000, rate: 100 }],
      cooling_stages: cooling.length > 0 ? cooling : [{ start_temp: item.target_temperature ?? 1000, end_temp: 20, rate: 50 }],
    });
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    setMutationError('');
    const maxTemp = calcMaxTemp(form.heating_stages, form.cooling_stages);
    const stages = toStagesJson(form.heating_stages, form.cooling_stages);
    const calculatedDuration = calcTotalDuration(form.heating_stages, form.cooling_stages);
    const hasStages = form.heating_stages.some(s => s.rate > 0) || form.cooling_stages.some(s => s.rate > 0);
    const effectiveDuration = hasStages && calculatedDuration > 0
      ? calculatedDuration
      : (form.total_duration_hours ? parseFloat(form.total_duration_hours) : null);
    const payload: Record<string, unknown> = {
      name: form.name,
      temperature_group_id: form.temperature_group_id || null,
      typology_id: form.typology_id || null,
      target_temperature: maxTemp || null,
      total_duration_hours: effectiveDuration,
      stages,
      is_active: form.is_active,
    };
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  }, [form, editItem, createMutation, updateMutation]);

  const saving = createMutation.isPending || updateMutation.isPending;

  /* ── helper: format stages summary for table ──────────────────────── */
  const formatStagesSummary = (item: FiringProfile) => {
    const raw = (item as unknown as Record<string, unknown>).stages as unknown[];
    if (!Array.isArray(raw) || raw.length === 0) return null;
    const { heating, cooling } = parseStages(raw);
    const parts: string[] = [];
    if (heating.length > 0) parts.push(`${heating.length} heat`);
    if (cooling.length > 0) parts.push(`${cooling.length} cool`);
    return parts.join(' + ');
  };

  /* ── table columns ───────────────────────────────────────────────── */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] =
    useMemo(
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
          key: 'typology',
          header: 'Typology',
          render: (r: FiringProfile) =>
            r.typology_name ? (
              <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                {r.typology_name}
              </span>
            ) : (
              <span className="text-gray-400">&mdash;</span>
            ),
        },
        {
          key: 'target_temperature',
          header: 'Max Temp (°C)',
          render: (r: FiringProfile) =>
            r.target_temperature != null ? (
              <span className="font-mono text-sm font-bold text-red-600">
                {r.target_temperature}°C
              </span>
            ) : (
              <span className="text-gray-400">&mdash;</span>
            ),
        },
        {
          key: 'total_duration_hours',
          header: 'Duration (h)',
          render: (r: FiringProfile) =>
            r.total_duration_hours != null ? (
              <span className="font-mono text-sm font-bold">{r.total_duration_hours}h</span>
            ) : (
              <span className="text-gray-400">&mdash;</span>
            ),
        },
        {
          key: 'stages',
          header: 'Curve',
          render: (r: FiringProfile) => {
            const summary = formatStagesSummary(r);
            return summary ? (
              <span className="rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
                {summary}
              </span>
            ) : (
              <span className="text-gray-400">&mdash;</span>
            );
          },
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
        className="w-full max-w-2xl"
      >
        <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />

          <div className="grid grid-cols-2 gap-4">
            {/* Temperature Group selector */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Temperature Group
              </label>
              <select
                value={form.temperature_group_id}
                onChange={(e) =>
                  setForm({ ...form, temperature_group_id: e.target.value })
                }
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
              <p className="mt-0.5 text-xs text-gray-400">
                Sets the apex temperature (Layer 1)
              </p>
            </div>
            {/* Typology selector */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Typology
              </label>
              <select
                value={form.typology_id}
                onChange={(e) =>
                  setForm({ ...form, typology_id: e.target.value })
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                <option value="">-- Any typology --</option>
                {typologies.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                    {t.factory_name ? ` · ${t.factory_name}` : ''}
                  </option>
                ))}
              </select>
              <p className="mt-0.5 text-xs text-gray-400">
                Drives ramp/hold/cool rates (Layer 3)
              </p>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Total Duration (hours)
              </label>
              {(() => {
                const calculated = calcTotalDuration(form.heating_stages, form.cooling_stages);
                const manual = form.total_duration_hours ? parseFloat(form.total_duration_hours) : 0;
                const hasStages = form.heating_stages.some(s => s.rate > 0) || form.cooling_stages.some(s => s.rate > 0);
                const effectiveDuration = hasStages && calculated > 0 ? calculated : manual;
                return (
                  <>
                    <input
                      type="number"
                      step="0.5"
                      placeholder="auto from stages"
                      value={hasStages && calculated > 0 ? calculated : form.total_duration_hours}
                      onChange={(e) => setForm({ ...form, total_duration_hours: e.target.value })}
                      readOnly={hasStages && calculated > 0}
                      className={`w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none ${
                        hasStages && calculated > 0 ? 'bg-gray-50 text-gray-600' : 'bg-white'
                      }`}
                    />
                    {hasStages && calculated > 0 && (
                      <p className="mt-0.5 text-xs text-blue-500">
                        ≈{effectiveDuration}h calculated from {form.heating_stages.length + form.cooling_stages.length} intervals
                      </p>
                    )}
                  </>
                );
              })()}
            </div>
          </div>

          {/* Heating intervals */}
          <StageEditor
            label="Heating Intervals"
            stages={form.heating_stages}
            onChange={(s) => setForm({ ...form, heating_stages: s })}
            color="red"
          />

          {/* Cooling intervals */}
          <StageEditor
            label="Cooling Intervals"
            stages={form.cooling_stages}
            onChange={(s) => setForm({ ...form, cooling_stages: s })}
            color="blue"
          />

          {/* Summary */}
          <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
            <div className="flex items-center gap-4 text-sm">
              <span className="text-gray-500">
                Max temp:{' '}
                <strong className="text-red-600">
                  {calcMaxTemp(form.heating_stages, form.cooling_stages)}°C
                </strong>
              </span>
              <span className="text-gray-500">
                Heating intervals: <strong>{form.heating_stages.length}</strong>
              </span>
              <span className="text-gray-500">
                Cooling intervals: <strong>{form.cooling_stages.length}</strong>
              </span>
              <span className="text-gray-500">
                Total: <strong className="text-blue-600">≈{calcTotalDuration(form.heating_stages, form.cooling_stages)}h</strong>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
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
          Are you sure you want to delete this firing profile? This action cannot be
          undone.
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
