import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import {
  useAllWarehouseSections,
  useCreateWarehouseSection,
  useUpdateWarehouseSection,
  useDeleteWarehouseSection,
  type WarehouseSection,
} from '@/hooks/useWarehouseSections';
import { useFactories } from '@/hooks/useFactories';
import { useUsers } from '@/hooks/useUsers';

interface FormData {
  name: string;
  code: string;
  description: string;
  factory_id: string;
  managed_by: string;
  warehouse_type: string;
  display_order: number;
  is_default: boolean;
  is_active: boolean;
}

const EMPTY_FORM: FormData = {
  name: '',
  code: '',
  description: '',
  factory_id: '',
  managed_by: '',
  warehouse_type: 'section',
  display_order: 0,
  is_default: false,
  is_active: true,
};

const WAREHOUSE_TYPES = [
  { value: 'section', label: 'Section' },
  { value: 'warehouse', label: 'Warehouse' },
  { value: 'virtual', label: 'Virtual' },
];

export default function AdminWarehousesPage() {
  const navigate = useNavigate();
  const { data, isLoading } = useAllWarehouseSections(true);
  const { data: factoriesData } = useFactories();
  const { data: usersData } = useUsers({ role: 'production_manager', per_page: 100 });
  const createMut = useCreateWarehouseSection();
  const updateMut = useUpdateWarehouseSection();
  const deleteMut = useDeleteWarehouseSection();

  const [editing, setEditing] = useState<string | null>(null); // 'new' | id | null
  const [form, setForm] = useState<FormData>(EMPTY_FORM);
  const [error, setError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const items = data?.items ?? [];
  const factories = factoriesData?.items ?? [];
  const managers = usersData?.items ?? [];

  function startCreate() {
    setForm(EMPTY_FORM);
    setEditing('new');
    setError('');
  }

  function startEdit(item: WarehouseSection) {
    setForm({
      name: item.name,
      code: item.code,
      description: item.description ?? '',
      factory_id: item.factory_id ?? '',
      managed_by: item.managed_by ?? '',
      warehouse_type: item.warehouse_type || 'section',
      display_order: item.display_order ?? 0,
      is_default: item.is_default,
      is_active: item.is_active,
    });
    setEditing(item.id);
    setError('');
  }

  function cancel() {
    setEditing(null);
    setError('');
  }

  async function handleSave() {
    if (!form.name.trim() || !form.code.trim()) {
      setError('Name and code are required');
      return;
    }
    setError('');
    const payload = {
      name: form.name.trim(),
      code: form.code.trim(),
      description: form.description.trim() || undefined,
      factory_id: form.factory_id || null,
      managed_by: form.managed_by || null,
      warehouse_type: form.warehouse_type,
      display_order: form.display_order,
      is_default: form.is_default,
      is_active: form.is_active,
    };

    try {
      if (editing === 'new') {
        await createMut.mutateAsync(payload);
      } else {
        await updateMut.mutateAsync({ id: editing!, data: payload });
      }
      setEditing(null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to save';
      setError(msg);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteMut.mutateAsync(id);
      setDeleteConfirm(null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to delete';
      setError(msg);
    }
  }

  function renderForm() {
    return (
      <div className="space-y-3">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Name *</label>
            <input
              className="w-full rounded border px-3 py-2 text-sm"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Main Warehouse"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Code *</label>
            <input
              className="w-full rounded border px-3 py-2 text-sm"
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="e.g. main_warehouse"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
            <input
              className="w-full rounded border px-3 py-2 text-sm"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Optional description"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Factory</label>
            <select
              className="w-full rounded border px-3 py-2 text-sm"
              value={form.factory_id}
              onChange={(e) => setForm({ ...form, factory_id: e.target.value })}
            >
              <option value="">Global (no factory)</option>
              {factories.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Managed By (PM)</label>
            <select
              className="w-full rounded border px-3 py-2 text-sm"
              value={form.managed_by}
              onChange={(e) => setForm({ ...form, managed_by: e.target.value })}
            >
              <option value="">Not assigned</option>
              {managers.map((u) => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Type</label>
            <select
              className="w-full rounded border px-3 py-2 text-sm"
              value={form.warehouse_type}
              onChange={(e) => setForm({ ...form, warehouse_type: e.target.value })}
            >
              {WAREHOUSE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Display Order</label>
            <input
              type="number"
              className="w-full rounded border px-3 py-2 text-sm"
              value={form.display_order}
              onChange={(e) => setForm({ ...form, display_order: Number(e.target.value) || 0 })}
            />
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
              />
              Default
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />
              Active
            </label>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleSave} disabled={createMut.isPending || updateMut.isPending}>
            {createMut.isPending || updateMut.isPending ? 'Saving...' : 'Save'}
          </Button>
          <Button variant="secondary" onClick={cancel}>Cancel</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => navigate('/admin')} className="mb-2 text-sm text-blue-600 hover:underline">
            &larr; Back to Admin
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Warehouse Sections</h1>
          <p className="text-sm text-gray-500">Manage warehouses and storage sections. Global warehouses are shared across all factories.</p>
        </div>
        {editing !== 'new' && (
          <Button onClick={startCreate}>+ Add Warehouse</Button>
        )}
      </div>

      {isLoading && (
        <div className="flex justify-center py-12"><Spinner /></div>
      )}

      {/* Create form */}
      {editing === 'new' && (
        <Card title="New Warehouse Section">
          {renderForm()}
        </Card>
      )}

      {/* List */}
      {items.map((item) => (
        <Card key={item.id}>
          {editing === item.id ? (
            <>
              <h3 className="mb-3 font-semibold text-gray-900">Edit: {item.name}</h3>
              {renderForm()}
            </>
          ) : (
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-gray-900">{item.name}</h3>
                  <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{item.code}</span>
                  <span className={`rounded px-2 py-0.5 text-xs ${
                    item.warehouse_type === 'warehouse' ? 'bg-blue-100 text-blue-700' :
                    item.warehouse_type === 'virtual' ? 'bg-purple-100 text-purple-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {item.warehouse_type}
                  </span>
                  {!item.is_active && (
                    <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">Inactive</span>
                  )}
                  {item.is_default && (
                    <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">Default</span>
                  )}
                </div>
                {item.description && (
                  <p className="text-sm text-gray-500">{item.description}</p>
                )}
                <div className="flex gap-4 text-xs text-gray-500">
                  <span>Factory: {(item as WarehouseSection & { factory_name?: string }).factory_name || 'Global'}</span>
                  {item.managed_by_name && <span>Manager: {item.managed_by_name}</span>}
                  <span>Order: {item.display_order}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => startEdit(item)}>
                  Edit
                </Button>
                {deleteConfirm === item.id ? (
                  <div className="flex gap-1">
                    <Button
                      variant="secondary"
                      className="!bg-red-600 !text-white hover:!bg-red-700"
                      onClick={() => handleDelete(item.id)}
                      disabled={deleteMut.isPending}
                    >
                      Confirm
                    </Button>
                    <Button variant="secondary" onClick={() => setDeleteConfirm(null)}>
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="secondary"
                    className="!text-red-600 hover:!bg-red-50"
                    onClick={() => setDeleteConfirm(item.id)}
                  >
                    Delete
                  </Button>
                )}
              </div>
            </div>
          )}
        </Card>
      ))}

      {!isLoading && items.length === 0 && (
        <Card>
          <p className="py-8 text-center text-gray-500">No warehouse sections yet. Click "+ Add Warehouse" to create one.</p>
        </Card>
      )}
    </div>
  );
}
