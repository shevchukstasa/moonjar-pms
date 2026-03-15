import { useState } from 'react';
import { toast } from 'sonner';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useAuthStore } from '@/stores/authStore';
import { useNotificationPreferences, useCreatePreference, useUpdatePreference } from '@/hooks/useNotificationPreferences';
import { useTelegramSubscribe, useTelegramUnsubscribe, useBotStatus } from '@/hooks/useTelegramBot';
import type { NotificationPreference } from '@/api/notifications';

const NOTIFICATION_TYPES = [
  { type: 'alert', label: 'Urgent Alerts' },
  { type: 'task_assigned', label: 'Task Assignments' },
  { type: 'status_change', label: 'Status Changes' },
  { type: 'material_received', label: 'Material Received' },
  { type: 'repair_sla', label: 'Repair / SLA Warnings' },
] as const;

const CHANNEL_OPTIONS = [
  { value: 'in_app', label: 'In-App Only' },
  { value: 'telegram', label: 'Telegram Only' },
  { value: 'both', label: 'Both' },
];

function TelegramSection() {
  const user = useAuthStore((s) => s.user);
  const updateUser = useAuthStore((s) => s.updateUser);
  const { data: botStatus } = useBotStatus();
  const subscribe = useTelegramSubscribe();
  const unsubscribe = useTelegramUnsubscribe();
  const [telegramId, setTelegramId] = useState('');

  const isLinked = !!user?.telegram_user_id;
  const botUsername = botStatus?.bot_username;

  const handleLink = () => {
    const id = parseInt(telegramId, 10);
    if (!id || isNaN(id)) {
      toast.error('Please enter a valid Telegram user ID');
      return;
    }
    subscribe.mutate(id, {
      onSuccess: () => {
        updateUser({ telegram_user_id: id });
        setTelegramId('');
        toast.success('Telegram account linked successfully');
      },
      onError: () => toast.error('Failed to link Telegram account'),
    });
  };

  const handleUnlink = () => {
    unsubscribe.mutate(undefined, {
      onSuccess: () => {
        updateUser({ telegram_user_id: null });
        toast.success('Telegram account unlinked');
      },
      onError: () => toast.error('Failed to unlink Telegram account'),
    });
  };

  return (
    <Card title="Telegram Account">
      {isLinked ? (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-3 py-1 text-sm font-medium text-green-700">
              <span className="h-2 w-2 rounded-full bg-green-500" />
              Telegram linked (ID: {user.telegram_user_id})
            </span>
          </div>
          <Button
            variant="danger"
            size="sm"
            onClick={handleUnlink}
            disabled={unsubscribe.isPending}
          >
            {unsubscribe.isPending ? 'Unlinking...' : 'Unlink'}
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-md bg-blue-50 p-3">
            <p className="text-sm text-blue-800">
              To link your Telegram account:
            </p>
            <ol className="mt-2 list-inside list-decimal space-y-1 text-sm text-blue-700">
              <li>
                Open Telegram and search for{' '}
                {botUsername ? (
                  <span className="font-medium">@{botUsername}</span>
                ) : (
                  <span className="font-medium">@MoonjarBot</span>
                )}
              </li>
              <li>Send <span className="font-mono font-medium">/start</span> to the bot</li>
              <li>The bot will show your Telegram user ID</li>
              <li>Enter that ID below and click Link</li>
            </ol>
          </div>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Input
                label="Telegram User ID"
                type="number"
                placeholder="e.g. 123456789"
                value={telegramId}
                onChange={(e) => setTelegramId(e.target.value)}
              />
            </div>
            <Button
              size="md"
              onClick={handleLink}
              disabled={!telegramId || subscribe.isPending}
            >
              {subscribe.isPending ? 'Linking...' : 'Link'}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

function PreferenceRow({
  notificationType,
  label,
  preference,
  isTelegramLinked,
}: {
  notificationType: string;
  label: string;
  preference: NotificationPreference | undefined;
  isTelegramLinked: boolean;
}) {
  const createPref = useCreatePreference();
  const updatePref = useUpdatePreference();

  const currentChannel = preference?.channel || 'in_app';

  const handleChange = (newChannel: string) => {
    if (preference) {
      updatePref.mutate(
        { id: preference.id, data: { channel: newChannel } },
        {
          onSuccess: () => toast.success(`Updated ${label} preference`),
          onError: () => toast.error(`Failed to update ${label}`),
        },
      );
    } else {
      createPref.mutate(
        { notification_type: notificationType, channel: newChannel },
        {
          onSuccess: () => toast.success(`Set ${label} preference`),
          onError: () => toast.error(`Failed to set ${label}`),
        },
      );
    }
  };

  const isPending = createPref.isPending || updatePref.isPending;

  // If Telegram is not linked, only allow in_app
  const options = isTelegramLinked
    ? CHANNEL_OPTIONS
    : CHANNEL_OPTIONS.map((o) =>
        o.value !== 'in_app' ? { ...o, label: `${o.label} (link Telegram first)` } : o,
      );

  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-3 pr-4 text-sm text-gray-700">{label}</td>
      <td className="py-3">
        <div className="flex items-center gap-2">
          <Select
            options={options}
            value={currentChannel}
            onChange={(e) => handleChange(e.target.value)}
            disabled={isPending || (!isTelegramLinked && currentChannel !== 'in_app')}
            className="max-w-[200px]"
          />
          {isPending && <Spinner className="h-4 w-4" />}
        </div>
      </td>
    </tr>
  );
}

export function NotificationSettings() {
  const user = useAuthStore((s) => s.user);
  const { data: preferences, isLoading, isError } = useNotificationPreferences();

  const isTelegramLinked = !!user?.telegram_user_id;

  const prefMap = new Map<string, NotificationPreference>();
  if (preferences) {
    for (const p of preferences) {
      prefMap.set(p.notification_type, p);
    }
  }

  return (
    <div className="space-y-6">
      <TelegramSection />

      <Card title="Notification Preferences">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Spinner className="h-6 w-6" />
          </div>
        ) : isError ? (
          <p className="py-4 text-sm text-red-500">
            Failed to load notification preferences. Please try again.
          </p>
        ) : (
          <>
            {!isTelegramLinked && (
              <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-700">
                Link your Telegram account above to enable Telegram notifications.
              </p>
            )}
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="pb-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Notification Type
                  </th>
                  <th className="pb-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Channel
                  </th>
                </tr>
              </thead>
              <tbody>
                {NOTIFICATION_TYPES.map(({ type, label }) => (
                  <PreferenceRow
                    key={type}
                    notificationType={type}
                    label={label}
                    preference={prefMap.get(type)}
                    isTelegramLinked={isTelegramLinked}
                  />
                ))}
              </tbody>
            </table>
          </>
        )}
      </Card>
    </div>
  );
}
