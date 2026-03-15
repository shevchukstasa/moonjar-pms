import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { packagingApi, type PackagingBoxType } from '@/api/packaging';
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

  /* Expanded box (selected for capacity/spacer editing) */
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [capRows, setCapRows] = useState<CapRow[]>([]);
  const [spacerRows, setSpacerRows] = useState<SpacerRow[]>([]);
  const [panelError, setPanelError] = useState('');

  /* Delete */
  const [deleteId, setDeleteId] = useState<string | null>(null);

  /* Auto-expand newly created box type */
  const [pendingExpandId, setPendingExpandId] = useState<string | null>(null);

  /* ── Mutations ────────────────────────────────────────── */

  const createMut = useMutation({
    mutationFn: (p: Record<string, unknown>) => packagingApi.create(p as any),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['packaging-box-types'] });
      closeBoxDialog();
      // Auto-expand new box type after data refreshes
      if (data?.id) setPendingExpandId(data.id);
    },
    onError: (e: any) => setBoxError(e?.response?.data?.detail ?? 'Failed'),
  });
  const updateMut = useMutation({
    mutationFn: ({ id, p }: { id: string; p: Record<string, unknown> }) => packagingApi.update(id, p),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['packaging-box-types'] }); closeBoxDialog(); },
    onError: (e: any) => setBoxError(e?.response?.data?.detail ?? 'Failed'),
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => packagingApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packaging-box-types'] });
      setDeleteId(null);
      setExpandedId(null);
    },
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

  /* Auto-expand after create */
  useEffect(() => {
    if (pendingExpandId && items.find((b) => b.id === pendingExpandId)) {
      toggleExpand(items.find((b) => b.id === pendingExpandId)!);
      setPendingExpandId(null);
    }
  }, [pendingExpandId, items]);

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

  const toggleExpand = useCallback((bt: PackagingBoxType) => {
    if (expandedId === bt.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(bt.id);
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
  }, [expandedId]);

  /* Capacity handlers */
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
    if (!expandedId) return;
    const caps = capRows
      .filter((r) => r.size_id)
      .map((r) => ({
        size_id: r.size_id,
        pieces_per_box: r.pieces_per_box ? parseInt(r.pieces_per_box) : undefined,
        sqm_per_box: r.sqm_per_box ? parseFloat(r.sqm_per_box) : undefined,
      }));
    capMut.mutate({ id: expandedId, caps });
  }, [expandedId, capRows, capMut]);

  /* Spacer handlers */
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
    if (!expandedId) return;
    const sp = spacerRows
      .filter((r) => r.size_id && r.spacer_material_id)
      .map((r) => ({
        size_id: r.size_id,
        spacer_material_id: r.spacer_material_id,
        qty_per_box: parseInt(r.qty_per_box) || 1,
      }));
    spacerMut.mutate({ id: expandedId, sp });
  }, [expandedId, spacerRows, spacerMut]);

  const saving = createMut.isPending || updateMut.isPending;

  /* Keep expanded box data fresh */
  const getExpandedBox = (): PackagingBoxType | null => {
    if (!expandedId) return null;
    return items.find((b) => b.id === expandedId) ?? null;
  };

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
        <Card>
          <div className="py-10 text-center">
            <p className="text-lg font-medium text-gray-500">No box types configured</p>
            <p className="mt-2 text-sm text-gray-400">
              Create a box type, then configure which tile sizes fit in it and how many pieces per box.
            </p>
            <Button className="mt-4" onClick={openCreate}>+ Add Box Type</Button>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {items.map((bt) => {
            const isExpanded = expandedId === bt.id;
            return (
              <Card key={bt.id} className="overflow-hidden">
                {/* Card header (always visible) */}
                <div
                  onClick={() => toggleExpand(bt)}
                  className="cursor-pointer p-4 transition-colors hover:bg-gray-50"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`text-lg transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                        {'\u25B6'}
                      </span>
                      <div>
                        <p className="font-semibold text-gray-900">{bt.name}</p>
                        <p className="text-xs text-gray-500">
                          {bt.material_code ?? ''} {bt.material_name ?? 'No material'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge status={bt.is_active ? 'active' : 'inactive'} label={bt.is_active ? 'Active' : 'Inactive'} />
                      <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                        {bt.capacities.length} {bt.capacities.length === 1 ? 'size' : 'sizes'}
                      </span>
                      {bt.spacer_rules.length > 0 && (
                        <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700">
                          {bt.spacer_rules.length} {bt.spacer_rules.length === 1 ? 'spacer' : 'spacers'}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Summary badges (when collapsed) */}
                  {!isExpanded && bt.capacities.length > 0 && (
                    <div className="mt-2 ml-8 flex flex-wrap gap-1">
                      {bt.capacities.map((c) => (
                        <span key={c.id} className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                          {c.size_name}{' '}
                          {c.pieces_per_box != null ? `${c.pieces_per_box} pcs` : ''}
                          {c.pieces_per_box != null && c.sqm_per_box != null ? ' / ' : ''}
                          {c.sqm_per_box != null ? `${c.sqm_per_box} m\u00B2` : ''}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Expanded panel */}
                {isExpanded && (
                  <div className="border-t border-gray-200 bg-gray-50 px-4 py-4 space-y-5">
                    {/* Actions bar */}
                    <div className="flex gap-2">
                      <Button variant="secondary" size="sm" onClick={(e) => { e.stopPropagation(); openEdit(bt); }}>
                        Edit Box Type
                      </Button>
                      <Button variant="secondary" size="sm" className="text-red-600 hover:bg-red-50" onClick={(e) => { e.stopPropagation(); setDeleteId(bt.id); }}>
                        Delete
                      </Button>
                    </div>

                    {panelError && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-600">{panelError}</p>}

                    {/* Capacities section */}
                    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-sm font-semibold text-gray-800">Size Capacities</h3>
                          <p className="text-xs text-gray-500">How many pieces / m{'\u00B2'} of each tile size fit in this box</p>
                        </div>
                        <Button size="sm" onClick={addCapRow} disabled={capRows.length >= 10}>+ Add Size</Button>
                      </div>
                      {capRows.length === 0 ? (
                        <div className="rounded-md bg-amber-50 px-3 py-3 text-sm text-amber-700">
                          No sizes configured yet. Click "+ Add Size" to specify how many tiles fit per box.
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {/* Header row */}
                          <div className="flex items-end gap-2 text-xs font-medium text-gray-500">
                            <div className="flex-1">Size</div>
                            <div className="w-28">Pieces / box</div>
                            <div className="w-28">m{'\u00B2'} / box</div>
                            <div className="w-8" />
                          </div>
                          {capRows.map((row, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                              <div className="flex-1">
                                <select
                                  value={row.size_id}
                                  onChange={(e) => updateCapRow(idx, 'size_id', e.target.value)}
                                  className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                                >
                                  <option value="">Select size...</option>
                                  {sizes.map((s) => (
                                    <option key={s.id} value={s.id}>
                                      {s.name} ({s.width_mm}x{s.height_mm}mm){s.is_custom ? ' \u2014 custom' : ''}
                                    </option>
                                  ))}
                                </select>
                              </div>
                              <div className="w-28">
                                <NumericInput
                                  value={row.pieces_per_box}
                                  onChange={(e) => updateCapRow(idx, 'pieces_per_box', e.target.value)}
                                  placeholder="pcs"
                                />
                              </div>
                              <div className="w-28">
                                <NumericInput
                                  value={row.sqm_per_box}
                                  onChange={(e) => updateCapRow(idx, 'sqm_per_box', e.target.value)}
                                  placeholder="m\u00B2"
                                />
                              </div>
                              <button
                                onClick={() => removeCapRow(idx)}
                                className="flex h-8 w-8 items-center justify-center rounded text-gray-400 hover:bg-red-50 hover:text-red-600"
                              >
                                {'\u2715'}
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                      {capRows.length > 0 && (
                        <div className="flex justify-end pt-1">
                          <Button size="sm" onClick={saveCapacities} disabled={capMut.isPending}>
                            {capMut.isPending ? 'Saving\u2026' : 'Save Capacities'}
                          </Button>
                        </div>
                      )}
                    </div>

                    {/* Spacer Rules section */}
                    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-sm font-semibold text-gray-800">Spacer Rules</h3>
                          <p className="text-xs text-gray-500">How many spacers go into each box per tile size</p>
                        </div>
                        <Button size="sm" onClick={addSpacerRow}>+ Add Spacer</Button>
                      </div>
                      {spacerRows.length === 0 ? (
                        <p className="text-sm text-gray-400">No spacer rules. Click "+ Add Spacer" if spacers are needed.</p>
                      ) : (
                        <div className="space-y-2">
                          {/* Header row */}
                          <div className="flex items-end gap-2 text-xs font-medium text-gray-500">
                            <div className="w-36">Size</div>
                            <div className="flex-1">Spacer Material</div>
                            <div className="w-24">Qty / box</div>
                            <div className="w-8" />
                          </div>
                          {spacerRows.map((row, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                              <div className="w-36">
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
                              <div className="w-24">
                                <NumericInput
                                  value={row.qty_per_box}
                                  onChange={(e) => updateSpacerRow(idx, 'qty_per_box', e.target.value)}
                                  placeholder="qty"
                                />
                              </div>
                              <button
                                onClick={() => removeSpacerRow(idx)}
                                className="flex h-8 w-8 items-center justify-center rounded text-gray-400 hover:bg-red-50 hover:text-red-600"
                              >
                                {'\u2715'}
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                      {spacerRows.length > 0 && (
                        <div className="flex justify-end pt-1">
                          <Button size="sm" onClick={saveSpacers} disabled={spacerMut.isPending}>
                            {spacerMut.isPending ? 'Saving\u2026' : 'Save Spacers'}
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
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
          {!editBox && (
            <p className="rounded-md bg-blue-50 px-3 py-2 text-xs text-blue-700">
              After creating, the box type will expand so you can add size capacities and spacer rules.
            </p>
          )}
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
