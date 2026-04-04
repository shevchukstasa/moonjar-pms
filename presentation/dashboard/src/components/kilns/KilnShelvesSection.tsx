import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { Dialog } from '@/components/ui/Dialog';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import {
  kilnShelvesApi,
  SHELF_MATERIALS,
  type KilnShelfItem,
  type KilnShelfCreate,
} from '@/api/tpsDashboard';
import type { KilnItem } from '@/hooks/useKilns';

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  damaged: 'bg-yellow-100 text-yellow-700',
  written_off: 'bg-red-100 text-red-700',
};

const MATERIAL_LABELS: Record<string, string> = Object.fromEntries(
  SHELF_MATERIALS.map((m) => [m.value, m.label]),
);

function cyclePercent(shelf: KilnShelfItem): number | null {
  if (!shelf.max_firing_cycles || shelf.max_firing_cycles === 0) return null;
  return Math.round((shelf.firing_cycles_count / shelf.max_firing_cycles) * 100);
}

function CycleBar({ shelf }: { shelf: KilnShelfItem }) {
  const pct = cyclePercent(shelf);
  if (pct === null) return <span className="text-xs text-gray-400">{shelf.firing_cycles_count} cycles</span>;
  const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-green-500';
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-200">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs text-gray-500">
        {shelf.firing_cycles_count}/{shelf.max_firing_cycles}
      </span>
    </div>
  );
}

/* ────── Main Section ────── */

export function KilnShelvesSection({
  factoryId,
  kilns,
}: {
  factoryId: string;
  kilns: KilnItem[];
}) {
  const qc = useQueryClient();
  const [showWrittenOff, setShowWrittenOff] = useState(false);
  const [filterKilnId, setFilterKilnId] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [writeOffShelf, setWriteOffShelf] = useState<KilnShelfItem | null>(null);
  const [editShelf, setEditShelf] = useState<KilnShelfItem | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['kiln-shelves', factoryId, showWrittenOff],
    queryFn: () => kilnShelvesApi.list(factoryId, undefined, showWrittenOff),
    enabled: !!factoryId,
  });

  const shelves = useMemo(() => {
    const items = data?.items || [];
    if (!filterKilnId) return items;
    return items.filter((s) => s.resource_id === filterKilnId);
  }, [data, filterKilnId]);

  // Group by kiln
  const kilnMap = useMemo(() => {
    const map = new Map<string, string>();
    kilns.forEach((k) => map.set(k.id, k.name));
    return map;
  }, [kilns]);

  const grouped = useMemo(() => {
    const groups = new Map<string, KilnShelfItem[]>();
    shelves.forEach((s) => {
      const arr = groups.get(s.resource_id) || [];
      arr.push(s);
      groups.set(s.resource_id, arr);
    });
    return groups;
  }, [shelves]);

  const kilnOptions = [
    { value: '', label: 'All Kilns' },
    ...kilns.map((k) => ({ value: k.id, label: k.name })),
  ];

  // Stats
  const totalActive = shelves.filter((s) => s.status === 'active').length;
  const totalArea = shelves
    .filter((s) => s.status === 'active')
    .reduce((sum, s) => sum + (s.area_sqm || 0), 0);
  const nearEnd = shelves.filter((s) => {
    const p = cyclePercent(s);
    return p !== null && p >= 80 && s.status === 'active';
  }).length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Kiln Shelves</h2>
          <p className="text-sm text-gray-500">
            {totalActive} active shelves &middot; {totalArea.toFixed(2)} m&sup2; total area
            {nearEnd > 0 && (
              <span className="ml-2 text-amber-600 font-medium">
                {nearEnd} nearing end-of-life
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-40">
            <Select
              options={kilnOptions}
              value={filterKilnId}
              onChange={(e) => setFilterKilnId(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-1.5 text-xs text-gray-500">
            <input
              type="checkbox"
              checked={showWrittenOff}
              onChange={(e) => setShowWrittenOff(e.target.checked)}
              className="rounded"
            />
            Show written-off
          </label>
          <Button size="sm" onClick={() => setCreateOpen(true)} disabled={kilns.length === 0}>
            + Add Shelf
          </Button>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner className="h-6 w-6" /></div>
      ) : shelves.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
          <p className="text-gray-400">No kiln shelves registered</p>
          <p className="mt-1 text-xs text-gray-400">Add shelves to track their lifecycle and usage</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Array.from(grouped.entries()).map(([kilnId, items]) => (
            <KilnShelfGroup
              key={kilnId}
              kilnName={kilnMap.get(kilnId) || 'Unknown Kiln'}
              shelves={items}
              onWriteOff={setWriteOffShelf}
              onEdit={setEditShelf}
              onIncrementCycles={(shelf) => {
                kilnShelvesApi.incrementCycles(shelf.id).then(() => {
                  qc.invalidateQueries({ queryKey: ['kiln-shelves'] });
                });
              }}
            />
          ))}
        </div>
      )}

      {/* Dialogs */}
      <CreateShelfDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        factoryId={factoryId}
        kilns={kilns}
      />
      <WriteOffDialog
        shelf={writeOffShelf}
        onClose={() => setWriteOffShelf(null)}
      />
      <EditShelfDialog
        shelf={editShelf}
        onClose={() => setEditShelf(null)}
        kilns={kilns}
      />
    </div>
  );
}

