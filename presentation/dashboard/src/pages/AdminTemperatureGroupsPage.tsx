import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import apiClient from '@/api/client';
import { Thermometer, Plus, Pencil, Trash2, X, Save } from 'lucide-react';
import { Dialog } from '@/components/ui/Dialog';
import { CsvImportDialog } from '@/components/admin/CsvImportDialog';
import { CSV_CONFIGS } from '@/config/csvImportConfigs';

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
  temperature: number;
  description: string | null;
  is_active: boolean;
  display_order: number;
  recipes: RecipeLink[];
  created_at: string | null;
  updated_at: string | null;
}

interface FormData {
  name: string;
  temperature: number;
  description: string;
  display_order: number;
}

const emptyForm: FormData = {
  name: '',
  temperature: 1012,
  description: '',
  display_order: 0,
};

export default function AdminTemperatureGroupsPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<string | null>(null); // group id or 'new'
  const [form, setForm] = useState<FormData>(emptyForm);
  const [error, setError] = useState('');
  const [csvOpen, setCsvOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

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

  const deleteGroup = useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`/reference/temperature-groups/${id}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['temperature-groups'] });
      setDeleteId(null);
    },
    onError: (err: unknown) => {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to delete');
    },
  });

  const startEdit = (group: TemperatureGroup) => {
    setForm({
      name: group.name,
      temperature: group.temperature,
      description: group.description || '',
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
    if (!form.temperature || form.temperature <= 0) {
      setError('Temperature is required');
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
            Manage firing temperature groups and linked recipes
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => setCsvOpen(true)}>Import CSV</Button>
          <Button size="sm" onClick={startNew} disabled={editing === 'new'}>
            <Plus className="h-4 w-4 mr-1" />
            Add Group
          </Button>
        </div>
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
                    <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-sm font-semibold text-orange-800">
                      {group.temperature} °C
                    </span>
                    {!group.is_active && (
                      <Badge status="inactive" label="Inactive" />
                    )}
                  </div>

                  {group.description && (
                    <p className="text-xs text-gray-400 mt-1">{group.description}</p>
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

                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => startEdit(group)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="sm" className="text-red-600" onClick={() => setDeleteId(group.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </Card>
        ))}
      </div>

      <CsvImportDialog open={csvOpen} onClose={() => setCsvOpen(false)} {...CSV_CONFIGS.temperature_groups} onSuccess={() => qc.invalidateQueries({ queryKey: ['temperature-groups'] })} />

      {!isLoading && (!groups || groups.length === 0) && (
        <div className="text-center text-gray-400 py-8">
          No temperature groups configured. Click &quot;Add Group&quot; to create one.
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Temperature Group">
        <p className="text-sm text-gray-600">Are you sure you want to delete this temperature group? This action will be logged.</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => deleteId && deleteGroup.mutate(deleteId)} disabled={deleteGroup.isPending}>
            {deleteGroup.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
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

      <div className="grid grid-cols-3 gap-3">
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
          <label className="block text-xs font-medium text-gray-600 mb-1">Temperature (°C) *</label>
          <input
            type="number"
            value={form.temperature}
            onChange={(e) => setForm({ ...form, temperature: parseInt(e.target.value) || 0 })}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="e.g. 1012"
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
