import { NotificationSettings } from '@/components/settings/NotificationSettings';

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
      <NotificationSettings />
    </div>
  );
}
