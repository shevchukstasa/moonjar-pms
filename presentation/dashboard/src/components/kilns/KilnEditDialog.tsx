import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { kilnEditSchema, type KilnEditFormData, KILN_STATUS_OPTIONS } from '@/types/forms';
import { useUpdateKiln, useUpdateKilnStatus, useDeleteKiln, type KilnItem } from '@/hooks/useKilns';
import { useFactories } from '@/hooks/useFactories';

interface Props {
  open: boolean;
  onClose: () => void;
  kiln: KilnItem | null;
}

export function KilnEditDialog({ open, onClose, kiln }: Props) {
  const updateKiln = useUpdateKiln();
  const updateStatus = useUpdateKilnStatus();
  const deleteKiln = useDeleteKiln();
  const { data: factoriesData } = useFactories();
  const factories = factoriesData?.items || [];
  const [submitError, setSubmitError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const statusOptions = [...KILN_STATUS_OPTIONS];

  const factoryOptions = factories.map((f) => ({
    value: f.id,
    label: `${f.name}${f.location ? ` (${f.location})` : ''}`,
  }));

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<KilnEditFormData>({
    resolver: zodResolver(kilnEditSchema),
  });

  useEffect(() => {
    if (kiln) {
      reset({
        name: kiln.name,
        factory_id: kiln.factory_id,
        kiln_dimensions_cm: kiln.kiln_dimensions_cm || { width: 0, depth: 0, height: 0 },
        kiln_working_area_cm: kiln.kiln_working_area_cm || { width: 0, depth: 0, height: 0 },
        kiln_multi_level: kiln.kiln_multi_level,
        kiln_coefficient: kiln.kiln_coefficient || 0.8,
      });
      setConfirmDelete(false);
    }
  }, [kiln, reset]);

  const onSubmit = async (data: KilnEditFormData) => {
    if (!kiln) return;
    setSubmitError('');
    try {
      await updateKiln.mutateAsync({ id: kiln.id, data });
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setSubmitError(resp?.detail || 'Failed to update kiln');
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!kiln) return;
    setSubmitError('');
    try {
      await updateStatus.mutateAsync({ id: kiln.id, status: newStatus });
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setSubmitError(resp?.detail || 'Failed to update status');
    }
  };

  const handleDelete = async () => {
    if (!kiln) return;
    setSubmitError('');
    try {
      await deleteKiln.mutateAsync(kiln.id);
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setSubmitError(resp?.detail || 'Failed to delete kiln');
      setConfirmDelete(false);
    }
  };

  if (!kiln) return null;

  return (
    <Dialog open={open} onClose={onClose} title="Edit Kiln" className="w-full max-w-lg">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Input label="Kiln Name" {...register('name')} error={errors.name?.message} />
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Type</label>
            <p className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm capitalize text-gray-600">
              {kiln.kiln_type === 'big' ? 'Large' : kiln.kiln_type === 'small' ? 'Small' : 'Raku'}
            </p>
          </div>
        </div>

        {/* Factory assignment */}
        <Select
          label="Factory"
          {...register('factory_id')}
          error={errors.factory_id?.message}
          options={factoryOptions}
        />

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Outer Dimensions (cm)</label>
          <div className="grid grid-cols-3 gap-2">
            <Input placeholder="Width" type="number" {...register('kiln_dimensions_cm.width')} />
            <Input placeholder="Depth" type="number" {...register('kiln_dimensions_cm.depth')} />
            <Input placeholder="Height" type="number" {...register('kiln_dimensions_cm.height')} />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Working Area (cm)</label>
          <div className="grid grid-cols-3 gap-2">
            <Input placeholder="Width" type="number" {...register('kiln_working_area_cm.width')} />
            <Input placeholder="Depth" type="number" {...register('kiln_working_area_cm.depth')} />
            <Input placeholder="Height" type="number" {...register('kiln_working_area_cm.height')} />
          </div>
        </div>

        <Input label="Coefficient" type="number" step="0.01" {...register('kiln_coefficient')} />

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register('kiln_multi_level')} className="rounded border-gray-300" />
          Multi-level support
        </label>

        {/* Calculated levels info */}
        {kiln.kiln_multi_level && kiln.kiln_working_area_cm && (
          <div className="rounded-md border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700">
            Levels are calculated automatically based on product height, air gap, and shelf
            thickness (configured in Loading Rules).
          </div>
        )}

        {/* Status control */}
        <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
          <label className="mb-2 block text-sm font-medium text-gray-700">Status</label>
          <div className="flex items-center gap-2">
            <Select
              options={statusOptions}
              value={kiln.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="flex-1"
            />
          </div>
        </div>

        {submitError && <p className="text-sm text-red-500">{submitError}</p>}

        <div className="flex items-center justify-between border-t pt-4">
          {/* Delete section */}
          <div>
            {!confirmDelete ? (
              <Button
                type="button"
                variant="ghost"
                className="text-red-500 hover:bg-red-50 hover:text-red-700"
                onClick={() => setConfirmDelete(true)}
              >
                Delete Kiln
              </Button>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-xs text-red-600">Are you sure?</span>
                <Button
                  type="button"
                  variant="ghost"
                  className="text-red-600 hover:bg-red-100"
                  onClick={handleDelete}
                  disabled={deleteKiln.isPending}
                >
                  {deleteKiln.isPending ? 'Deleting...' : 'Yes, delete'}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setConfirmDelete(false)}
                >
                  Cancel
                </Button>
              </div>
            )}
          </div>

          {/* Save section */}
          <div className="flex gap-3">
            <Button type="button" variant="secondary" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </form>
    </Dialog>
  );
}
