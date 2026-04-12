import { useEffect, useState } from 'react';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useUpdatePosition } from '@/hooks/usePositions';
import { useCollections, useFinishingTypes, useColors } from '@/hooks/useReferenceData';
import { useSizes } from '@/hooks/useSizes';
import {
  SHAPE_OPTIONS,
  APPLICATION_OPTIONS,
  EDGE_PROFILE_OPTIONS,
  PRIORITY_OPTIONS,
} from '@/types/forms';

const PRODUCT_TYPES = [
  { value: 'tile', label: 'Tile' },
  { value: 'countertop', label: 'Countertop' },
  { value: 'sink', label: 'Sink' },
  { value: '3d', label: '3D Product' },
  { value: 'custom', label: 'Custom' },
];

const PLACE_OF_APPLICATION = [
  { value: 'face', label: 'Face Only' },
  { value: 'face_edges_1', label: 'Face + 1 Edge' },
  { value: 'face_edges_2', label: 'Face + 2 Edges' },
  { value: 'face_edges_all', label: 'Face + All Edges' },
  { value: 'with_back', label: 'With Back' },
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface PositionEditDialogProps {
  open: boolean;
  onClose: () => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  position: Record<string, any> | null;
}

export function PositionEditDialog({ open, onClose, position }: PositionEditDialogProps) {
  const updatePosition = useUpdatePosition();
  const { data: collectionsData, isLoading: collectionsLoading } = useCollections();
  const { data: sizesData, isLoading: sizesLoading } = useSizes();
  const { data: finishingTypes, isLoading: finishingLoading } = useFinishingTypes();
  const { data: colorsData, isLoading: colorsLoading } = useColors();

  const [form, setForm] = useState({
    color: '',
    size: '',
    thickness_mm: 11,
    shape: 'rectangle',
    place_of_application: 'face',
    application: '',
    collection: '',
    finishing: '',
    product_type: 'tile',
    quantity: 1,
    edge_profile: 'straight',
    edge_profile_sides: 1,
    quantity_unit: 'pcs',
    priority_order: 0,
    color_2: '',
    description: '',
    is_additional_item: false,
  });
  const [submitError, setSubmitError] = useState('');

  // Pre-fill form when position changes
  useEffect(() => {
    if (position) {
      setForm({
        color: position.color || '',
        size: position.size || '',
        thickness_mm: position.thickness_mm || 11,
        shape: position.shape || 'rectangle',
        place_of_application: position.place_of_application || 'face',
        application: position.application || '',
        collection: position.collection || '',
        finishing: position.finishing || '',
        product_type: position.product_type || 'tile',
        quantity: position.quantity || 1,
        quantity_unit: position.quantity_unit || 'pcs',
        edge_profile: position.edge_profile || 'straight',
        edge_profile_sides: position.edge_profile_sides || 1,
        priority_order: position.priority_order || 0,
        color_2: position.color_2 || '',
        description: position.description || '',
        is_additional_item: position.is_additional_item || false,
      });
      setSubmitError('');
    }
  }, [position]);

  const handleChange = (field: string, value: string | number) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    if (!position?.id) return;
    setSubmitError('');
    try {
      await updatePosition.mutateAsync({
        id: position.id,
        data: {
          color: form.color,
          size: form.size,
          thickness_mm: Number(form.thickness_mm),
          shape: form.shape,
          place_of_application: form.place_of_application,
          application: form.application,
          collection: form.collection || null,
          finishing: form.finishing || null,
          product_type: form.product_type,
          quantity: Number(form.quantity),
          quantity_unit: form.quantity_unit,
          edge_profile: form.edge_profile,
          edge_profile_sides: form.edge_profile !== 'straight' ? Number(form.edge_profile_sides) : null,
          priority_order: Number(form.priority_order),
          color_2: form.color_2 || null,
          description: form.description || null,
        },
      });
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setSubmitError(resp?.detail || 'Failed to update position');
    }
  };

  const showColor2 = ['Stencil', 'Silkscreen'].includes(form.application);
  const showEdgeSides = form.edge_profile !== 'straight';

  // Build collections dropdown
  const collectionOptions = [
    { value: '', label: 'None' },
    ...(collectionsData || []).map((c) => ({ value: c.value, label: c.label })),
  ];

  // Build sizes dropdown
  const sizeOptions = [
    { value: '', label: 'Select size...' },
    ...(sizesData?.items || []).map((s) => ({ value: s.name, label: s.name })),
  ];

  // Priority mapping: priority_order number -> label
  const priorityToOrder: Record<string, number> = { normal: 0, urgent: 50, critical: 100 };
  const orderToPriority = (val: number): string => {
    if (val >= 100) return 'critical';
    if (val >= 50) return 'urgent';
    return 'normal';
  };

  return (
    <Dialog open={open} onClose={onClose} title={`Edit Position ${position?.position_label || ''}`} className="w-full max-w-2xl">
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          {/* Color — dropdown from DB */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Color {colorsLoading && <Spinner className="ml-1 inline h-3 w-3" />}
            </label>
            <select
              value={form.color}
              onChange={(e) => handleChange('color', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">Select color...</option>
              {(colorsData || []).map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
              {form.color && !(colorsData || []).find((c) => c.value === form.color) && (
                <option value={form.color}>{form.color} (custom)</option>
              )}
            </select>
          </div>

          {/* Size dropdown */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Size {sizesLoading && <Spinner className="ml-1 inline h-3 w-3" />}
            </label>
            <select
              value={form.size}
              onChange={(e) => handleChange('size', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              {sizeOptions.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
              {/* Keep current value if not in list */}
              {form.size && !sizeOptions.find((o) => o.value === form.size) && (
                <option value={form.size}>{form.size}</option>
              )}
            </select>
          </div>

          {/* Thickness */}
          <Input
            label="Thickness (mm)"
            type="number"
            step="0.1"
            value={String(form.thickness_mm)}
            onChange={(e) => handleChange('thickness_mm', Number(e.target.value))}
          />

          {/* Shape */}
          <Select
            label="Shape"
            value={form.shape}
            onChange={(e) => handleChange('shape', e.target.value)}
            options={SHAPE_OPTIONS.map((s) => ({ value: s.value, label: s.label }))}
          />

          {/* Place of Application */}
          <Select
            label="Glaze Place"
            value={form.place_of_application}
            onChange={(e) => handleChange('place_of_application', e.target.value)}
            options={PLACE_OF_APPLICATION}
          />

          {/* Application */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Application</label>
            <select
              value={form.application}
              onChange={(e) => handleChange('application', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">None</option>
              {APPLICATION_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
              {form.application && !APPLICATION_OPTIONS.find((o) => o.value === form.application) && (
                <option value={form.application}>{form.application}</option>
              )}
            </select>
          </div>

          {/* Collection */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Collection {collectionsLoading && <Spinner className="ml-1 inline h-3 w-3" />}
            </label>
            <select
              value={form.collection}
              onChange={(e) => handleChange('collection', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              {collectionOptions.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
              {form.collection && !collectionOptions.find((o) => o.value === form.collection) && (
                <option value={form.collection}>{form.collection}</option>
              )}
            </select>
          </div>

          {/* Finishing — dropdown from DB */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Finishing {finishingLoading && <Spinner className="ml-1 inline h-3 w-3" />}
            </label>
            <select
              value={form.finishing}
              onChange={(e) => handleChange('finishing', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">None</option>
              {(finishingTypes || []).map((f) => (
                <option key={f.id} value={f.name}>{f.name}</option>
              ))}
              {form.finishing && !(finishingTypes || []).find((f) => f.name === form.finishing) && (
                <option value={form.finishing}>{form.finishing} (custom)</option>
              )}
            </select>
          </div>

          {/* Product Type */}
          <Select
            label="Product Type"
            value={form.product_type}
            onChange={(e) => handleChange('product_type', e.target.value)}
            options={PRODUCT_TYPES}
          />

          {/* Quantity + Unit toggle */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Quantity ({form.quantity_unit === 'sqm' ? 'm²' : 'pcs'})
            </label>
            <div className="relative">
              <input
                type="number"
                className="w-full rounded-md border border-gray-300 px-3 py-2 pr-16 text-sm focus:border-blue-500 focus:outline-none"
                value={String(form.quantity)}
                onChange={(e) => handleChange('quantity', Number(e.target.value))}
              />
              <div className="absolute inset-y-0 right-0 flex items-center pr-1">
                <button
                  type="button"
                  className={`px-2 py-1 text-xs font-medium rounded-l ${form.quantity_unit !== 'sqm' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-500'}`}
                  onClick={() => handleChange('quantity_unit', 'pcs')}
                >pcs</button>
                <button
                  type="button"
                  className={`px-2 py-1 text-xs font-medium rounded-r ${form.quantity_unit === 'sqm' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-500'}`}
                  onClick={() => handleChange('quantity_unit', 'sqm')}
                >m²</button>
              </div>
            </div>
          </div>

          {/* Edge Profile */}
          <Select
            label="Edge Profile"
            value={form.edge_profile}
            onChange={(e) => handleChange('edge_profile', e.target.value)}
            options={EDGE_PROFILE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
          />

          {/* Edge Sides — only when edge != straight */}
          {showEdgeSides && (
            <Input
              label="Edge Sides (1-4)"
              type="number"
              min={1}
              max={4}
              value={String(form.edge_profile_sides)}
              onChange={(e) => handleChange('edge_profile_sides', Number(e.target.value))}
            />
          )}

          {/* Priority */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Priority</label>
            <select
              value={orderToPriority(form.priority_order)}
              onChange={(e) => handleChange('priority_order', priorityToOrder[e.target.value] ?? 0)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              {PRIORITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Color 2 — only for Stencil/Silkscreen */}
          {showColor2 && (
            <Input
              label="Color 2"
              value={form.color_2}
              onChange={(e) => handleChange('color_2', e.target.value)}
              placeholder="Second color"
            />
          )}
        </div>

        {/* Description */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => handleChange('description', e.target.value)}
            placeholder="Position description / notes"
            rows={2}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Additional item checkbox */}
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.is_additional_item}
            onChange={(e) => handleChange('is_additional_item', e.target.checked as unknown as string)}
            className="rounded border-gray-300"
          />
          Additional Service (Color Matching, Silkscreen line, etc.)
        </label>

        {submitError && <p className="text-sm text-red-500">{submitError}</p>}

        <div className="flex justify-end gap-3 border-t pt-4">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={updatePosition.isPending}>
            {updatePosition.isPending ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
