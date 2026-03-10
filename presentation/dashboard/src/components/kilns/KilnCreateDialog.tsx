import { useState, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { kilnCreateSchema, type KilnCreateFormData, KILN_TYPE_OPTIONS } from '@/types/forms';
import { useCreateKiln } from '@/hooks/useKilns';

const DEFAULTS: Record<string, Partial<KilnCreateFormData>> = {
  big: {
    kiln_dimensions_cm: { width: 100, depth: 100, height: 100 },
    kiln_working_area_cm: { width: 54, depth: 84, height: 80 },
    kiln_multi_level: true,
    kiln_coefficient: 0.8,
  },
  small: {
    kiln_dimensions_cm: { width: 120, depth: 180, height: 50 },
    kiln_working_area_cm: { width: 100, depth: 160, height: 45 },
    kiln_multi_level: false,
    kiln_coefficient: 0.92,
  },
  raku: {
    kiln_dimensions_cm: { width: 70, depth: 110, height: 50 },
    kiln_working_area_cm: { width: 60, depth: 100, height: 45 },
    kiln_multi_level: false,
    kiln_coefficient: 0.85,
  },
};

interface Props {
  open: boolean;
  onClose: () => void;
  factoryId: string;
}

export function KilnCreateDialog({ open, onClose, factoryId }: Props) {
  const createKiln = useCreateKiln();
  const [submitError, setSubmitError] = useState('');

  const typeOptions = useMemo(() => [{ value: '', label: 'Select type...' }, ...KILN_TYPE_OPTIONS], []);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<KilnCreateFormData>({
    resolver: zodResolver(kilnCreateSchema),
    defaultValues: {
      name: '',
      kiln_type: '',
      kiln_dimensions_cm: { width: 0, depth: 0, height: 0 },
      kiln_working_area_cm: { width: 0, depth: 0, height: 0 },
      kiln_multi_level: false,
      kiln_coefficient: 0.8,
    },
  });

  const kilnType = watch('kiln_type');

  const applyDefaults = (type: string) => {
    const d = DEFAULTS[type];
    if (d) {
      if (d.kiln_dimensions_cm) {
        setValue('kiln_dimensions_cm.width', d.kiln_dimensions_cm.width);
        setValue('kiln_dimensions_cm.depth', d.kiln_dimensions_cm.depth);
        setValue('kiln_dimensions_cm.height', d.kiln_dimensions_cm.height);
      }
      if (d.kiln_working_area_cm) {
        setValue('kiln_working_area_cm.width', d.kiln_working_area_cm.width);
        setValue('kiln_working_area_cm.depth', d.kiln_working_area_cm.depth);
        setValue('kiln_working_area_cm.height', d.kiln_working_area_cm.height);
      }
      if (d.kiln_multi_level !== undefined) setValue('kiln_multi_level', d.kiln_multi_level);
      if (d.kiln_coefficient !== undefined) setValue('kiln_coefficient', d.kiln_coefficient);
    }
  };

  const onSubmit = async (data: KilnCreateFormData) => {
    setSubmitError('');
    try {
      await createKiln.mutateAsync({ ...data, factory_id: factoryId });
      reset();
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: unknown } } })?.response?.data;
      const detail = resp?.detail;
      if (Array.isArray(detail)) {
        setSubmitError(detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ') || 'Validation error');
      } else {
        setSubmitError((detail as string | undefined) || 'Failed to create kiln');
      }
    }
  };

  const handleClose = () => { reset(); setSubmitError(''); onClose(); };

  return (
    <Dialog open={open} onClose={handleClose} title="Add Kiln" className="w-full max-w-lg">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Input label="Kiln Name" {...register('name')} error={errors.name?.message} placeholder="Large Kiln" />
          <div>
            <Select
              label="Type"
              {...register('kiln_type', {
                onChange: (e) => applyDefaults(e.target.value),
              })}
              error={errors.kiln_type?.message}
              options={typeOptions}
            />
          </div>
        </div>

        {kilnType && (
          <>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Outer Dimensions (cm)</label>
              <div className="grid grid-cols-3 gap-2">
                <Input placeholder="Width" type="number" {...register('kiln_dimensions_cm.width')} error={errors.kiln_dimensions_cm?.width?.message} />
                <Input placeholder="Depth" type="number" {...register('kiln_dimensions_cm.depth')} error={errors.kiln_dimensions_cm?.depth?.message} />
                <Input placeholder="Height" type="number" {...register('kiln_dimensions_cm.height')} error={errors.kiln_dimensions_cm?.height?.message} />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Working Area (cm)</label>
              <div className="grid grid-cols-3 gap-2">
                <Input placeholder="Width" type="number" {...register('kiln_working_area_cm.width')} error={errors.kiln_working_area_cm?.width?.message} />
                <Input placeholder="Depth" type="number" {...register('kiln_working_area_cm.depth')} error={errors.kiln_working_area_cm?.depth?.message} />
                <Input placeholder="Height" type="number" {...register('kiln_working_area_cm.height')} error={errors.kiln_working_area_cm?.height?.message} />
              </div>
            </div>

            <Input label="Coefficient" type="number" step="0.01" {...register('kiln_coefficient')} error={errors.kiln_coefficient?.message} />

            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...register('kiln_multi_level')} className="rounded border-gray-300" />
              Multi-level support
            </label>
          </>
        )}

        {submitError && <p className="text-sm text-red-500">{submitError}</p>}

        <div className="flex justify-end gap-3 border-t pt-4">
          <Button type="button" variant="secondary" onClick={handleClose}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting || !kilnType}>
            {isSubmitting ? 'Creating...' : 'Add Kiln'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