/* ────── Shelf Group (per kiln) ────── */

function KilnShelfGroup({
  kilnName,
  shelves,
  onWriteOff,
  onEdit,
  onIncrementCycles,
}: {
  kilnName: string;
  shelves: KilnShelfItem[];
  onWriteOff: (s: KilnShelfItem) => void;
  onEdit: (s: KilnShelfItem) => void;
  onIncrementCycles: (s: KilnShelfItem) => void;
}) {
  const active = shelves.filter((s) => s.status !== 'written_off');
  const writtenOff = shelves.filter((s) => s.status === 'written_off');
  const totalArea = active.reduce((sum, s) => sum + (s.area_sqm || 0), 0);

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-800">{kilnName}</span>
          <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
            {active.length} shelves &middot; {totalArea.toFixed(2)} m&sup2;
          </span>
        </div>
      </div>
      <div className="divide-y divide-gray-50">
        {shelves.map((shelf) => (
          <ShelfRow
            key={shelf.id}
            shelf={shelf}
            onWriteOff={() => onWriteOff(shelf)}
            onEdit={() => onEdit(shelf)}
            onIncrementCycles={() => onIncrementCycles(shelf)}
          />
        ))}
      </div>
      {writtenOff.length > 0 && (
        <div className="border-t border-gray-100 px-4 py-1.5 text-xs text-gray-400">
          {writtenOff.length} written-off shelf(s)
        </div>
      )}
    </div>
  );
}

/* ────── Single Shelf Row ────── */

