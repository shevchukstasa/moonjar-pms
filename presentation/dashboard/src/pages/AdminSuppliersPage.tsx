import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { suppliersApi } from '@/api/suppliers';
import { useSuppliers, type SupplierItem } from '@/hooks/useSuppliers';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/Table';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
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
};

export default function AdminSuppliersPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<SupplierItem | null>(null);
  const [form, setForm] = useState<SupplierForm>(emptyForm);

  const { data, isLoading } = useSuppliers();
  const items = data?.items ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => suppliersApi.create(payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['suppliers'] }); closeDialog(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => suppliersApi.update(id, payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['suppliers'] }); closeDialog(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => suppliersApi.remove(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['suppliers'] }); setDeleteId(null); },
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
    });
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    const payload: Record<string, unknown> = {
      name: form.name,
      contact_person: form.contact_person || null,
      phone: form.phone || null,
      email: form.email || null,
      address: form.address || null,
      default_lead_time_days: parseInt(form.default_lead_time_days) || 35,
      notes: form.notes || null,
      is_active: form.is_active,
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
      { key: 'contact_person', header: 'Contact', render: (s: SupplierItem) => s.contact_person || <span className="text-gray-400">&mdash;</span> },
      { key: 'phone', header: 'Phone', render: (s: SupplierItem) => s.phone || <span className="text-gray-400">&mdash;</span> },
      { key: 'email', header: 'Email', render: (s: SupplierItem) => s.email || <span className="text-gray-400">&mdash;</span> },
      { key: 'default_lead_time_days', header: 'Lead Time', render: (s: SupplierItem) => `${s.default_lead_time_days} days` },
      {
        key: 'rating',
        header: 'Rating',
        render: (s: SupplierItem) => s.rating != null ? `${s.rating}/5` : <span className="text-gray-400">&mdash;</span>,
      },
      {
        key: 'is_active',
        header: 'Status',
        render: (s: SupplierItem) => <Badge status={s.is_active ? 'active' : 'inactive'} label={s.is_active ? 'Active' : 'Inactive'} />,
      },
      {
        key: 'actions',
        header: '',
        render: (s: SupplierItem) => (
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={() => openEdit(s)}>Edit</Button>
            <Button variant="ghost" size="sm" className="text-red-600" onClick={() => setDeleteId(s.id)}>Delete</Button>
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
          <h1 className="text-2xl font-bold text-gray-900">Suppliers</h1>
          <p className="mt-1 text-sm text-gray-500">Manage material suppliers and lead times</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>Back to Admin</Button>
          <Button onClick={openCreate}>+ Add Supplier</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 ? (
        <Card><p className="py-8 text-center text-gray-400">No suppliers found</p></Card>
      ) : (
        <DataTable columns={columns} data={items as unknown as Record<string, unknown>[]} />
      )}

      <Dialog open={dialogOpen} onClose={closeDialog} title={editItem ? 'Edit Supplier' : 'Add Supplier'} className="w-full max-w-lg">
        <div className="space-y-4">
          <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Contact Person" value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
            <Input label="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <Input label="Lead Time (days)" type="number" value={form.default_lead_time_days} onChange={(e) => setForm({ ...form, default_lead_time_days: e.target.value })} />
          </div>
          <Input label="Address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          <Input label="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
            Active
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={!form.name || saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Supplier">
        <p className="text-sm text-gray-600">Are you sure you want to delete this supplier? This action cannot be undone.</p>
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
