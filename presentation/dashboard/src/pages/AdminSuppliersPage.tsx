import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { suppliersApi } from '@/api/suppliers';
import { useSuppliers, type SupplierItem } from '@/hooks/useSuppliers';
import { useMaterialHierarchy } from '@/hooks/useMaterialGroups';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { NumericInput } from '@/components/ui/NumericInput';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

interface SupplierForm {
  name: string;
  contact_person: string;
  phone: string;
  email: string;
  address: string;
  default_lead_time_days: string;
  notes: string;
  is_active: boolean;
  subgroup_ids: string[];
}

const emptyForm: SupplierForm = {
  name: '',
  contact_person: '',
  phone: '',
  email: '',
  address: '',
  default_lead_time_days: '35',
  notes: '',
  is_active: true,
  subgroup_ids: [],
};

export default function AdminSuppliersPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState('');
  const [editItem, setEditItem] = useState<SupplierItem | null>(null);
  const [form, setForm] = useState<SupplierForm>(emptyForm);
  const [formError, setFormError] = useState('');

  const { data, isLoading, isError } = useSuppliers();
  const items = data?.items ?? [];

  const { data: hierarchy } = useMaterialHierarchy();

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => suppliersApi.create(payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['suppliers'] }); closeDialog(); },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to create supplier');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => suppliersApi.update(id, payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['suppliers'] }); closeDialog(); },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to update supplier');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => suppliersApi.remove(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['suppliers'] }); setDeleteId(null); setDeleteError(''); },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setDeleteError(detail ?? 'Failed to delete supplier');
    },
  });

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setEditItem(null);
    setForm(emptyForm);
    setFormError('');
  }, []);

  const openCreate = useCallback(() => {
    setEditItem(null);
    setForm(emptyForm);
    setFormError('');
    setDialogOpen(true);
  }, []);

  const openEdit = useCallback((item: SupplierItem) => {
    setEditItem(item);
    setForm({
      name: item.name,
      contact_person: item.contact_person ?? '',
      phone: item.phone ?? '',
      email: item.email ?? '',
      address: item.address ?? '',
      default_lead_time_days: String(item.default_lead_time_days),
      notes: item.notes ?? '',
      is_active: item.is_active,
      subgroup_ids: item.subgroup_ids ?? [],
    });
    setFormError('');
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    if (!form.name.trim()) { setFormError('Name is required'); return; }
    setFormError('');
    const payload: Record<string, unknown> = {
      name: form.name,
      contact_person: form.contact_person || null,
      phone: form.phone || null,
      email: form.email || null,
      address: form.address || null,
      default_lead_time_days: parseInt(form.default_lead_time_days) || 35,
      notes: form.notes || null,
      is_active: form.is_active,
      subgroup_ids: form.subgroup_ids,
    };
    if (editItem) {
      updateMutation.mutate({ id: editItem.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  }, [form, editItem, createMutation, updateMutation]);

  const toggleSubgroup = useCallback((sgId: string) => {
    setForm((prev) => ({
      ...prev,
      subgroup_ids: prev.subgroup_ids.includes(sgId)
        ? prev.subgroup_ids.filter((id) => id !== sgId)
        : [...prev.subgroup_ids, sgId],
    }));
  }, []);

  const saving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Suppliers</h1>
          <p className="mt-1 text-sm text-gray-500">Manage material suppliers, lead times, and linked subgroups</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>Back to Admin</Button>
          <Button onClick={openCreate}>+ Add Supplier</Button>
        </div>
      </div>

      {isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-red-800">⚠ Error loading suppliers</p>
        </div>
      ) : isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 ? (
        <Card><p className="py-8 text-center text-gray-400">No suppliers found</p></Card>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-xs font-medium uppercase tracking-wider text-gray-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Contact</th>
                <th className="px-4 py-3">Phone</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Lead Time</th>
                <th className="px-4 py-3">Subgroups</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((s) => (
                <tr key={s.id} className="bg-white hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{s.name}</td>
                  <td className="px-4 py-3 text-gray-500">{s.contact_person || <span className="text-gray-300">{'\u2014'}</span>}</td>
                  <td className="px-4 py-3 text-gray-500">{s.phone || <span className="text-gray-300">{'\u2014'}</span>}</td>
                  <td className="px-4 py-3 text-gray-500">{s.email || <span className="text-gray-300">{'\u2014'}</span>}</td>
                  <td className="px-4 py-3 text-gray-500">{s.default_lead_time_days}d</td>
                  <td className="px-4 py-3">
                    {s.subgroup_names && s.subgroup_names.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {s.subgroup_names.map((name, i) => (
                          <span key={i} className="inline-flex rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                            {name}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-300">{'\u2014'}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge status={s.is_active ? 'active' : 'inactive'} label={s.is_active ? 'Active' : 'Inactive'} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(s)}>Edit</Button>
                      <Button variant="ghost" size="sm" className="text-red-600" onClick={() => { setDeleteId(s.id); setDeleteError(''); }}>Delete</Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      <Dialog open={dialogOpen} onClose={closeDialog} title={editItem ? 'Edit Supplier' : 'Add Supplier'} className="w-full max-w-lg">
        <div className="space-y-4">
          <Input label="Name *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Contact Person" value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
            <Input label="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <NumericInput
              label="Lead Time (days)"
              value={form.default_lead_time_days}
              onChange={(e) => setForm({ ...form, default_lead_time_days: e.target.value })}
            />
          </div>
          <Input label="Address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          <Input label="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />

          {/* Subgroup multi-select */}
          {hierarchy && hierarchy.length > 0 && (
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Material Subgroups</label>
              <div className="max-h-48 space-y-3 overflow-y-auto rounded-lg border border-gray-200 p-3">
                {hierarchy.map((g) => (
                  <div key={g.id}>
                    <p className="mb-1 text-xs font-semibold uppercase text-gray-400">
                      {g.icon ? `${g.icon} ` : ''}{g.name}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {g.subgroups.map((sg) => {
                        const selected = form.subgroup_ids.includes(sg.id);
                        return (
                          <button
                            key={sg.id}
                            type="button"
                            onClick={() => toggleSubgroup(sg.id)}
                            className={`rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
                              selected
                                ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                                : 'border-gray-200 text-gray-500 hover:bg-gray-50'
                            }`}
                          >
                            {sg.icon ? `${sg.icon} ` : ''}{sg.name}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
              {form.subgroup_ids.length > 0 && (
                <p className="mt-1 text-xs text-gray-400">{form.subgroup_ids.length} selected</p>
              )}
            </div>
          )}

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
            Active
          </label>
          {formError && <p className="text-sm text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={!form.name || saving}>
              {saving ? 'Saving\u2026' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete dialog */}
      <Dialog open={!!deleteId} onClose={() => { setDeleteId(null); setDeleteError(''); }} title="Delete Supplier">
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Are you sure you want to delete this supplier? Materials linked to this supplier will have their supplier cleared.
          </p>
          {deleteError && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-600">{deleteError}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => { setDeleteId(null); setDeleteError(''); }}>Cancel</Button>
            <Button
              className="bg-red-600 hover:bg-red-700 focus:ring-red-500"
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting\u2026' : 'Delete'}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
