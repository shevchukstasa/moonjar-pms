import { useState, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { userCreateSchema, type UserCreateFormData, ROLE_OPTIONS, LANGUAGE_OPTIONS } from '@/types/forms';
import { useCreateUser } from '@/hooks/useUsers';
import { useFactories } from '@/hooks/useFactories';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function UserCreateDialog({ open, onClose }: Props) {
  const createUser = useCreateUser();
  const { data: factoriesData } = useFactories();
  const [submitError, setSubmitError] = useState('');

  const roleOptions = useMemo(() => [{ value: '', label: 'Select role...' }, ...ROLE_OPTIONS], []);
  const langOptions = useMemo(() => [...LANGUAGE_OPTIONS], []);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<UserCreateFormData>({
    resolver: zodResolver(userCreateSchema),
    defaultValues: { email: '', name: '', role: '', password: '', factory_ids: [], language: 'en' },
  });

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

  const onSubmit = async (data: UserCreateFormData) => {
    setSubmitError('');
    try {
      await createUser.mutateAsync(data);
      reset();
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setSubmitError(resp?.detail || 'Failed to create user');
    }
  };

  const handleClose = () => {
    reset();
    setSubmitError('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Create User" className="w-full max-w-lg">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Input label="Email" type="email" {...register('email')} error={errors.email?.message} placeholder="user@example.com" />
          <Input label="Name" {...register('name')} error={errors.name?.message} placeholder="Full name" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Select label="Role" {...register('role')} error={errors.role?.message} options={roleOptions} />
          <Select label="Language" {...register('language')} options={langOptions} />
        </div>

        <Input label="Password" type="password" {...register('password')} error={errors.password?.message} placeholder="Min 6 characters" />

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

        {submitError && <p className="text-sm text-red-500">{submitError}</p>}

        <div className="flex justify-end gap-3 border-t pt-4">
          <Button type="button" variant="secondary" onClick={handleClose}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating...' : 'Create User'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
