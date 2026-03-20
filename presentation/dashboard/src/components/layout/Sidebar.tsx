import { NavLink } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useUiStore } from '@/stores/uiStore';
import { cn } from '@/lib/cn';

type NavItem = { to: string; label: string } | { section: string };

const navByRole: Record<string, NavItem[]> = {
  owner: [
    { section: 'Dashboards' },
    { to: '/owner', label: 'Owner' },
    { to: '/ceo', label: 'CEO' },
    { section: 'Production' },
    { to: '/manager', label: 'Manager' },
    { to: '/manager/schedule', label: 'Schedule' },
    { to: '/manager/kilns', label: 'Kilns' },
    { to: '/manager/materials', label: 'Materials (Mgr)' },
    { section: 'Catalog' },
    { to: '/admin/materials', label: 'Materials' },
    { to: '/admin/recipes', label: 'Recipes' },
    { to: '/admin/firing-profiles', label: 'Firing Profiles' },
    { to: '/admin/temperature-groups', label: 'Temp Groups' },
    { to: '/admin/colors', label: 'Colors' },
    { to: '/admin/collections', label: 'Collections' },
    { to: '/admin/color-collections', label: 'Color Collections' },
    { to: '/admin/application-types', label: 'Application Types' },
    { to: '/admin/places-of-application', label: 'Places of Application' },
    { to: '/admin/finishing-types', label: 'Finishing Types' },
    { to: '/admin/suppliers', label: 'Suppliers' },
    { to: '/admin/warehouses', label: 'Warehouses' },
    { to: '/admin/packaging', label: 'Packaging' },
    { to: '/admin/sizes', label: 'Sizes' },
    { to: '/admin/consumption-rules', label: 'Consumption Rules' },
    { section: 'Operations' },
    { to: '/quality', label: 'Quality' },
    { to: '/warehouse', label: 'Warehouse' },
    { to: '/packing', label: 'Sorting & Packing' },
    { to: '/purchaser', label: 'Purchasing' },
    { section: 'System' },
    { to: '/users', label: 'Users' },
    { to: '/admin', label: 'Admin Panel' },
    { to: '/tablo', label: 'Tablo' },
  ],
  administrator: [
    { to: '/admin', label: 'Admin Panel' },
    { to: '/admin/materials', label: 'Materials' },
    { to: '/admin/recipes', label: 'Recipes' },
    { to: '/admin/firing-profiles', label: 'Firing Profiles' },
    { to: '/admin/temperature-groups', label: 'Temperature Groups' },
    { to: '/admin/colors', label: 'Colors' },
    { to: '/admin/collections', label: 'Collections' },
    { to: '/admin/suppliers', label: 'Suppliers' },
    { to: '/admin/warehouses', label: 'Warehouses' },
    { to: '/admin/packaging', label: 'Packaging' },
    { to: '/admin/sizes', label: 'Sizes' },
    { to: '/admin/consumption-rules', label: 'Consumption Rules' },
    { to: '/users', label: 'Users' },
  ],
  ceo: [{ to: '/ceo', label: 'Dashboard' }, { to: '/tablo', label: 'Tablo' }, { to: '/users', label: 'Users' }],
  production_manager: [
    { to: '/manager', label: 'Dashboard' },
    { to: '/manager/schedule', label: 'Schedule' },
    { to: '/manager/kilns', label: 'Kilns' },
    { to: '/manager/kiln-inspections', label: 'Kiln Inspections' },
    { to: '/manager/materials', label: 'Materials' },
    { to: '/admin/recipes', label: 'Recipes' },
    { to: '/admin/firing-profiles', label: 'Firing Profiles' },
    { to: '/admin/temperature-groups', label: 'Temp Groups' },
    { to: '/admin/warehouses', label: 'Warehouses' },
    { to: '/admin/packaging', label: 'Packaging' },
    { to: '/admin/sizes', label: 'Sizes' },
    { to: '/admin/consumption-rules', label: 'Consumption Rules' },
    { to: '/tablo', label: 'Tablo' },
    { to: '/manager/guide', label: '\uD83D\uDCD6 Guide' },
  ],
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
    <aside className={cn('fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-white transition-all', sidebarOpen ? 'w-72' : 'w-16')}>
      <div className="flex h-20 items-center justify-between border-b px-4">
        {sidebarOpen && <span className="text-3xl font-semibold"><span className="text-blue-600">Moonjar</span> <span className="font-bold text-gray-900">Production</span></span>}
        <button onClick={toggleSidebar} className="rounded p-1 text-gray-400 hover:bg-gray-100">{sidebarOpen ? '\u2190' : '\u2192'}</button>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4">
        {items.map((item) =>
          'section' in item ? (
            sidebarOpen ? (
              <div key={item.section} className="px-3 pb-1 pt-4 text-base font-semibold uppercase tracking-wider text-gray-400 first:pt-0">{item.section}</div>
            ) : (
              <div key={item.section} className="my-2 border-t border-gray-200" />
            )
          ) : (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => cn('flex items-center gap-3 rounded-md px-3 py-2.5 text-lg font-medium transition-colors', isActive ? 'bg-primary-50 text-primary-700' : 'text-gray-600 hover:bg-gray-100')}>
              {sidebarOpen ? item.label : item.label[0]}
            </NavLink>
          ),
        )}
      </nav>
    </aside>
  );
}
