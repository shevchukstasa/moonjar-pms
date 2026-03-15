import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import apiClient from '@/api/client';
import { Thermometer, Plus, Pencil, Trash2, X, Save } from 'lucide-react';

const THERMOCOUPLE_OPTIONS = [
  { value: '', label: '-- Select --' },
  { value: 'chinese', label: 'Chinese' },
  { value: 'indonesia_manufacture', label: 'Indonesia Manufacture' },
] as const;

const CONTROL_CABLE_OPTIONS = [
  { value: '', label: '-- Select --' },
  { value: 'indonesia_manufacture', label: 'Indonesia Manufacture' },
] as const;

const CONTROL_DEVICE_OPTIONS = [
  { value: '', label: '-- Select --' },
  { value: 'oven', label: 'OVEN' },
  { value: 'self_made', label: 'Self Made' },
] as const;

interface RecipeLink {
  id: string;
  recipe_id: string;
  recipe_name: string | null;
  recipe_collection: string | null;
  is_default: boolean;
}

interface TemperatureGroup {
  id: string;
  name: string;
  min_temperature: number;
  max_temperature: number;
  description: string | null;
  thermocouple: string | null;
  control_cable: string | null;
  control_device: string | null;
  is_active: boolean;
  display_order: number;
  recipes: RecipeLink[];
  created_at: string | null;
  updated_at: string | null;
}

interface FormData {
  name: string;
  min_temperature: number;
  max_temperature: number;
  description: string;
  thermocouple: string;
  control_cable: string;
  control_device: string;
  display_order: number;
}

const emptyForm: FormData = {
  name: '',
  min_temperature: 800,
  max_temperature: 1050,
  description: '',
  thermocouple: '',
  control_cable: '',
  control_device: '',
  display_order: 0,
};

function labelFor(value: string | null, options: readonly { value: string; label: string }[]): string {
  if (!value) return '-';
  return options.find((o) => o.value === value)?.label || value;
}

export default function AdminTemperatureGroupsPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<string | null>(null); // group id or 'new'
  const [form, setForm] = useState<FormData>(emptyForm);
  const [error, setError] = useState('');

  const { data: groups, isLoading } = useQuery<TemperatureGroup[]>({
    queryKey: ['temperature-groups'],
    queryFn: () =>
      apiClient
        .get('/reference/temperature-groups', { params: { include_inactive: true } })
        .then((r) => r.data),
  });

  const createGroup = useMutation({
    mutationFn: (data: FormData) =>
      apiClient.post('/reference/temperature-groups', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['temperature-groups'] });
      setEditing(null);
      setError('');
    },
    onError: (err: unknown) => {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed');
    },
  });

  const updateGroup = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<FormData> & { is_active?: boolean } }) =>
      apiClient.put(`/reference/temperature-groups/${id}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['temperature-groups'] });
      setEditing(null);
      setError('');
    },
    onError: (err: unknown) => {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed');
    },
  });

  const startEdit = (group: TemperatureGroup) => {
    setForm({
      name: group.name,
      min_temperature: group.min_temperature,
      max_temperature: group.max_temperature,
      description: group.description || '',
      thermocouple: group.thermocouple || '',
      control_cable: group.control_cable || '',
      control_device: group.control_device || '',
      display_order: group.display_order,
    });
    setEditing(group.id);
    setError('');
  };

  const startNew = () => {
    setForm({ ...emptyForm, display_order: (groups?.length || 0) });
    setEditing('new');
    setError('');
  };

  const save = () => {
    if (!form.name.trim()) {
      setError('Name is required');
      return;
    }
    if (form.min_temperature >= form.max_temperature) {
      setError('Min temperature must be less than max');
      return;
    }
    if (editing === 'new') {
      createGroup.mutate(form);
    } else if (editing) {
      updateGroup.mutate({ id: editing, data: form });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Temperature Groups</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage firing temperature groups and equipment specifications
          </p>
        </div>
        <Button size="sm" onClick={startNew} disabled={editing === 'new'}>
          <Plus className="h-4 w-4 mr-1" />
          Add Group
        </Button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-8">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {/* New Group Form */}
      {editing === 'new' && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">New Temperature Group</h3>
          <GroupForm form={form} setForm={setForm} error={error} />
          <div className="flex gap-2 mt-4">
            <Button size="sm" onClick={save} disabled={createGroup.isPending}>
              {createGroup.isPending ? <Spinner className="h-3 w-3 mr-1" /> : <Save className="h-3 w-3 mr-1" />}
              Create
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setEditing(null)}>
              <X className="h-3 w-3 mr-1" /> Cancel
            </Button>
          </div>
        </Card>
      )}

      {/* Groups List */}
      <div className="space-y-4">
        {(groups || []).map((group) => (
          <Card key={group.id}>
            {editing === group.id ? (
              /* Edit mode */
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Edit: {group.name}</h3>
                <GroupForm form={form} setForm={setForm} error={error} />
                <div className="flex gap-2 mt-4">
                  <Button size="sm" onClick={save} disabled={updateGroup.isPending}>
                    {updateGroup.isPending ? <Spinner className="h-3 w-3 mr-1" /> : <Save className="h-3 w-3 mr-1" />}
                    Save
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => setEditing(null)}>
                    <X className="h-3 w-3 mr-1" /> Cancel
                  </Button>
                  {group.is_active ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-600 ml-auto"
                      onClick={() => updateGroup.mutate({ id: group.id, data: { is_active: false } })}
                    >
                      <Trash2 className="h-3 w-3 mr-1" /> Deactivate
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-green-600 ml-auto"
                      onClick={() => updateGroup.mutate({ id: group.id, data: { is_active: true } })}
                    >
                      Activate
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              /* View mode */
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Thermometer className="h-5 w-5 text-orange-500" />
                    <h3 className="text-base font-semibold text-gray-900">{group.name}</h3>
                    {!group.is_active && (
                      <Badge status="inactive" label="Inactive" />
                    )}
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500 text-xs block">Temperature Range</span>
                      <span className="font-medium text-gray-900">
                        {group.min_temperature} – {group.max_temperature} °C
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 text-xs block">Thermocouple</span>
                      <span className="font-medium text-gray-900">
                        {labelFor(group.thermocouple, THERMOCOUPLE_OPTIONS)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 text-xs block">Control Cable</span>
                      <span className="font-medium text-gray-900">
                        {labelFor(group.control_cable, CONTROL_CABLE_OPTIONS)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500 text-xs block">Control Device</span>
                      <span className="font-medium text-gray-900">
                        {labelFor(group.control_device, CONTROL_DEVICE_OPTIONS)}
                      </span>
                    </div>
                  </div>

                  {group.description && (
                    <p className="text-xs text-gray-400 mt-2">{group.description}</p>
                  )}

                  {/* Linked Recipes */}
                  {group.recipes.length > 0 && (
                    <div className="mt-3">
                      <span className="text-xs text-gray-500 font-medium">
                        Linked Recipes ({group.recipes.length}):
                      </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {group.recipes.map((r) => (
                          <span
                            key={r.id}
                            className="inline-flex items-center rounded bg-orange-50 px-2 py-0.5 text-xs text-orange-700"
                          >
                            {r.recipe_name || r.recipe_id.slice(0, 8)}
                            {r.is_default && (
                              <Badge status="active" label="Default" />
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <Button variant="ghost" size="sm" onClick={() => startEdit(group)}>
                  <Pencil className="h-4 w-4" />
                </Button>
              </div>
            )}
          </Card>
        ))}
      </div>

      {!isLoading && (!groups || groups.length === 0) && (
        <div className="text-center text-gray-400 py-8">
          No temperature groups configured. Click "Add Group" to create one.
        </div>
      )}
    </div>
  );
}

function GroupForm({
  form,
  setForm,
  error,
}: {
  form: FormData;
  setForm: (f: FormData) => void;
  error: string;
}) {
  return (
    <div className="space-y-3">
      {error && <p className="text-xs text-red-500">{error}</p>}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Name *</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="e.g. Low Temperature"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Display Order</label>
          <input
            type="number"
            value={form.display_order}
            onChange={(e) => setForm({ ...form, display_order: parseInt(e.target.value) || 0 })}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Min Temperature (°C) *</label>
          <input
            type="number"
            value={form.min_temperature}
            onChange={(e) => setForm({ ...form, min_temperature: parseInt(e.target.value) || 0 })}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Max Temperature (°C) *</label>
          <input
            type="number"
            value={form.max_temperature}
            onChange={(e) => setForm({ ...form, max_temperature: parseInt(e.target.value) || 0 })}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Thermocouple</label>
          <select
            value={form.thermocouple}
            onChange={(e) => setForm({ ...form, thermocouple: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          >
            {THERMOCOUPLE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Control Cable</label>
          <select
            value={form.control_cable}
            onChange={(e) => setForm({ ...form, control_cable: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          >
            {CONTROL_CABLE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Control Device</label>
          <select
            value={form.control_device}
            onChange={(e) => setForm({ ...form, control_device: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          >
            {CONTROL_DEVICE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
        <textarea
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          rows={2}
        />
      </div>
    </div>
  );
}
