import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { factoryCreateSchema, type FactoryFormData } from '@/types/forms';
import { useCreateFactory, useUpdateFactory, type Factory } from '@/hooks/useFactories';

const TIMEZONE_OPTIONS = [
  'Asia/Makassar',
  'Asia/Jakarta',
  'Asia/Jayapura',
  'UTC',
];

interface Props {
  open: boolean;
  onClose: () => void;
  factory?: Factory | null;
}

export function FactoryDialog({ open, onClose, factory }: Props) {
  const createFactory = useCreateFactory();
  const updateFactory = useUpdateFactory();
  const isEdit = !!factory;
  const [submitError, setSubmitError] = useState('');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FactoryFormData>({
    resolver: zodResolver(factoryCreateSchema),
    defaultValues: { name: '', location: '', timezone: 'Asia/Makassar', is_active: true },
  });

  useEffect(() => {
    if (factory) {
      reset({
        name: factory.name,
        location: factory.location || '',
        timezone: factory.timezone || 'Asia/Makassar',
        is_active: factory.is_active,
      });
    } else {
      reset({ name: '', location: '', timezone: 'Asia/Makassar', is_active: true });
    }
  }, [factory, reset]);

  const onSubmit = async (data: FactoryFormData) => {
    setSubmitError('');
    try {
      if (isEdit && factory) {
        await updateFactory.mutateAsync({ id: factory.id, data });
      } else {
        await createFactory.mutateAsync(data);
      }
      reset();
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setSubmitError(resp?.detail || `Failed to ${isEdit ? 'update' : 'create'} factory`);
    }
  };

  const handleClose = () => {
    reset();
    setSubmitError('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} title={isEdit ? 'Edit Factory' : 'Add Factory'} className="w-full max-w-md">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input label="Factory Name" {...register('name')} error={errors.name?.message} placeholder="Bali Factory" />
        <Input label="Location" {...register('location')} placeholder="Bali, Indonesia" />

        <div className="w-full">
          <label className="mb-1 block text-sm font-medium text-gray-700">Timezone</label>
          <select {...register('timezone')} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
            {TIMEZONE_OPTIONS.map((tz) => (
              <option key={tz} value={tz}>{tz}</option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register('is_active')} className="rounded border-gray-300" />
          Active
        </label>

        {submitError && <p className="text-sm text-red-500">{submitError}</p>}

        <div className="flex justify-end gap-3 border-t pt-4">
          <Button type="button" variant="secondary" onClick={handleClose}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : isEdit ? 'Save Changes' : 'Add Factory'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
