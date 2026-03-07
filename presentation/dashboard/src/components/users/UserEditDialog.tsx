import { useState, useMemo, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { userUpdateSchema, type UserUpdateFormData, ROLE_OPTIONS, LANGUAGE_OPTIONS } from '@/types/forms';
import { useUpdateUser, useToggleUserActive, type UserItem } from '@/hooks/useUsers';
import { useFactories } from '@/hooks/useFactories';

interface Props {
  open: boolean;
  onClose: () => void;
  user: UserItem | null;
}

export function UserEditDialog({ open, onClose, user }: Props) {
  const updateUser = useUpdateUser();
  const toggleActive = useToggleUserActive();
  const { data: factoriesData } = useFactories();
  const [submitError, setSubmitError] = useState('');

  const roleOptions = useMemo(() => [...ROLE_OPTIONS], []);
  const langOptions = useMemo(() => [...LANGUAGE_OPTIONS], []);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<UserUpdateFormData>({
    resolver: zodResolver(userUpdateSchema),
  });

  // Reset form when user changes
  useEffect(() => {
    if (user) {
      reset({
        name: user.name,
        role: user.role,
        language: user.language || 'en',
        factory_ids: user.factories.map((f) => f.id),
      });
    }
  }, [user, reset]);

  const selectedFactories = watch('factory_ids') || [];
  const factories = factoriesData?.items || [];

  const toggleFactory = (fid: string) => {
    const current = selectedFactories;
    if (current.includes(fid)) {
      setValue('factory_ids', current.filter((id) => id !== fid));
    } else {
      setValue('factory_ids', [...current, fid]);
    }
  };

  const onSubmit = async (data: UserUpdateFormData) => {
    if (!user) return;
    setSubmitError('');
    try {
      await updateUser.mutateAsync({ id: user.id, data });
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setSubmitError(resp?.detail || 'Failed to update user');
    }
  };

  const handleToggleActive = async () => {
    if (!user) return;
    setSubmitError('');
    try {
      await toggleActive.mutateAsync(user.id);
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setSubmitError(resp?.detail || 'Failed to toggle user status');
    }
  };

  const handleClose = () => {
    setSubmitError('');
    onClose();
  };

  if (!user) return null;

  return (
    <Dialog open={open} onClose={handleClose} title="Edit User" className="w-full max-w-lg">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Email (read-only) */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
          <p className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600">{user.email}</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Input label="Name" {...register('name')} error={errors.name?.message} />
          <Select label="Role" {...register('role')} error={errors.role?.message} options={roleOptions} />
        </div>

        <Select label="Language" {...register('language')} options={langOptions} />

        {/* Factory assignment */}
        {factories.length > 0 && (
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Factory Access</label>
            <div className="space-y-1.5">
              {factories.map((f) => (
                <label key={f.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedFactories.includes(f.id)}
                    onChange={() => toggleFactory(f.id)}
                    className="rounded border-gray-300"
                  />
                  {f.name}
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Active/Inactive toggle */}
        <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">Account Status</p>
              <p className="text-xs text-gray-500">
                {user.is_active ? 'User can log in and access the system' : 'User is deactivated and cannot log in'}
              </p>
            </div>
            <Button
              type="button"
              variant={user.is_active ? 'danger' : 'primary'}
              size="sm"
              onClick={handleToggleActive}
              disabled={toggleActive.isPending}
            >
              {user.is_active ? 'Deactivate' : 'Activate'}
            </Button>
          </div>
        </div>

        {submitError && <p className="text-sm text-red-500">{submitError}</p>}

        <div className="flex justify-end gap-3 border-t pt-4">
          <Button type="button" variant="secondary" onClick={handleClose}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
