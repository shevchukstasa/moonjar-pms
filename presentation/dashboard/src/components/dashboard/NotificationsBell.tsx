import { useState, useRef, useEffect } from 'react';
import { Bell } from 'lucide-react';
import { Spinner } from '@/components/ui/Spinner';
import {
  useNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
} from '@/hooks/useNotifications';

export function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Fetch last 10 notifications (unread first, then recent)
  const { data, isLoading } = useNotifications({ per_page: 10 });
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const items = data?.items ?? [];
  const unreadCount: number = data?.unread_count ?? 0;

  // Close panel when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  function timeAgo(iso: string | null | undefined): string {
    if (!iso) return '';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60_000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell icon button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative flex items-center justify-center rounded-full p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus:outline-none"
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-10 z-50 w-80 rounded-lg border border-gray-200 bg-white shadow-lg">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2">
            <span className="text-sm font-semibold text-gray-900">
              Notifications
              {unreadCount > 0 && (
                <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                  {unreadCount} new
                </span>
              )}
            </span>
            {unreadCount > 0 && (
              <button
                className="text-xs text-blue-600 hover:underline"
                onClick={() => markAllRead.mutate()}
                disabled={markAllRead.isPending}
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Notifications list */}
          <div className="max-h-80 overflow-y-auto">
            {isLoading ? (
              <div className="flex justify-center py-6">
                <Spinner className="h-5 w-5" />
              </div>
            ) : items.length === 0 ? (
              <div className="py-6 text-center text-sm text-gray-400">
                No notifications
              </div>
            ) : (
              items.map((notif: {
                id: string;
                title: string;
                message?: string;
                is_read: boolean;
                created_at?: string;
                type?: string;
              }) => (
                <div
                  key={notif.id}
                  onClick={() => {
                    if (!notif.is_read) {
                      markRead.mutate(notif.id);
                    }
                  }}
                  className={`cursor-pointer border-b border-gray-50 px-4 py-3 hover:bg-gray-50 transition-colors ${
                    !notif.is_read ? 'bg-blue-50/40' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className={`text-sm ${!notif.is_read ? 'font-semibold text-gray-900' : 'font-medium text-gray-700'}`}>
                        {notif.title}
                      </p>
                      {notif.message && (
                        <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">
                          {notif.message}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-shrink-0 flex-col items-end gap-1">
                      <span className="text-[10px] text-gray-400">
                        {timeAgo(notif.created_at)}
                      </span>
                      {!notif.is_read && (
                        <span className="h-2 w-2 rounded-full bg-blue-500" />
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          {items.length > 0 && (
            <div className="border-t border-gray-100 px-4 py-2 text-center">
              <span className="text-xs text-gray-400">Last 10 notifications</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
