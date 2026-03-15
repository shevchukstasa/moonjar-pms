import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { packagingApi, type PackagingBoxType, type PackagingCapacity, type PackagingSpacerRule } from '@/api/packaging';
import { usePackagingBoxTypes, usePackagingSizes, type SizeItem } from '@/hooks/usePackaging';
import { useMaterials, type MaterialItem } from '@/hooks/useMaterials';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { NumericInput } from '@/components/ui/NumericInput';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

/* ── Box Type Form ─────────────────────────────────────── */

interface BoxTypeForm {
  material_id: string;
  name: string;
  notes: string;
  is_active: boolean;
}

const emptyBoxForm: BoxTypeForm = {
  material_id: '',
  name: '',
  notes: '',
  is_active: true,
};

/* ── Capacity Row ──────────────────────────────────────── */

interface CapRow {
  size_id: string;
  pieces_per_box: string;
  sqm_per_box: string;
}

/* ── Spacer Row ────────────────────────────────────────── */

interface SpacerRow {
  size_id: string;
  spacer_material_id: string;
  qty_per_box: string;
}

/* ── Component ─────────────────────────────────────────── */

export default function AdminPackagingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  /* Data */
  const { data, isLoading, isError } = usePackagingBoxTypes();
  const items = data?.items ?? [];
  const { data: sizesData } = usePackagingSizes();
  const sizes = sizesData?.items ?? [];
  const { data: matsData } = useMaterials({ material_type: 'packaging', per_page: 200 });
  const packagingMaterials = matsData?.items ?? [];
  const { data: allMatsData } = useMaterials({ per_page: 500 });
  const allMaterials = allMatsData?.items ?? [];

  /* Box Type Dialog */
  const [boxDialogOpen, setBoxDialogOpen] = useState(false);
  const [editBox, setEditBox] = useState<PackagingBoxType | null>(null);
  const [boxForm, setBoxForm] = useState<BoxTypeForm>(emptyBoxForm);
  const [boxError, setBoxError] = useState('');

  /* Capacity / Spacer panel */
  const [selectedBox, setSelectedBox] = useState<PackagingBoxType | null>(null);
  const [capRows, setCapRows] = useState<CapRow[]>([]);
  const [spacerRows, setSpacerRows] = useState<SpacerRow[]>([]);
  const [panelError, setPanelError] = useState('');

  /* Delete */
  const [deleteId, setDeleteId] = useState<string | null>(null);

  /* ── Mutations ────────────────────────────────────────── */

  const createMut = useMutation({
    mutationFn: (p: Record<string, unknown>) => packagingApi.create(p as any),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['packaging-box-types'] }); closeBoxDialog(); },
    onError: (e: any) => setBoxError(e?.response?.data?.detail ?? 'Failed'),
  });
  const updateMut = useMutation({
    mutationFn: ({ id, p }: { id: string; p: Record<string, unknown> }) => packagingApi.update(id, p),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['packaging-box-types'] }); closeBoxDialog(); },
    onError: (e: any) => setBoxError(e?.response?.data?.detail ?? 'Failed'),
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => packagingApi.remove(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['packaging-box-types'] }); setDeleteId(null); setSelectedBox(null); },
  });
  const capMut = useMutation({
    mutationFn: ({ id, caps }: { id: string; caps: any[] }) => packagingApi.setCapacities(id, caps),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['packaging-box-types'] }); setPanelError(''); },
    onError: (e: any) => setPanelError(e?.response?.data?.detail ?? 'Failed to save capacities'),
  });
  const spacerMut = useMutation({
    mutationFn: ({ id, sp }: { id: string; sp: any[] }) => packagingApi.setSpacers(id, sp),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['packaging-box-types'] }); setPanelError(''); },
    onError: (e: any) => setPanelError(e?.response?.data?.detail ?? 'Failed to save spacers'),
  });

  /* ── Handlers ─────────────────────────────────────────── */

  const closeBoxDialog = useCallback(() => {
    setBoxDialogOpen(false);
    setEditBox(null);
    setBoxForm(emptyBoxForm);
    setBoxError('');
  }, []);

  const openCreate = useCallback(() => {
    setEditBox(null);
    setBoxForm(emptyBoxForm);
    setBoxError('');
    setBoxDialogOpen(true);
  }, []);

  const openEdit = useCallback((bt: PackagingBoxType) => {
    setEditBox(bt);
    setBoxForm({
      material_id: bt.material_id,
      name: bt.name,
      notes: bt.notes ?? '',
      is_active: bt.is_active,
    });
    setBoxError('');
    setBoxDialogOpen(true);
  }, []);

  const handleBoxSubmit = useCallback(() => {
    if (!boxForm.name.trim()) { setBoxError('Name is required'); return; }
    if (!boxForm.material_id) { setBoxError('Material is required'); return; }
    const payload = {
      material_id: boxForm.material_id,
      name: boxForm.name,
      notes: boxForm.notes || null,
      is_active: boxForm.is_active,
    };
    if (editBox) {
      updateMut.mutate({ id: editBox.id, p: payload });
    } else {
      createMut.mutate(payload);
    }
  }, [boxForm, editBox, createMut, updateMut]);

  const selectBox = useCallback((bt: PackagingBoxType) => {
    setSelectedBox(bt);
    setPanelError('');
    setCapRows(
      bt.capacities.map((c) => ({
        size_id: c.size_id,
        pieces_per_box: c.pieces_per_box != null ? String(c.pieces_per_box) : '',
        sqm_per_box: c.sqm_per_box != null ? String(c.sqm_per_box) : '',
      }))
    );
    setSpacerRows(
      bt.spacer_rules.map((sr) => ({
        size_id: sr.size_id,
        spacer_material_id: sr.spacer_material_id,
        qty_per_box: String(sr.qty_per_box),
      }))
    );
  }, []);

  const addCapRow = useCallback(() => {
    if (capRows.length >= 10) return;
    setCapRows((prev) => [...prev, { size_id: '', pieces_per_box: '', sqm_per_box: '' }]);
  }, [capRows.length]);

  const removeCapRow = useCallback((idx: number) => {
    setCapRows((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const updateCapRow = useCallback((idx: number, field: keyof CapRow, val: string) => {
    setCapRows((prev) => prev.map((r, i) => i === idx ? { ...r, [field]: val } : r));
  }, []);

  const saveCapacities = useCallback(() => {
    if (!selectedBox) return;
    const caps = capRows
      .filter((r) => r.size_id)
      .map((r) => ({
        size_id: r.size_id,
        pieces_per_box: r.pieces_per_box ? parseInt(r.pieces_per_box) : undefined,
        sqm_per_box: r.sqm_per_box ? parseFloat(r.sqm_per_box) : undefined,
      }));
    capMut.mutate({ id: selectedBox.id, caps });
  }, [selectedBox, capRows, capMut]);

  const addSpacerRow = useCallback(() => {
    setSpacerRows((prev) => [...prev, { size_id: '', spacer_material_id: '', qty_per_box: '1' }]);
  }, []);

  const removeSpacerRow = useCallback((idx: number) => {
    setSpacerRows((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const updateSpacerRow = useCallback((idx: number, field: keyof SpacerRow, val: string) => {
    setSpacerRows((prev) => prev.map((r, i) => i === idx ? { ...r, [field]: val } : r));
  }, []);

  const saveSpacers = useCallback(() => {
    if (!selectedBox) return;
    const sp = spacerRows
      .filter((r) => r.size_id && r.spacer_material_id)
      .map((r) => ({
        size_id: r.size_id,
        spacer_material_id: r.spacer_material_id,
        qty_per_box: parseInt(r.qty_per_box) || 1,
      }));
    spacerMut.mutate({ id: selectedBox.id, sp });
  }, [selectedBox, spacerRows, spacerMut]);

  const saving = createMut.isPending || updateMut.isPending;

  /* Refresh selected box after mutation */
  const refreshedSelectedBox = selectedBox
    ? items.find((b) => b.id === selectedBox.id) ?? selectedBox
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Packaging Rules</h1>
          <p className="mt-1 text-sm text-gray-500">
            Configure box types, tile size capacities, and spacer requirements
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>Back to Admin</Button>
          <Button onClick={openCreate}>+ Add Box Type</Button>
        </div>
      </div>

      {isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-red-800">{'\u26A0'} Error loading packaging data</p>
        </div>
      ) : isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 ? (
        <Card><p className="py-8 text-center text-gray-400">No box types configured</p></Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left: Box Types list */}
          <div className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">Box Types</h2>
            {items.map((bt) => (
              <div
                key={bt.id}
                onClick={() => selectBox(bt)}
                className={`cursor-pointer rounded-lg border p-4 transition-colors ${
                  refreshedSelectedBox?.id === bt.id
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-gray-200 bg-white hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{bt.name}</p>
                    <p className="text-xs text-gray-500">
                      {bt.material_code ?? ''} {bt.material_name ?? 'No material'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge status={bt.is_active ? 'active' : 'inactive'} label={bt.is_active ? 'Active' : 'Inactive'} />
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {bt.capacities.length} sizes
                    </span>
                  </div>
                </div>
                {bt.capacities.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {bt.capacities.map((c) => (
                      <span key={c.id} className="inline-flex rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                        {c.size_name} {'\u2014'} {c.pieces_per_box != null ? `${c.pieces_per_box} pcs` : ''}{c.sqm_per_box != null ? ` ${c.sqm_per_box} m\u00B2` : ''}
                      </span>
                    ))}
                  </div>
                )}
                <div className="mt-2 flex gap-1">
                  <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); openEdit(bt); }}>Edit</Button>
                  <Button variant="ghost" size="sm" className="text-red-600" onClick={(e) => { e.stopPropagation(); setDeleteId(bt.id); }}>Delete</Button>
                </div>
              </div>
            ))}
          </div>

          {/* Right: Capacities + Spacers panel */}
          {refreshedSelectedBox ? (
            <div className="space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
                {refreshedSelectedBox.name} {'\u2014'} Configuration
              </h2>

              {panelError && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-600">{panelError}</p>}

              {/* Capacities */}
              <Card>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-gray-700">Size Capacities</h3>
                    <Button size="sm" onClick={addCapRow} disabled={capRows.length >= 10}>+ Add Size</Button>
                  </div>
                  {capRows.length === 0 ? (
                    <p className="text-sm text-gray-400">No capacities configured. Add a size.</p>
                  ) : (
                    <div className="space-y-2">
                      {capRows.map((row, idx) => (
                        <div key={idx} className="flex items-end gap-2">
                          <div className="flex-1">
                            {idx === 0 && <label className="mb-1 block text-xs text-gray-500">Size</label>}
                            <select
                              value={row.size_id}
                              onChange={(e) => updateCapRow(idx, 'size_id', e.target.value)}
                              className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                            >
                              <option value="">Select size...</option>
                              {sizes.map((s) => (
                                <option key={s.id} value={s.id}>{s.name}{s.is_custom ? ' (custom)' : ''}</option>
                              ))}
                            </select>
                          </div>
                          <div className="w-24">
                            {idx === 0 && <label className="mb-1 block text-xs text-gray-500">Pcs/box</label>}
                            <NumericInput
                              value={row.pieces_per_box}
                              onChange={(e) => updateCapRow(idx, 'pieces_per_box', e.target.value)}
                              placeholder="pcs"
                            />
                          </div>
                          <div className="w-24">
                            {idx === 0 && <label className="mb-1 block text-xs text-gray-500">m{'\u00B2'}/box</label>}
                            <NumericInput
                              value={row.sqm_per_box}
                              onChange={(e) => updateCapRow(idx, 'sqm_per_box', e.target.value)}
                              placeholder="m\u00B2"
                            />
                          </div>
                          <button
                            onClick={() => removeCapRow(idx)}
                            className="mb-0.5 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
                          >
                            {'\u2715'}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="flex justify-end pt-1">
                    <Button size="sm" onClick={saveCapacities} disabled={capMut.isPending}>
                      {capMut.isPending ? 'Saving\u2026' : 'Save Capacities'}
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Spacer Rules */}
              <Card>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-gray-700">Spacer Rules</h3>
                    <Button size="sm" onClick={addSpacerRow}>+ Add Spacer</Button>
                  </div>
                  {spacerRows.length === 0 ? (
                    <p className="text-sm text-gray-400">No spacer rules. Add one.</p>
                  ) : (
                    <div className="space-y-2">
                      {spacerRows.map((row, idx) => (
                        <div key={idx} className="flex items-end gap-2">
                          <div className="w-28">
                            {idx === 0 && <label className="mb-1 block text-xs text-gray-500">Size</label>}
                            <select
                              value={row.size_id}
                              onChange={(e) => updateSpacerRow(idx, 'size_id', e.target.value)}
                              className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                            >
                              <option value="">Size...</option>
                              {sizes.map((s) => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                              ))}
                            </select>
                          </div>
                          <div className="flex-1">
                            {idx === 0 && <label className="mb-1 block text-xs text-gray-500">Spacer Material</label>}
                            <select
                              value={row.spacer_material_id}
                              onChange={(e) => updateSpacerRow(idx, 'spacer_material_id', e.target.value)}
                              className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                            >
                              <option value="">Select material...</option>
                              {allMaterials
                                .filter((m) => m.material_type === 'packaging' || m.material_type === 'consumable')
                                .map((m) => (
                                  <option key={m.id} value={m.id}>{m.material_code} {m.name}</option>
                                ))}
                            </select>
                          </div>
                          <div className="w-20">
                            {idx === 0 && <label className="mb-1 block text-xs text-gray-500">Qty/box</label>}
                            <NumericInput
                              value={row.qty_per_box}
                              onChange={(e) => updateSpacerRow(idx, 'qty_per_box', e.target.value)}
                              placeholder="qty"
                            />
                          </div>
                          <button
                            onClick={() => removeSpacerRow(idx)}
                            className="mb-0.5 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
                          >
                            {'\u2715'}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="flex justify-end pt-1">
                    <Button size="sm" onClick={saveSpacers} disabled={spacerMut.isPending}>
                      {spacerMut.isPending ? 'Saving\u2026' : 'Save Spacers'}
                    </Button>
                  </div>
                </div>
              </Card>
            </div>
          ) : (
            <Card>
              <p className="py-12 text-center text-gray-400">Select a box type to configure capacities and spacers</p>
            </Card>
          )}
        </div>
      )}

      {/* Create / Edit Box Type Dialog */}
      <Dialog open={boxDialogOpen} onClose={closeBoxDialog} title={editBox ? 'Edit Box Type' : 'Add Box Type'} className="w-full max-w-md">
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Packaging Material *</label>
            <select
              value={boxForm.material_id}
              onChange={(e) => setBoxForm({ ...boxForm, material_id: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select material...</option>
              {packagingMaterials.map((m) => (
                <option key={m.id} value={m.id}>{m.material_code} {m.name}</option>
              ))}
            </select>
          </div>
          <Input label="Name *" value={boxForm.name} onChange={(e) => setBoxForm({ ...boxForm, name: e.target.value })} />
          <Input label="Notes" value={boxForm.notes} onChange={(e) => setBoxForm({ ...boxForm, notes: e.target.value })} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={boxForm.is_active} onChange={(e) => setBoxForm({ ...boxForm, is_active: e.target.checked })} className="rounded" />
            Active
          </label>
          {boxError && <p className="text-sm text-red-600">{boxError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeBoxDialog}>Cancel</Button>
            <Button onClick={handleBoxSubmit} disabled={!boxForm.name || !boxForm.material_id || saving}>
              {saving ? 'Saving\u2026' : editBox ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Box Type">
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Are you sure? This will delete all capacities and spacer rules for this box type.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button
              className="bg-red-600 hover:bg-red-700 focus:ring-red-500"
              onClick={() => deleteId && deleteMut.mutate(deleteId)}
              disabled={deleteMut.isPending}
            >
              {deleteMut.isPending ? 'Deleting\u2026' : 'Delete'}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
