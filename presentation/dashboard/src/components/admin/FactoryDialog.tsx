import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { factoryCreateSchema, TELEGRAM_LANGUAGE_OPTIONS, type FactoryFormData } from '@/types/forms';
import { useCreateFactory, useUpdateFactory, type Factory } from '@/hooks/useFactories';
import { useTestChat } from '@/hooks/useTelegramBot';

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
  const testChat = useTestChat();
  const isEdit = !!factory;
  const [submitError, setSubmitError] = useState('');
  const [testResult, setTestResult] = useState<{ field: string; success: boolean; message: string } | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FactoryFormData>({
    resolver: zodResolver(factoryCreateSchema),
    defaultValues: {
      name: '',
      location: '',
      timezone: 'Asia/Makassar',
      is_active: true,
      masters_group_chat_id: '',
      purchaser_chat_id: '',
      telegram_language: 'id',
    },
  });

  const mastersChat = watch('masters_group_chat_id');
  const purchaserChat = watch('purchaser_chat_id');

  useEffect(() => {
    if (factory) {
      reset({
        name: factory.name,
        location: factory.location || '',
        timezone: factory.timezone || 'Asia/Makassar',
        is_active: factory.is_active,
        masters_group_chat_id: factory.masters_group_chat_id?.toString() || '',
        purchaser_chat_id: factory.purchaser_chat_id?.toString() || '',
        telegram_language: factory.telegram_language || 'id',
      });
    } else {
      reset({
        name: '',
        location: '',
        timezone: 'Asia/Makassar',
        is_active: true,
        masters_group_chat_id: '',
        purchaser_chat_id: '',
        telegram_language: 'id',
      });
    }
    setTestResult(null);
  }, [factory, reset]);

  const handleTestChat = async (field: string, chatId: string) => {
    if (!chatId.trim()) return;
    setTestResult(null);
    try {
      const result = await testChat.mutateAsync(chatId.trim());
      if (result.success) {
        setTestResult({
          field,
          success: true,
          message: `✅ Connected: ${result.chat_title || 'OK'} (${result.chat_type})`,
        });
      } else {
        setTestResult({ field, success: false, message: `❌ ${result.error}` });
      }
    } catch {
      setTestResult({ field, success: false, message: '❌ Failed to test chat' });
    }
  };

  const onSubmit = async (data: FactoryFormData) => {
    setSubmitError('');
    // Convert string chat IDs to numbers for the API (or null if empty)
    const mastersId = data.masters_group_chat_id ? Number(data.masters_group_chat_id) : null;
    const purchaserId = data.purchaser_chat_id ? Number(data.purchaser_chat_id) : null;
    if ((mastersId !== null && !Number.isInteger(mastersId)) ||
        (purchaserId !== null && !Number.isInteger(purchaserId))) {
      setSubmitError('Chat IDs must be valid integers');
      return;
    }
    const payload: Record<string, unknown> = {
      ...data,
      masters_group_chat_id: mastersId,
      purchaser_chat_id: purchaserId,
    };
    try {
      if (isEdit && factory) {
        await updateFactory.mutateAsync({ id: factory.id, data: payload });
      } else {
        await createFactory.mutateAsync(payload);
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
    setTestResult(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} title={isEdit ? 'Edit Factory' : 'Add Factory'} className="w-full max-w-lg">
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

        {/* ── Telegram Integration ── */}
        <div className="border-t pt-4">
          <h3 className="mb-3 text-sm font-semibold text-gray-700">Telegram Integration</h3>

          {/* Masters Group Chat */}
          <div className="mb-3">
            <label className="mb-1 block text-sm font-medium text-gray-700">Masters Group Chat ID</label>
            <div className="flex gap-2">
              <input
                {...register('masters_group_chat_id')}
                placeholder="-1001234567890"
                className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={!mastersChat?.trim() || testChat.isPending}
                onClick={() => handleTestChat('masters', mastersChat || '')}
              >
                Test
              </Button>
            </div>
            {errors.masters_group_chat_id?.message && (
              <p className="mt-1 text-xs text-red-500">{errors.masters_group_chat_id.message}</p>
            )}
            {testResult?.field === 'masters' && (
              <p className={`mt-1 text-xs ${testResult.success ? 'text-green-600' : 'text-red-500'}`}>
                {testResult.message}
              </p>
            )}
          </div>

          {/* Purchaser Chat */}
          <div className="mb-3">
            <label className="mb-1 block text-sm font-medium text-gray-700">Purchaser Chat ID</label>
            <div className="flex gap-2">
              <input
                {...register('purchaser_chat_id')}
                placeholder="-1001234567890"
                className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={!purchaserChat?.trim() || testChat.isPending}
                onClick={() => handleTestChat('purchaser', purchaserChat || '')}
              >
                Test
              </Button>
            </div>
            {errors.purchaser_chat_id?.message && (
              <p className="mt-1 text-xs text-red-500">{errors.purchaser_chat_id.message}</p>
            )}
            {testResult?.field === 'purchaser' && (
              <p className={`mt-1 text-xs ${testResult.success ? 'text-green-600' : 'text-red-500'}`}>
                {testResult.message}
              </p>
            )}
          </div>

          {/* Telegram Language */}
          <div className="mb-2">
            <label className="mb-1 block text-sm font-medium text-gray-700">Notification Language</label>
            <select {...register('telegram_language')} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
              {TELEGRAM_LANGUAGE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <p className="text-xs text-gray-400">
            Add the bot to a Telegram group, then use <code className="rounded bg-gray-100 px-1">/chatid</code> or{' '}
            <a href="https://t.me/raw_data_bot" target="_blank" rel="noreferrer" className="text-blue-500 hover:underline">
              @raw_data_bot
            </a>{' '}
            to get the chat ID.
          </p>
        </div>

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
