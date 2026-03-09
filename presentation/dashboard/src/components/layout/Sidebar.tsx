import { NavLink } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useUiStore } from '@/stores/uiStore';
import { cn } from '@/lib/cn';

const navByRole: Record<string, { to: string; label: string }[]> = {
  owner: [{ to: '/owner', label: 'Dashboard' }, { to: '/users', label: 'Users' }, { to: '/admin', label: 'Admin' }],
  administrator: [{ to: '/admin', label: 'Admin Panel' }, { to: '/users', label: 'Users' }],
  ceo: [{ to: '/ceo', label: 'Dashboard' }, { to: '/tablo', label: 'Tablo' }, { to: '/users', label: 'Users' }],
  production_manager: [{ to: '/manager', label: 'Dashboard' }, { to: '/manager/schedule', label: 'Schedule' }, { to: '/manager/kilns', label: 'Kilns' }, { to: '/tablo', label: 'Tablo' }],
  quality_manager: [{ to: '/quality', label: 'Quality' }],
  warehouse: [{ to: '/warehouse', label: 'Warehouse' }],
  sorter_packer: [{ to: '/packing', label: 'Sorting & Packing' }],
  purchaser: [{ to: '/purchaser', label: 'Purchasing' }],
};

export function Sidebar() {
  const user = useAuthStore((s) => s.user);
  const { sidebarOpen, toggleSidebar } = useUiStore();
  const items = user ? navByRole[user.role] || [] : [];
  return (
    <aside className={cn('fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-white transition-all', sidebarOpen ? 'w-64' : 'w-16')}>
      <div className="flex h-16 items-center justify-between border-b px-4">
        {sidebarOpen && <span className="text-lg font-semibold"><span className="text-blue-600">Moonjar</span> <span className="font-bold text-gray-900">Production</span></span>}
        <button onClick={toggleSidebar} className="rounded p-1 text-gray-400 hover:bg-gray-100">{sidebarOpen ? '\u2190' : '\u2192'}</button>
      </div>
      <nav className="flex-1 space-y-1 px-2 py-4">
        {items.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => cn('flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors', isActive ? 'bg-primary-50 text-primary-700' : 'text-gray-600 hover:bg-gray-100')}>
            {sidebarOpen ? item.label : item.label[0]}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
