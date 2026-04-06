import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { packagingApi, type PackagingBoxType } from '@/api/packaging';
import { usePackagingBoxTypes, usePackagingSizes } from '@/hooks/usePackaging';
import { useMaterials } from '@/hooks/useMaterials';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { NumericInput } from '@/components/ui/NumericInput';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { CsvImportDialog } from '@/components/admin/CsvImportDialog';
import { CSV_CONFIGS } from '@/config/csvImportConfigs';

/* ── Row types ────────────────────────────────────────── */

interface CapRow {
  size_id: string;
  pieces_per_box: string;
  sqm_per_box: string;
}

interface SpacerRow {
  size_id: string;
  spacer_material_id: string;
  qty_per_box: string;
}

/* ── Component ─────────────────────────────────────────── */

export default function AdminPackagingPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  /* Data */
  const { data, isLoading, isError } = usePackagingBoxTypes();
  const items = data?.items ?? [];
  const { data: sizesData } = usePackagingSizes();
  const sizes = sizesData?.items ?? [];
  const { data: matsData } = useMaterials({ material_type: 'packaging', per_page: 200 });
  const packagingMaterials = matsData?.items ?? [];
  const { data: allMatsData } = useMaterials({ per_page: 500 });
  const allMaterials = allMatsData?.items ?? [];

  /* ── New box form state ─────────────────────────────── */
  const [showNewForm, setShowNewForm] = useState(false);
  const [newMaterialId, setNewMaterialId] = useState('');
  const [newNotes, setNewNotes] = useState('');
  const [newCapRows, setNewCapRows] = useState<CapRow[]>([{ size_id: '', pieces_per_box: '', sqm_per_box: '' }]);
  const [newSpacerRows, setNewSpacerRows] = useState<SpacerRow[]>([]);
  const [newError, setNewError] = useState('');
  const [newSaving, setNewSaving] = useState(false);

  /* ── Expanded existing box edit state ───────────────── */
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editCapRows, setEditCapRows] = useState<CapRow[]>([]);
  const [editSpacerRows, setEditSpacerRows] = useState<SpacerRow[]>([]);
  const [editError, setEditError] = useState('');

  /* Delete */
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [csvOpen, setCsvOpen] = useState(false);

  /* ── Mutations ──────────────────────────────────────── */

  const deleteMut = useMutation({
    mutationFn: (id: string) => packagingApi.remove(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['packaging-box-types'] }); setDeleteId(null); setExpandedId(null); },
  });

  const capMut = useMutation({
    mutationFn: ({ id, caps }: { id: string; caps: any[] }) => packagingApi.setCapacities(id, caps),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['packaging-box-types'] }); setEditError(''); },
    onError: (e: any) => setEditError(e?.response?.data?.detail ?? 'Failed to save capacities'),
  });

  const spacerMut = useMutation({
    mutationFn: ({ id, sp }: { id: string; sp: any[] }) => packagingApi.setSpacers(id, sp),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['packaging-box-types'] }); setEditError(''); },
    onError: (e: any) => setEditError(e?.response?.data?.detail ?? 'Failed to save spacers'),
  });

  /* ── New form handlers ──────────────────────────────── */

  const resetNewForm = useCallback(() => {
    setShowNewForm(false);
    setNewMaterialId('');
    setNewNotes('');
    setNewCapRows([{ size_id: '', pieces_per_box: '', sqm_per_box: '' }]);
    setNewSpacerRows([]);
    setNewError('');
    setNewSaving(false);
  }, []);

  const handleCreateAll = useCallback(async () => {
    if (!newMaterialId) { setNewError('Select a packaging material'); return; }
    const mat = packagingMaterials.find((m) => m.id === newMaterialId);
    const name = mat?.name ?? 'Box';
    const caps = newCapRows.filter((r) => r.size_id).map((r) => ({
      size_id: r.size_id,
      pieces_per_box: r.pieces_per_box ? parseInt(r.pieces_per_box) : undefined,
      sqm_per_box: r.sqm_per_box ? parseFloat(r.sqm_per_box) : undefined,
    }));
    if (caps.length === 0) { setNewError('Add at least one size with capacity'); return; }

    setNewSaving(true);
    setNewError('');
    try {
      // 1. Create box type
      const created = await packagingApi.create({ material_id: newMaterialId, name, notes: newNotes || undefined, is_active: true });
      const boxId = created.id;

      // 2. Set capacities
      await packagingApi.setCapacities(boxId, caps);

      // 3. Set spacers (if any)
      const spacers = newSpacerRows.filter((r) => r.size_id && r.spacer_material_id).map((r) => ({
        size_id: r.size_id,
        spacer_material_id: r.spacer_material_id,
        qty_per_box: parseInt(r.qty_per_box) || 1,
      }));
      if (spacers.length > 0) {
        await packagingApi.setSpacers(boxId, spacers);
      }

      qc.invalidateQueries({ queryKey: ['packaging-box-types'] });
      resetNewForm();
    } catch (e: any) {
      setNewError(e?.response?.data?.detail ?? 'Failed to create box type');
    } finally {
      setNewSaving(false);
    }
  }, [newMaterialId, newCapRows, newSpacerRows, newNotes, packagingMaterials, qc, resetNewForm]);

  /* ── Existing box expand/edit ───────────────────────── */

  const toggleExpand = useCallback((bt: PackagingBoxType) => {
    if (expandedId === bt.id) { setExpandedId(null); return; }
    setExpandedId(bt.id);
    setEditError('');
    setEditCapRows(
      bt.capacities.length > 0
        ? bt.capacities.map((c) => ({
            size_id: c.size_id,
            pieces_per_box: c.pieces_per_box != null ? String(c.pieces_per_box) : '',
            sqm_per_box: c.sqm_per_box != null ? String(c.sqm_per_box) : '',
          }))
        : [{ size_id: '', pieces_per_box: '', sqm_per_box: '' }]
    );
    setEditSpacerRows(
      bt.spacer_rules.map((sr) => ({
        size_id: sr.size_id,
        spacer_material_id: sr.spacer_material_id,
        qty_per_box: String(sr.qty_per_box),
      }))
    );
  }, [expandedId]);

  const saveExisting = useCallback(() => {
    if (!expandedId) return;
    const caps = editCapRows.filter((r) => r.size_id).map((r) => ({
      size_id: r.size_id,
      pieces_per_box: r.pieces_per_box ? parseInt(r.pieces_per_box) : undefined,
      sqm_per_box: r.sqm_per_box ? parseFloat(r.sqm_per_box) : undefined,
    }));
    const spacers = editSpacerRows.filter((r) => r.size_id && r.spacer_material_id).map((r) => ({
      size_id: r.size_id,
      spacer_material_id: r.spacer_material_id,
      qty_per_box: parseInt(r.qty_per_box) || 1,
    }));
    // Save both in parallel
    capMut.mutate({ id: expandedId, caps });
    spacerMut.mutate({ id: expandedId, sp: spacers });
  }, [expandedId, editCapRows, editSpacerRows, capMut, spacerMut]);

  const editSaving = capMut.isPending || spacerMut.isPending;

  /* ── Shared sub-components ──────────────────────────── */

  const renderCapacityTable = (
    rows: CapRow[],
    setRows: React.Dispatch<React.SetStateAction<CapRow[]>>,
  ) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800">Size Capacities *</h3>
        <Button size="sm" variant="secondary" onClick={() => {
          if (rows.length < 10) setRows((prev) => [...prev, { size_id: '', pieces_per_box: '', sqm_per_box: '' }]);
        }} disabled={rows.length >= 10}>+ Add Size</Button>
      </div>
      {/* Header */}
      <div className="flex items-end gap-2 text-xs font-medium text-gray-500 px-1">
        <div className="flex-1">Tile Size</div>
        <div className="w-28">Pieces / box</div>
        <div className="w-28">m{'\u00B2'} / box</div>
        <div className="w-8" />
      </div>
      {rows.map((row, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <div className="flex-1">
            <select
              value={row.size_id}
              onChange={(e) => setRows((prev) => prev.map((r, i) => i === idx ? { ...r, size_id: e.target.value } : r))}
              className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
            >
              <option value="">Select size...</option>
              {sizes.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.width_mm}{'\u00D7'}{s.height_mm}mm){s.is_custom ? ' — custom' : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="w-28">
            <NumericInput
              value={row.pieces_per_box}
              onChange={(e) => setRows((prev) => prev.map((r, i) => i === idx ? { ...r, pieces_per_box: e.target.value } : r))}
              placeholder="pcs"
            />
          </div>
          <div className="w-28">
            <NumericInput
              value={row.sqm_per_box}
              onChange={(e) => setRows((prev) => prev.map((r, i) => i === idx ? { ...r, sqm_per_box: e.target.value } : r))}
              placeholder="m\u00B2"
            />
          </div>
          <button
            onClick={() => setRows((prev) => prev.filter((_, i) => i !== idx))}
            className="flex h-8 w-8 items-center justify-center rounded text-gray-400 hover:bg-red-50 hover:text-red-600"
          >{'✕'}</button>
        </div>
      ))}
    </div>
  );

  const renderSpacerTable = (
    rows: SpacerRow[],
    setRows: React.Dispatch<React.SetStateAction<SpacerRow[]>>,
  ) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800">Spacer Rules</h3>
        <Button size="sm" variant="secondary" onClick={() => setRows((prev) => [...prev, { size_id: '', spacer_material_id: '', qty_per_box: '1' }])}>+ Add Spacer</Button>
      </div>
      {rows.length === 0 ? (
        <p className="text-xs text-gray-400 pl-1">No spacers needed? Skip this section.</p>
      ) : (
        <>
          <div className="flex items-end gap-2 text-xs font-medium text-gray-500 px-1">
            <div className="w-36">Tile Size</div>
            <div className="flex-1">Spacer Material</div>
            <div className="w-24">Qty / box</div>
            <div className="w-8" />
          </div>
          {rows.map((row, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <div className="w-36">
                <select
                  value={row.size_id}
                  onChange={(e) => setRows((prev) => prev.map((r, i) => i === idx ? { ...r, size_id: e.target.value } : r))}
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
                  onChange={(e) => setRows((prev) => prev.map((r, i) => i === idx ? { ...r, spacer_material_id: e.target.value } : r))}
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
                  onChange={(e) => setRows((prev) => prev.map((r, i) => i === idx ? { ...r, qty_per_box: e.target.value } : r))}
                  placeholder="qty"
                />
              </div>
              <button
                onClick={() => setRows((prev) => prev.filter((_, i) => i !== idx))}
                className="flex h-8 w-8 items-center justify-center rounded text-gray-400 hover:bg-red-50 hover:text-red-600"
              >{'✕'}</button>
            </div>
          ))}
        </>
      )}
    </div>
  );

  /* ── Render ─────────────────────────────────────────── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Packaging Rules</h1>
          <p className="mt-1 text-sm text-gray-500">Box types with tile size capacities and spacer requirements</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>Back to Admin</Button>
          <Button variant="secondary" onClick={() => setCsvOpen(true)}>Import CSV</Button>
          {!showNewForm && <Button onClick={() => setShowNewForm(true)}>+ Add Box Type</Button>}
        </div>
      </div>

      {/* ── NEW BOX TYPE FORM ───────────────────────────── */}
      {showNewForm && (
        <Card className="border-2 border-indigo-300 bg-indigo-50/30">
          <div className="p-5 space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">New Box Type</h2>
              <Button variant="secondary" size="sm" onClick={resetNewForm}>Cancel</Button>
            </div>

            {/* Material selector */}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">Packaging Material (box) *</label>
              <select
                value={newMaterialId}
                onChange={(e) => setNewMaterialId(e.target.value)}
                className="w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">Select material...</option>
                {packagingMaterials.map((m) => (
                  <option key={m.id} value={m.id}>{m.material_code} {m.name}</option>
                ))}
              </select>
            </div>

            {/* Capacities */}
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              {renderCapacityTable(newCapRows, setNewCapRows)}
            </div>

            {/* Spacers */}
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              {renderSpacerTable(newSpacerRows, setNewSpacerRows)}
            </div>

            {/* Notes */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Notes</label>
              <textarea
                value={newNotes}
                onChange={(e) => setNewNotes(e.target.value)}
                rows={2}
                className="w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="Optional notes..."
              />
            </div>

            {newError && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-600">{newError}</p>}

            <div className="flex gap-2">
              <Button onClick={handleCreateAll} disabled={newSaving}>
                {newSaving ? 'Saving…' : 'Save Box Type'}
              </Button>
              <Button variant="secondary" onClick={resetNewForm}>Cancel</Button>
            </div>
          </div>
        </Card>
      )}

      {/* ── EXISTING BOX TYPES ──────────────────────────── */}
      {isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-red-800">{'⚠'} Error loading packaging data</p>
        </div>
      ) : isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : items.length === 0 && !showNewForm ? (
        <Card>
          <div className="py-10 text-center">
            <p className="text-lg font-medium text-gray-500">No box types configured</p>
            <p className="mt-2 text-sm text-gray-400">
              Add a box type to configure which tile sizes fit and how many per box.
            </p>
            <Button className="mt-4" onClick={() => setShowNewForm(true)}>+ Add Box Type</Button>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {items.map((bt) => {
            const isExpanded = expandedId === bt.id;
            // Refresh from list
            const fresh = items.find((b) => b.id === bt.id) ?? bt;
            return (
              <Card key={bt.id} className="overflow-hidden">
                {/* Header (always visible) */}
                <div
                  onClick={() => toggleExpand(fresh)}
                  className="cursor-pointer p-4 transition-colors hover:bg-gray-50"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`text-lg transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}>
                        {'▶'}
                      </span>
                      <div>
                        <p className="font-semibold text-gray-900">
                          {bt.material_name ?? bt.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {bt.material_code ?? ''}{bt.notes ? ` — ${bt.notes}` : ''}
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

                  {/* Collapsed summary */}
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

                {/* Expanded edit panel */}
                {isExpanded && (
                  <div className="border-t border-gray-200 bg-gray-50 px-4 py-4 space-y-5">
                    {editError && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-600">{editError}</p>}

                    {/* Capacities */}
                    <div className="rounded-lg border border-gray-200 bg-white p-4">
                      {renderCapacityTable(editCapRows, setEditCapRows)}
                    </div>

                    {/* Spacers */}
                    <div className="rounded-lg border border-gray-200 bg-white p-4">
                      {renderSpacerTable(editSpacerRows, setEditSpacerRows)}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-between">
                      <Button
                        variant="secondary"
                        size="sm"
                        className="text-red-600 hover:bg-red-50"
                        onClick={(e) => { e.stopPropagation(); setDeleteId(bt.id); }}
                      >
                        Delete Box Type
                      </Button>
                      <Button onClick={saveExisting} disabled={editSaving}>
                        {editSaving ? 'Saving…' : 'Save Changes'}
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}

      <CsvImportDialog open={csvOpen} onClose={() => setCsvOpen(false)} {...CSV_CONFIGS.packaging} onSuccess={() => qc.invalidateQueries({ queryKey: ['packaging-box-types'] })} />

      {/* Delete dialog */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Box Type">
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Delete this box type and all its capacity/spacer rules? This cannot be undone.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button
              className="bg-red-600 hover:bg-red-700 focus:ring-red-500"
              onClick={() => deleteId && deleteMut.mutate(deleteId)}
              disabled={deleteMut.isPending}
            >
              {deleteMut.isPending ? 'Deleting…' : 'Delete'}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
