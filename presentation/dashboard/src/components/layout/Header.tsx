import { useState, useRef, useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { Avatar } from '@/components/ui/Avatar';
import { DropdownMenu } from '@/components/ui/DropdownMenu';
import { useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import apiClient from '@/api/client';

export function Header() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const notifications = useNotificationStore((s) => s.notifications);
  const unreadCount = useNotificationStore((s) => s.unreadCount);
  const markAllRead = useNotificationStore((s) => s.markAllRead);

  const [showNotifications, setShowNotifications] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    }
    if (showNotifications) {
      document.addEventListener('mousedown', handleClick);
      return () => document.removeEventListener('mousedown', handleClick);
    }
  }, [showNotifications]);

  const handleLogout = async () => {
    try { await apiClient.post('/auth/logout'); } catch {}
    logout();
    navigate('/login');
  };

  const toggleNotifications = () => {
    setShowNotifications((v) => !v);
    if (!showNotifications && unreadCount > 0) {
      markAllRead();
    }
  };

  return (
    <header className="flex h-16 items-center justify-between border-b bg-white px-6">
      <div />
      <div className="flex items-center gap-4">
        <div className="relative" ref={panelRef}>
          <button
            className="relative rounded-full p-2 text-gray-400 hover:bg-gray-100"
            aria-label="Notifications"
            onClick={toggleNotifications}
          >
            <Bell size={20} />
            {unreadCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-lg border bg-white shadow-lg">
              <div className="border-b px-4 py-3">
                <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
              </div>
              <div className="max-h-72 overflow-y-auto">
                {notifications.length === 0 ? (
                  <p className="px-4 py-6 text-center text-sm text-gray-400">No notifications yet</p>
                ) : (
                  notifications.slice(0, 20).map((n) => (
                    <div
                      key={n.id}
                      className={`border-b px-4 py-3 text-sm last:border-b-0 ${n.read ? 'bg-white' : 'bg-blue-50'}`}
                    >
                      <p className="font-medium text-gray-900">{n.title}</p>
                      {n.body && <p className="mt-0.5 text-gray-500">{n.body}</p>}
                      <p className="mt-1 text-xs text-gray-400">
                        {new Date(n.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {user && (
          <DropdownMenu
            trigger={<Avatar name={user.name} className="cursor-pointer" />}
            items={[
              { label: user.name, onClick: () => {} },
              { label: 'Settings', onClick: () => navigate('/settings') },
              { label: 'Logout', onClick: handleLogout },
            ]}
          />
        )}
      </div>
    </header>
  );
}
