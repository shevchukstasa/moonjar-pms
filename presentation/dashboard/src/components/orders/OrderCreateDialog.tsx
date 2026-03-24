import { useState, useMemo } from 'react';
import { useForm, useFieldArray, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import {
  orderCreateSchema,
  type OrderCreateFormData,
  SHAPE_OPTIONS,
  BOWL_SHAPE_OPTIONS,
  APPLICATION_OPTIONS,
  EDGE_PROFILE_OPTIONS,
  PRIORITY_OPTIONS,
} from '@/types/forms';
import { useCreateOrder } from '@/hooks/useOrders';
import { useFactories } from '@/hooks/useFactories';
import { useCollections } from '@/hooks/useReferenceData';
import { useSizes } from '@/hooks/useSizes';

const PRODUCT_TYPES = [
  { value: 'tile', label: 'Tile' },
  { value: 'table_top', label: 'Table Top' },
  { value: 'countertop', label: 'Countertop' },
  { value: 'sink', label: 'Sink' },
  { value: '3d', label: '3D' },
];

const PLACE_OF_APPLICATION = [
  { value: 'face', label: 'Face Only' },
  { value: 'face_edges_1', label: 'Face + 1 Edge' },
  { value: 'face_edges_2', label: 'Face + 2 Edges' },
  { value: 'face_edges_all', label: 'Face + All Edges' },
  { value: 'with_back', label: 'With Back' },
];

const DEFAULT_ITEM = {
  color: '',
  size: '',
  application: '',
  finishing: '',
  collection: '',
  thickness_mm: null,
  place_of_application: 'face',
  quantity_pcs: 1,
  quantity_unit: 'pcs',
  product_type: 'tile',
  shape: 'rectangle',
  length_cm: null,
  width_cm: null,
  depth_cm: null,
  bowl_shape: '',
  edge_profile: 'straight',
  edge_profile_sides: null,
  priority: 'normal',
  color_2: '',
};

interface Props {
  open: boolean;
  onClose: () => void;
}

export function OrderCreateDialog({ open, onClose }: Props) {
  const createOrder = useCreateOrder();
  const { data: factoriesData } = useFactories();
  const { data: collectionsData, isLoading: collectionsLoading } = useCollections();
  const { data: sizesData, isLoading: sizesLoading } = useSizes();
  const [submitError, setSubmitError] = useState('');

  const factoryOptions = useMemo(() => {
    const opts = [{ value: '', label: 'Select factory...' }];
    for (const f of factoriesData?.items || []) {
      opts.push({ value: f.id, label: f.name });
    }
    return opts;
  }, [factoriesData]);

  const collectionOptions = useMemo(() => {
    const opts = [{ value: '', label: 'None' }];
    for (const c of collectionsData || []) {
      opts.push({ value: c.value, label: c.label });
    }
    return opts;
  }, [collectionsData]);

  const sizeOptions = useMemo(() => {
    const opts = [{ value: '', label: 'Select size...' }];
    for (const s of sizesData?.items || []) {
      opts.push({ value: s.name, label: s.name });
    }
    return opts;
  }, [sizesData]);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<OrderCreateFormData>({
    resolver: zodResolver(orderCreateSchema),
    defaultValues: {
      order_number: '',
      client: '',
      factory_id: '',
      final_deadline: '',
      notes: '',
      mandatory_qc: false,
      items: [{ ...DEFAULT_ITEM }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'items' });
  const watchedItems = useWatch({ control, name: 'items' });

  const onSubmit = async (data: OrderCreateFormData) => {
    setSubmitError('');
    try {
      // Strip empty optional fields so backend gets null instead of ""
      const payload: Record<string, unknown> = { ...data };
      if (!payload.final_deadline) delete payload.final_deadline;
      if (!payload.notes) delete payload.notes;
      await createOrder.mutateAsync(payload);
      reset();
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: unknown } } })?.response?.data;
      let msg = 'Failed to create order';
      if (resp?.detail) {
        if (typeof resp.detail === 'string') {
          msg = resp.detail;
        } else if (Array.isArray(resp.detail)) {
          msg = resp.detail.map((e: { msg?: string; loc?: string[] }) => e.msg || JSON.stringify(e)).join('; ');
        }
      }
      setSubmitError(msg);
    }
  };

  const handleClose = () => {
    reset();
    setSubmitError('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Create Order" className="w-full max-w-3xl">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
        {/* Order info */}
        <div className="grid grid-cols-2 gap-4">
          <Input label="Order Number" {...register('order_number')} error={errors.order_number?.message} placeholder="M-001" />
          <Input label="Client" {...register('client')} error={errors.client?.message} placeholder="Client name" />
          <Select label="Factory" {...register('factory_id')} error={errors.factory_id?.message} options={factoryOptions} />
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Deadline</label>
            <input type="date" {...register('final_deadline')} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
          </div>
        </div>

        <Input label="Notes" {...register('notes')} placeholder="Optional notes" />

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register('mandatory_qc')} className="rounded border-gray-300" />
          Mandatory Quality Check
        </label>

        {/* Items */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">Items</h3>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => append({ ...DEFAULT_ITEM })}
            >
              + Add Item
            </Button>
          </div>
          {errors.items?.root?.message && (
            <p className="mb-2 text-xs text-red-500">{errors.items.root.message}</p>
          )}
          <div className="space-y-3">
            {fields.map((field, idx) => {
              const currentApp = watchedItems?.[idx]?.application || '';
              const showColor2 = ['Stencil', 'Silkscreen'].includes(currentApp);
              const currentEdge = watchedItems?.[idx]?.edge_profile || 'straight';
              const showEdgeSides = currentEdge !== 'straight';

              return (
                <div key={field.id} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-500">Item {idx + 1}</span>
                    {fields.length > 1 && (
                      <button type="button" onClick={() => remove(idx)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    {/* Color — text input (colors are free-form glaze names) */}
                    <Input label="Color" {...register(`items.${idx}.color`)} error={errors.items?.[idx]?.color?.message} placeholder="Moss Glaze" />

                    {/* Size — dropdown from /api/sizes */}
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Size {sizesLoading && <Spinner className="ml-1 inline h-3 w-3" />}
                      </label>
                      <select
                        {...register(`items.${idx}.size`)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                      >
                        {sizeOptions.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                      {errors.items?.[idx]?.size?.message && (
                        <p className="mt-0.5 text-xs text-red-500">{errors.items[idx].size.message}</p>
                      )}
                    </div>

                    {/* Quantity */}
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">Quantity</label>
                      <div className="flex gap-1">
                        <input type="number" step="0.01" {...register(`items.${idx}.quantity_pcs`)} className="w-full rounded-l-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" placeholder="100" />
                        <select {...register(`items.${idx}.quantity_unit`)} className="rounded-r-md border border-l-0 border-gray-300 bg-gray-50 px-2 py-2 text-xs font-medium text-gray-600">
                          <option value="pcs">pcs</option>
                          <option value="sqm">m2</option>
                        </select>
                      </div>
                      {errors.items?.[idx]?.quantity_pcs?.message && <p className="mt-0.5 text-xs text-red-500">{errors.items[idx].quantity_pcs.message}</p>}
                    </div>

                    {/* Application — static dropdown */}
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">Application</label>
                      <select
                        {...register(`items.${idx}.application`)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                      >
                        <option value="">None</option>
                        {APPLICATION_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    </div>

                    {/* Finishing */}
                    <Input label="Finishing" {...register(`items.${idx}.finishing`)} placeholder="10/20" />

                    {/* Collection — dropdown from API */}
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Collection {collectionsLoading && <Spinner className="ml-1 inline h-3 w-3" />}
                      </label>
                      <select
                        {...register(`items.${idx}.collection`)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                      >
                        {collectionOptions.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    </div>

                    {/* Thickness */}
                    <Input label="Thickness (mm)" type="number" step="0.1" {...register(`items.${idx}.thickness_mm`)} placeholder="10" />

                    {/* Place of Application */}
                    <Select label="Place of Application" {...register(`items.${idx}.place_of_application`)} options={PLACE_OF_APPLICATION} />

                    {/* Product Type */}
                    <Select label="Product Type" {...register(`items.${idx}.product_type`)} options={PRODUCT_TYPES} />

                    {/* Shape */}
                    <Select label="Shape" {...register(`items.${idx}.shape`)} options={SHAPE_OPTIONS.map(s => ({ value: s.value, label: s.label }))} />

                    {/* Edge Profile — static dropdown */}
                    <Select
                      label="Edge Profile"
                      {...register(`items.${idx}.edge_profile`)}
                      options={EDGE_PROFILE_OPTIONS.map(o => ({ value: o.value, label: o.label }))}
                    />

                    {/* Edge Sides — number 1-4, only when edge != straight */}
                    {showEdgeSides && (
                      <Input
                        label="Edge Sides (1-4)"
                        type="number"
                        min={1}
                        max={4}
                        {...register(`items.${idx}.edge_profile_sides`)}
                      />
                    )}

                    {/* Priority — dropdown */}
                    <Select
                      label="Priority"
                      {...register(`items.${idx}.priority`)}
                      options={PRIORITY_OPTIONS.map(o => ({ value: o.value, label: o.label }))}
                    />

                    {/* Color 2 — shown only for Stencil/Silkscreen */}
                    {showColor2 && (
                      <Input
                        label="Color 2"
                        {...register(`items.${idx}.color_2`)}
                        placeholder="Second color"
                      />
                    )}
                  </div>
                  {/* Dimension fields — shown for non-standard shapes */}
                  {watchedItems?.[idx]?.shape && !['rectangle', 'square'].includes(watchedItems[idx].shape || '') && (
                    <div className="mt-2 grid grid-cols-4 gap-3 border-t border-gray-200 pt-2">
                      <Input label="Length (cm)" type="number" step="0.01" {...register(`items.${idx}.length_cm`)} placeholder="30" />
                      <Input label="Width (cm)" type="number" step="0.01" {...register(`items.${idx}.width_cm`)} placeholder="30" />
                      {watchedItems[idx].product_type === 'sink' && (
                        <>
                          <Input label="Depth (cm)" type="number" step="0.01" {...register(`items.${idx}.depth_cm`)} placeholder="15" />
                          <Select label="Bowl Shape" {...register(`items.${idx}.bowl_shape`)} options={BOWL_SHAPE_OPTIONS.map(s => ({ value: s.value, label: s.label }))} />
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {submitError && <p className="text-sm text-red-500">{submitError}</p>}

        <div className="flex justify-end gap-3 border-t pt-4">
          <Button type="button" variant="secondary" onClick={handleClose}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating...' : 'Create Order'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
