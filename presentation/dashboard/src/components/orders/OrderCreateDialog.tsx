import { useState, useMemo } from 'react';
import { useForm, useFieldArray, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { orderCreateSchema, type OrderCreateFormData, SHAPE_OPTIONS, BOWL_SHAPE_OPTIONS } from '@/types/forms';
import { useCreateOrder } from '@/hooks/useOrders';
import { useFactories } from '@/hooks/useFactories';

const PRODUCT_TYPES = [
  { value: 'tile', label: 'Tile' },
  { value: 'countertop', label: 'Countertop' },
  { value: 'sink', label: 'Sink' },
  { value: '3d', label: '3D' },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function OrderCreateDialog({ open, onClose }: Props) {
  const createOrder = useCreateOrder();
  const { data: factoriesData } = useFactories();
  const [submitError, setSubmitError] = useState('');

  const factoryOptions = useMemo(() => {
    const opts = [{ value: '', label: 'Select factory...' }];
    for (const f of factoriesData?.items || []) {
      opts.push({ value: f.id, label: f.name });
    }
    return opts;
  }, [factoriesData]);

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
      items: [{ color: '', size: '', application: '', finishing: '', collection: '', quantity_pcs: 1, product_type: 'tile', shape: 'rectangle', length_cm: null, width_cm: null, depth_cm: null, bowl_shape: '' }],
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
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
              onClick={() => append({ color: '', size: '', application: '', finishing: '', collection: '', quantity_pcs: 1, product_type: 'tile', shape: 'rectangle', length_cm: null, width_cm: null, depth_cm: null, bowl_shape: '' })}
            >
              + Add Item
            </Button>
          </div>
          {errors.items?.root?.message && (
            <p className="mb-2 text-xs text-red-500">{errors.items.root.message}</p>
          )}
          <div className="space-y-3">
            {fields.map((field, idx) => (
              <div key={field.id} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500">Item {idx + 1}</span>
                  {fields.length > 1 && (
                    <button type="button" onClick={() => remove(idx)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <Input label="Color" {...register(`items.${idx}.color`)} error={errors.items?.[idx]?.color?.message} placeholder="Red" />
                  <Input label="Size" {...register(`items.${idx}.size`)} error={errors.items?.[idx]?.size?.message} placeholder="10x10" />
                  <Input label="Quantity" type="number" {...register(`items.${idx}.quantity_pcs`)} error={errors.items?.[idx]?.quantity_pcs?.message} />
                  <Input label="Application" {...register(`items.${idx}.application`)} placeholder="Wall" />
                  <Input label="Finishing" {...register(`items.${idx}.finishing`)} placeholder="Matte" />
                  <Input label="Collection" {...register(`items.${idx}.collection`)} placeholder="e.g. Stock" />
                  <Select label="Product Type" {...register(`items.${idx}.product_type`)} options={PRODUCT_TYPES} />
                  <Select label="Shape" {...register(`items.${idx}.shape`)} options={SHAPE_OPTIONS.map(s => ({ value: s.value, label: s.label }))} />
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
            ))}
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
