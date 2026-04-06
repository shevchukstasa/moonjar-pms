import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/Table';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { useSizes, useCreateSize, useUpdateSize, useDeleteSize } from '@/hooks/useSizes';
import { useQueryClient } from '@tanstack/react-query';
import type { SizeItem } from '@/api/sizes';
import { CsvImportDialog } from '@/components/admin/CsvImportDialog';
import { CSV_CONFIGS } from '@/config/csvImportConfigs';
import {
  ShapeDimensionEditor,
  SHAPE_DEFINITIONS,
  getShapeDefinition,
} from '@/components/shared/ShapeDimensionEditor';

interface SizeForm {
  name: string;
  width_mm: string;
  height_mm: string;
  thickness_mm: string;
  shape: string;
  shape_dimensions: Record<string, number>;
  calculated_area_cm2: number;
  is_custom: boolean;
}

const emptyForm: SizeForm = {
  name: '',
  width_mm: '',
  height_mm: '',
  thickness_mm: '',
  shape: 'rectangle',
  shape_dimensions: {},
  calculated_area_cm2: 0,
  is_custom: false,
};

export default function AdminSizesPage() {
  const navigate = useNavigate();
  const { data, isLoading } = useSizes();
  const createSize = useCreateSize();
  const updateSize = useUpdateSize();
  const deleteSize = useDeleteSize();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editItem, setEditItem] = useState<SizeItem | null>(null);
  const [form, setForm] = useState<SizeForm>(emptyForm);
  const [errorMsg, setErrorMsg] = useState('');
  const [csvOpen, setCsvOpen] = useState(false);
  const queryClient = useQueryClient();

  const items = data?.items ?? [];

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setEditItem(null);
    setForm(emptyForm);
    setErrorMsg('');
  }, []);

  const openCreate = useCallback(() => {
    setEditItem(null);
    setForm(emptyForm);
    setErrorMsg('');
    setDialogOpen(true);
  }, []);

  const openEdit = useCallback((item: SizeItem) => {
    setEditItem(item);
    // Reconstruct shape_dimensions from width_mm/height_mm if not stored separately
    const shape = item.shape || 'rectangle';
    const shapeDef = getShapeDefinition(shape);
    const dims: Record<string, number> = (item as unknown as Record<string, unknown>).shape_dimensions as Record<string, number> ?? {};
    // If no shape_dimensions stored, build from width/height (legacy sizes)
    if (Object.keys(dims).length === 0 && shapeDef) {
      if (shape === 'rectangle') {
        dims.width = item.width_mm / 10;
        dims.height = item.height_mm / 10;
      } else if (shape === 'square') {
        dims.side = item.width_mm / 10;
      } else if (shape === 'circle' || shape === 'semicircle') {
        dims.diameter = item.width_mm / 10;
      }
    }
    const area = shapeDef?.area(dims) ?? 0;
    setForm({
      name: item.name,
      width_mm: String(item.width_mm),
      height_mm: String(item.height_mm),
      thickness_mm: item.thickness_mm != null ? String(item.thickness_mm) : '',
      shape,
      shape_dimensions: dims,
      calculated_area_cm2: area ?? 0,
      is_custom: item.is_custom,
    });
    setErrorMsg('');
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    setErrorMsg('');
    const w = parseInt(form.width_mm);
    const h = parseInt(form.height_mm);
    const t = form.thickness_mm ? parseInt(form.thickness_mm) : undefined;

    if (!form.name.trim()) { setErrorMsg('Name is required'); return; }
    if (isNaN(w) || w <= 0) { setErrorMsg('Width (a) must be a positive number'); return; }
    if (isNaN(h) || h <= 0) { setErrorMsg('Height (b) must be a positive number'); return; }
    if (form.thickness_mm && (isNaN(t!) || t! <= 0)) { setErrorMsg('Thickness must be a positive number'); return; }

    const payload = {
      name: form.name.trim(),
      width_mm: w,
      height_mm: h,
      thickness_mm: t ?? null,
      shape: form.shape,
      shape_dimensions: Object.keys(form.shape_dimensions).length > 0 ? form.shape_dimensions : undefined,
      calculated_area_cm2: form.calculated_area_cm2 > 0 ? form.calculated_area_cm2 : undefined,
      is_custom: form.is_custom,
    };

    if (editItem) {
      updateSize.mutate(
        { id: editItem.id, data: payload },
        {
          onSuccess: closeDialog,
          onError: (err: unknown) => {
            const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Update failed';
            setErrorMsg(msg);
          },
        },
      );
    } else {
      createSize.mutate(payload, {
        onSuccess: closeDialog,
        onError: (err: unknown) => {
          const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Create failed';
          setErrorMsg(msg);
        },
      });
    }
  }, [form, editItem, createSize, updateSize, closeDialog]);

  const handleDelete = useCallback(() => {
    if (!deleteId) return;
    deleteSize.mutate(deleteId, {
      onSuccess: () => setDeleteId(null),
      onError: (err: unknown) => {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Delete failed';
        alert(msg);
        setDeleteId(null);
      },
    });
  }, [deleteId, deleteSize]);

  const saving = createSize.isPending || updateSize.isPending;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = useMemo(
    () => [
      { key: 'name', header: 'Name' },
      {
        key: 'width_mm',
        header: 'A (mm)',
        render: (s: SizeItem) => <span className="font-mono text-sm">{s.width_mm}</span>,
      },
      {
        key: 'height_mm',
        header: 'B (mm)',
        render: (s: SizeItem) => <span className="font-mono text-sm">{s.height_mm}</span>,
      },
      {
        key: 'thickness_mm',
        header: 'Thickness (mm)',
        render: (s: SizeItem) =>
          s.thickness_mm != null ? (
            <span className="font-mono text-sm">{s.thickness_mm}</span>
          ) : (
            <span className="text-gray-400">&mdash;</span>
          ),
      },
      {
        key: 'shape',
        header: 'Shape',
        render: (s: SizeItem) => {
          const def = s.shape ? getShapeDefinition(s.shape) : null;
          const label = def ? `${def.icon} ${def.label}` : s.shape || '—';
          return <Badge status="active" label={label} />;
        },
      },
      {
        key: 'is_custom',
        header: 'Custom',
        render: (s: SizeItem) =>
          s.is_custom ? (
            <Badge status="warning" label="Custom" />
          ) : (
            <span className="text-gray-400">Standard</span>
          ),
      },
      {
        key: 'glazing_board',
        header: 'Glazing Board (1 board)',
        render: (s: SizeItem) => {
          if (!s.glazing_board) return <span className="text-gray-300 text-xs">—</span>;
          const b = s.glazing_board;
          return (
            <div className="text-xs space-y-0.5">
              {b.is_custom_board ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800 border border-amber-200">
                  ⚠ {b.board_width_cm.toFixed(1)} cm wide
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 font-medium text-green-800 border border-green-200">
                  ✓ standard 20 cm
                </span>
              )}
              <div className="text-gray-500">
                {b.tiles_per_board} pcs · {b.area_per_board_m2.toFixed(4)} m²
              </div>
            </div>
          );
        },
      },
      {
        key: 'actions',
        header: '',
        render: (s: SizeItem) => (
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={() => openEdit(s)}>
              Edit
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-red-600"
              onClick={() => setDeleteId(s.id)}
            >
              Delete
            </Button>
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
          <h1 className="text-2xl font-bold text-gray-900">Sizes</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage tile &amp; stone sizes — dimensions, thickness, and shape
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>
            Back to Admin
          </Button>
          <Button variant="secondary" onClick={() => setCsvOpen(true)}>Import CSV</Button>
          <Button onClick={openCreate}>+ Add Size</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : items.length === 0 ? (
        <Card>
          <p className="py-8 text-center text-gray-400">No sizes found</p>
        </Card>
      ) : (
        <DataTable columns={columns} data={items as unknown as Record<string, unknown>[]} />
      )}

      {/* Create / Edit Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        title={editItem ? 'Edit Size' : 'Add Size'}
        className="w-full max-w-md"
      >
        <div className="space-y-4">
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. 10x10, 20x40"
            required
          />
          <div className="grid grid-cols-3 gap-3">
            <Input
              label="A — Width (mm)"
              type="number"
              value={form.width_mm}
              onChange={(e) => setForm({ ...form, width_mm: e.target.value })}
              placeholder="100"
              required
            />
            <Input
              label="B — Height (mm)"
              type="number"
              value={form.height_mm}
              onChange={(e) => setForm({ ...form, height_mm: e.target.value })}
              placeholder="100"
              required
            />
            <Input
              label="Thickness (mm)"
              type="number"
              value={form.thickness_mm}
              onChange={(e) => setForm({ ...form, thickness_mm: e.target.value })}
              placeholder="—"
            />
          </div>
          <ShapeDimensionEditor
            shape={form.shape}
            dimensions={form.shape_dimensions}
            onChange={(newShape, newDims, newArea) =>
              setForm({ ...form, shape: newShape, shape_dimensions: newDims, calculated_area_cm2: newArea })
            }
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_custom}
              onChange={(e) => setForm({ ...form, is_custom: e.target.checked })}
              className="rounded"
            />
            Custom size (non-standard)
          </label>

          {errorMsg && <p className="text-sm text-red-500">{errorMsg}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={saving}>
              {saving ? 'Saving...' : editItem ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      <CsvImportDialog open={csvOpen} onClose={() => setCsvOpen(false)} {...CSV_CONFIGS.sizes} onSuccess={() => queryClient.invalidateQueries({ queryKey: ['sizes'] })} />

      {/* Delete Confirmation */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Size">
        <p className="text-sm text-gray-600">
          Are you sure you want to delete this size? This will fail if the size is used in packaging
          rules.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete} disabled={deleteSize.isPending}>
            {deleteSize.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