function ShelfRow({
  shelf,
  onWriteOff,
  onEdit,
  onIncrementCycles,
}: {
  shelf: KilnShelfItem;
  onWriteOff: () => void;
  onEdit: () => void;
  onIncrementCycles: () => void;
}) {
  const isWrittenOff = shelf.status === 'written_off';

  return (
    <div
      className={`flex items-center justify-between px-4 py-2.5 transition-colors hover:bg-gray-50 ${
        isWrittenOff ? 'opacity-50' : ''
      }`}
    >
      <div className="flex items-center gap-4">
        {/* Name + material */}
        <div className="min-w-[140px]">
          <div className="text-sm font-medium text-gray-800">{shelf.name}</div>
          <div className="text-xs text-gray-400">
            {MATERIAL_LABELS[shelf.material] || shelf.material}
          </div>
        </div>

        {/* Dimensions */}
        <div className="text-sm text-gray-600">
          <span className="font-mono">{shelf.length_cm} &times; {shelf.width_cm}</span>
          <span className="text-xs text-gray-400 ml-0.5">cm</span>
          <span className="mx-1 text-gray-300">|</span>
          <span className="text-xs">{shelf.thickness_mm}mm</span>
        </div>

        {/* Area */}
        <div className="text-sm">
          <span className="font-medium text-gray-700">{shelf.area_sqm?.toFixed(4)}</span>
          <span className="text-xs text-gray-400 ml-0.5">m&sup2;</span>
        </div>

        {/* Status */}
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[shelf.status] || 'bg-gray-100 text-gray-600'}`}>
          {shelf.status}
        </span>

        {/* Cycles */}
        <CycleBar shelf={shelf} />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {!isWrittenOff && (
          <>
            <button
              onClick={onIncrementCycles}
              className="rounded p-1 text-xs text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              title="+1 firing cycle"
            >
              +1
            </button>
            <button
              onClick={onEdit}
              className="rounded p-1 text-xs text-blue-500 hover:bg-blue-50"
              title="Edit"
            >
              Edit
            </button>
            <button
              onClick={onWriteOff}
              className="rounded p-1 text-xs text-red-500 hover:bg-red-50"
              title="Write off"
            >
              Write Off
            </button>
          </>
        )}
        {isWrittenOff && shelf.write_off_reason && (
          <span className="text-xs text-gray-400 italic max-w-[200px] truncate" title={shelf.write_off_reason}>
            {shelf.write_off_reason}
          </span>
        )}
        {isWrittenOff && shelf.write_off_photo_url && (
          <a
            href={shelf.write_off_photo_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-500 hover:underline"
          >
            Photo
          </a>
        )}
      </div>
    </div>
  );
}

/* ────── Create Dialog ────── */

function CreateShelfDialog({
  open,
  onClose,
  factoryId,
  kilns,
}: {
  open: boolean;
  onClose: () => void;
  factoryId: string;
  kilns: KilnItem[];
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<KilnShelfCreate>>({
    factory_id: factoryId,
    material: 'silicon_carbide',
    thickness_mm: 15,
    max_firing_cycles: 200,
  });
  const [error, setError] = useState('');

  // Auto-update max_firing_cycles when material changes
  const handleMaterialChange = (mat: string) => {
    const defaults = SHELF_MATERIALS.find((m) => m.value === mat);
    setForm((f) => ({
      ...f,
      material: mat,
      max_firing_cycles: defaults?.defaultCycles ?? 100,
    }));
  };

  const createMut = useMutation({
    mutationFn: (payload: KilnShelfCreate) => kilnShelvesApi.create(payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['kiln-shelves'] });
      setForm({ factory_id: factoryId, material: 'silicon_carbide', thickness_mm: 15, max_firing_cycles: 200 });
      setError('');
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.detail || 'Failed to create shelf'),
  });

  const handleSubmit = () => {
    if (!form.resource_id) { setError('Select a kiln'); return; }
    if (!form.length_cm || form.length_cm <= 0) { setError('Enter valid length'); return; }
    if (!form.width_cm || form.width_cm <= 0) { setError('Enter valid width'); return; }
    createMut.mutate({
      resource_id: form.resource_id,
      factory_id: factoryId,
      name: form.name!.trim(),
      length_cm: form.length_cm!,
      width_cm: form.width_cm!,
      thickness_mm: form.thickness_mm,
      material: form.material,
      purchase_date: form.purchase_date,
      purchase_cost: form.purchase_cost,
      max_firing_cycles: form.max_firing_cycles,
      condition_notes: form.condition_notes,
    });
  };

  const kilnOptions = [
    { value: '', label: 'Select kiln...' },
    ...kilns.map((k) => ({ value: k.id, label: k.name })),
  ];

  return (
    <Dialog open={open} onClose={onClose} title="Add Kiln Shelf" className="w-[480px]">
      <div className="space-y-3">
        <Select
          label="Kiln"
          options={kilnOptions}
          value={form.resource_id || ''}
          onChange={(e) => setForm({ ...form, resource_id: e.target.value })}
        />
        <Input
          label="Shelf Name (auto-generated if empty)"
          placeholder="Auto: SiC-KilnName-001"
          value={form.name || ''}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <div className="grid grid-cols-3 gap-3">
          <Input
            label="Length (cm)"
            type="number"
            step="0.1"
            value={form.length_cm ?? ''}
            onChange={(e) => setForm({ ...form, length_cm: parseFloat(e.target.value) || undefined })}
          />
          <Input
            label="Width (cm)"
            type="number"
            step="0.1"
            value={form.width_cm ?? ''}
            onChange={(e) => setForm({ ...form, width_cm: parseFloat(e.target.value) || undefined })}
          />
          <Input
            label="Thickness (mm)"
            type="number"
            step="0.1"
            value={form.thickness_mm ?? 15}
            onChange={(e) => setForm({ ...form, thickness_mm: parseFloat(e.target.value) || 15 })}
          />
        </div>
        <Select
          label="Material"
          options={SHELF_MATERIALS}
          value={form.material || 'silicon_carbide'}
          onChange={(e) => handleMaterialChange(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Purchase Date"
            type="date"
            value={form.purchase_date || ''}
            onChange={(e) => setForm({ ...form, purchase_date: e.target.value })}
          />
          <Input
            label="Purchase Cost"
            type="number"
            step="0.01"
            placeholder="IDR"
            value={form.purchase_cost ?? ''}
            onChange={(e) => setForm({ ...form, purchase_cost: parseFloat(e.target.value) || undefined })}
          />
        </div>
        <Input
          label="Max Firing Cycles"
          type="number"
          placeholder="e.g. 200"
          value={form.max_firing_cycles ?? ''}
          onChange={(e) => setForm({ ...form, max_firing_cycles: parseInt(e.target.value) || undefined })}
        />
        <Input
          label="Notes"
          placeholder="Condition notes..."
          value={form.condition_notes || ''}
          onChange={(e) => setForm({ ...form, condition_notes: e.target.value })}
        />

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" onClick={handleSubmit} disabled={createMut.isPending}>
            {createMut.isPending ? 'Creating...' : 'Add Shelf'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

/* ────── Write Off Dialog ────── */

function WriteOffDialog({
  shelf,
  onClose,
}: {
  shelf: KilnShelfItem | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [reason, setReason] = useState('');
  const [photoUrl, setPhotoUrl] = useState('');
  const [result, setResult] = useState<string | null>(null);

  const writeOffMut = useMutation({
    mutationFn: () => kilnShelvesApi.writeOff(shelf!.id, reason, photoUrl || undefined),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['kiln-shelves'] });
      setResult(`Shelf written off. ${data.remaining_shelves} shelves remaining for this kiln.`);
      setTimeout(() => {
        setReason('');
        setPhotoUrl('');
        setResult(null);
        onClose();
      }, 2000);
    },
  });

  if (!shelf) return null;

  return (
    <Dialog open={!!shelf} onClose={onClose} title="Write Off Shelf" className="w-[420px]">
      <div className="space-y-3">
        <div className="rounded-lg bg-red-50 p-3">
          <p className="text-sm font-medium text-red-800">{shelf.name}</p>
          <p className="text-xs text-red-600">
            {shelf.length_cm} &times; {shelf.width_cm} cm &middot; {shelf.firing_cycles_count} firing cycles
          </p>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Reason *</label>
          <textarea
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            rows={3}
            placeholder="Describe why this shelf is being written off..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>

        <Input
          label="Photo URL"
          placeholder="https://... (link to damage photo)"
          value={photoUrl}
          onChange={(e) => setPhotoUrl(e.target.value)}
        />

        {result && (
          <div className="rounded-lg bg-green-50 p-3 text-sm text-green-800">{result}</div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button
            size="sm"
            className="bg-red-600 hover:bg-red-700 text-white"
            onClick={() => writeOffMut.mutate()}
            disabled={!reason.trim() || writeOffMut.isPending}
          >
            {writeOffMut.isPending ? 'Writing off...' : 'Confirm Write Off'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

/* ────── Edit Dialog ────── */

function EditShelfDialog({
  shelf,
  onClose,
  kilns,
}: {
  shelf: KilnShelfItem | null;
  onClose: () => void;
  kilns: KilnItem[];
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Record<string, any>>({});

  // Sync form when shelf changes
  useEffect(() => {
    if (shelf) {
      setForm({
        name: shelf.name,
        resource_id: shelf.resource_id,
        length_cm: shelf.length_cm,
        width_cm: shelf.width_cm,
        thickness_mm: shelf.thickness_mm,
        material: shelf.material,
        max_firing_cycles: shelf.max_firing_cycles,
        condition_notes: shelf.condition_notes || '',
        status: shelf.status,
      });
    }
  }, [shelf?.id]);

  const updateMut = useMutation({
    mutationFn: (payload: Record<string, any>) => kilnShelvesApi.update(shelf!.id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kiln-shelves'] });
      onClose();
    },
  });

  if (!shelf) return null;

  const kilnOptions = kilns.map((k) => ({ value: k.id, label: k.name }));

  return (
    <Dialog open={!!shelf} onClose={onClose} title="Edit Shelf" className="w-[440px]">
      <div className="space-y-3">
        <Select
          label="Assigned Kiln (move between kilns)"
          options={kilnOptions}
          value={form.resource_id || shelf.resource_id}
          onChange={(e) => setForm({ ...form, resource_id: e.target.value })}
        />
        <Input
          label="Name"
          value={form.name || ''}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <div className="grid grid-cols-3 gap-3">
          <Input
            label="Length (cm)"
            type="number"
            step="0.1"
            value={form.length_cm ?? ''}
            onChange={(e) => setForm({ ...form, length_cm: parseFloat(e.target.value) })}
          />
          <Input
            label="Width (cm)"
            type="number"
            step="0.1"
            value={form.width_cm ?? ''}
            onChange={(e) => setForm({ ...form, width_cm: parseFloat(e.target.value) })}
          />
          <Input
            label="Thickness (mm)"
            type="number"
            step="0.1"
            value={form.thickness_mm ?? ''}
            onChange={(e) => setForm({ ...form, thickness_mm: parseFloat(e.target.value) })}
          />
        </div>
        <Select
          label="Material"
          options={SHELF_MATERIALS}
          value={form.material || 'silicon_carbide'}
          onChange={(e) => setForm({ ...form, material: e.target.value })}
        />
        <Select
          label="Status"
          options={[
            { value: 'active', label: 'Active' },
            { value: 'damaged', label: 'Damaged' },
          ]}
          value={form.status || 'active'}
          onChange={(e) => setForm({ ...form, status: e.target.value })}
        />
        <Input
          label="Max Firing Cycles"
          type="number"
          value={form.max_firing_cycles ?? ''}
          onChange={(e) => setForm({ ...form, max_firing_cycles: parseInt(e.target.value) || null })}
        />
        <Input
          label="Notes"
          value={form.condition_notes || ''}
          onChange={(e) => setForm({ ...form, condition_notes: e.target.value })}
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" onClick={() => updateMut.mutate(form)} disabled={updateMut.isPending}>
            {updateMut.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
