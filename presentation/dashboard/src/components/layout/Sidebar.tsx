import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useUiStore } from '@/stores/uiStore';
import { cn } from '@/lib/cn';

/* ── Types ──────────────────────────────────────────────────────────── */

type NavItem = { to: string; label: string; icon?: string };
type NavSection = { section: string; icon?: string; items: NavItem[]; defaultOpen?: boolean };

/* ── Icon mapping for Notion-style sidebar ─────────────────────────── */

const navByRole: Record<string, NavSection[]> = {
  owner: [
    {
      section: 'Dashboards', icon: '📊', defaultOpen: true, items: [
        { to: '/owner', label: 'Owner', icon: '👑' },
        { to: '/ceo', label: 'CEO', icon: '📈' },
        { to: '/ceo/employees', label: 'Employees & Payroll', icon: '👷' },
      ],
    },
    {
      section: 'Production', icon: '🏭', defaultOpen: true, items: [
        { to: '/manager', label: 'Manager', icon: '📋' },
        { to: '/manager/schedule', label: 'Schedule', icon: '📅' },
        { to: '/manager/kilns', label: 'Kilns', icon: '🔥' },
        { to: '/manager/materials', label: 'Materials (Mgr)', icon: '📦' },
        { to: '/manager/grinding', label: 'Grinding', icon: '⚙️' },
        { to: '/tablo', label: 'Tablo', icon: '📺' },
      ],
    },
    {
      section: 'Kilns', icon: '🔥', items: [
        { to: '/manager/kiln-inspections', label: 'Inspections', icon: '🔍' },
        { to: '/manager/kiln-maintenance', label: 'Maintenance', icon: '🔧' },
        { to: '/admin/firing-profiles', label: 'Firing Profiles', icon: '📈' },
        { to: '/admin/temperature-groups', label: 'Temp Groups', icon: '🌡' },
        { to: '/admin/firing-schedules', label: 'Firing Schedules', icon: '🗓' },
      ],
    },
    {
      section: 'Materials & Recipes', icon: '🎨', items: [
        { to: '/admin/materials', label: 'Materials', icon: '🧪' },
        { to: '/admin/recipes', label: 'Recipes', icon: '📝' },
        { to: '/admin/consumption-rules', label: 'Consumption Rules', icon: '📏' },
        { to: '/admin/colors', label: 'Colors', icon: '🎨' },
        { to: '/admin/collections', label: 'Collections', icon: '📁' },
        { to: '/admin/color-collections', label: 'Color Collections', icon: '🌈' },
      ],
    },
    {
      section: 'Catalog', icon: '📚', items: [
        { to: '/admin/application-types', label: 'Application Types', icon: '✍️' },
        { to: '/admin/places-of-application', label: 'Places of Application', icon: '📍' },
        { to: '/admin/finishing-types', label: 'Finishing Types', icon: '✨' },
        { to: '/admin/suppliers', label: 'Suppliers', icon: '🤝' },
        { to: '/admin/sizes', label: 'Sizes', icon: '📐' },
        { to: '/admin/stages', label: 'Stages', icon: '🔄' },
      ],
    },
    {
      section: 'Warehouse', icon: '📦', items: [
        { to: '/admin/warehouses', label: 'Warehouses', icon: '🏪' },
        { to: '/admin/packaging', label: 'Packaging', icon: '📦' },
        { to: '/warehouse', label: 'Warehouse Dashboard', icon: '📊' },
        { to: '/warehouse/finished-goods', label: 'Finished Goods', icon: '✅' },
        { to: '/warehouse/reconciliations', label: 'Reconciliations', icon: '🔄' },
        { to: '/warehouse/mana-shipments', label: 'Mana Shipments', icon: '🚚' },
      ],
    },
    {
      section: 'Operations', icon: '⚡', items: [
        { to: '/quality', label: 'Quality', icon: '🔬' },
        { to: '/packing', label: 'Sorting & Packing', icon: '📦' },
        { to: '/purchaser', label: 'Purchasing', icon: '🛒' },
        { to: '/reports', label: 'Reports', icon: '📈' },
      ],
    },
    {
      section: 'System', icon: '⚙️', items: [
        { to: '/users', label: 'Users', icon: '👥' },
        { to: '/admin/employees', label: 'Employees', icon: '👷' },
        { to: '/admin', label: 'Admin Panel', icon: '🛠' },
        { to: '/admin/dashboard-access', label: 'Dashboard Access', icon: '🔐' },
        { to: '/admin/settings', label: 'Settings', icon: '⚙️' },
        { to: '/admin/factory-calendar', label: 'Factory Calendar', icon: '🗓' },
      ],
    },
  ],
  administrator: [
    {
      section: 'Admin', icon: '🛠', defaultOpen: true, items: [
        { to: '/admin', label: 'Admin Panel', icon: '🛠' },
        { to: '/users', label: 'Users', icon: '👥' },
        { to: '/admin/employees', label: 'Employees', icon: '👷' },
        { to: '/ceo/employees', label: 'Payroll', icon: '💰' },
        { to: '/admin/dashboard-access', label: 'Dashboard Access', icon: '🔐' },
        { to: '/admin/settings', label: 'Settings', icon: '⚙️' },
      ],
    },
    {
      section: 'Catalog', icon: '📚', items: [
        { to: '/admin/materials', label: 'Materials', icon: '🧪' },
        { to: '/admin/recipes', label: 'Recipes', icon: '📝' },
        { to: '/admin/firing-profiles', label: 'Firing Profiles', icon: '📈' },
        { to: '/admin/temperature-groups', label: 'Temperature Groups', icon: '🌡' },
        { to: '/admin/colors', label: 'Colors', icon: '🎨' },
        { to: '/admin/collections', label: 'Collections', icon: '📁' },
        { to: '/admin/suppliers', label: 'Suppliers', icon: '🤝' },
        { to: '/admin/warehouses', label: 'Warehouses', icon: '🏪' },
        { to: '/admin/packaging', label: 'Packaging', icon: '📦' },
        { to: '/admin/sizes', label: 'Sizes', icon: '📐' },
        { to: '/admin/stages', label: 'Stages', icon: '🔄' },
        { to: '/admin/firing-schedules', label: 'Firing Schedules', icon: '🗓' },
      ],
    },
    {
      section: 'Settings', icon: '⚙️', items: [
        { to: '/admin/consumption-rules', label: 'Consumption Rules', icon: '📏' },
        { to: '/admin/factory-calendar', label: 'Factory Calendar', icon: '🗓' },
        { to: '/warehouse/reconciliations', label: 'Reconciliations', icon: '🔄' },
      ],
    },
  ],
  ceo: [
    {
      section: 'CEO', icon: '📊', defaultOpen: true, items: [
        { to: '/ceo', label: 'Dashboard', icon: '📊' },
        { to: '/ceo/employees', label: 'Employees', icon: '👷' },
        { to: '/reports', label: 'Reports', icon: '📈' },
        { to: '/tablo', label: 'Tablo', icon: '📺' },
        { to: '/users', label: 'Users', icon: '👥' },
      ],
    },
  ],
  production_manager: [
    {
      section: 'Production', icon: '📊', defaultOpen: true, items: [
        { to: '/manager', label: 'Dashboard', icon: '📋' },
        { to: '/manager/schedule', label: 'Schedule', icon: '📅' },
        { to: '/manager/staff', label: 'Staff', icon: '👷' },
        { to: '/tablo', label: 'Tablo', icon: '📺' },
      ],
    },
    {
      section: 'Kilns', icon: '🔥', defaultOpen: true, items: [
        { to: '/manager/kilns', label: 'Kilns', icon: '🏭' },
        { to: '/manager/kiln-inspections', label: 'Inspections', icon: '🔍' },
        { to: '/manager/kiln-maintenance', label: 'Maintenance', icon: '🔧' },
        { to: '/admin/firing-profiles', label: 'Firing Profiles', icon: '📈' },
        { to: '/admin/temperature-groups', label: 'Temp Groups', icon: '🌡' },
      ],
    },
    {
      section: 'Materials', icon: '🎨', defaultOpen: true, items: [
        { to: '/manager/materials', label: 'Materials', icon: '🧪' },
        { to: '/admin/recipes', label: 'Recipes', icon: '📝' },
        { to: '/admin/consumption-rules', label: 'Consumption Rules', icon: '📏' },
        { to: '/manager/grinding', label: 'Grinding', icon: '⚙️' },
      ],
    },
    {
      section: 'Warehouse', icon: '📦', items: [
        { to: '/admin/warehouses', label: 'Warehouses', icon: '🏪' },
        { to: '/admin/packaging', label: 'Packaging', icon: '📦' },
        { to: '/admin/sizes', label: 'Sizes', icon: '📐' },
        { to: '/warehouse/finished-goods', label: 'Finished Goods', icon: '✅' },
        { to: '/warehouse/reconciliations', label: 'Reconciliations', icon: '🔄' },
        { to: '/warehouse/mana-shipments', label: 'Mana Shipments', icon: '🚚' },
      ],
    },
    {
      section: 'Planning', icon: '📅', items: [
        { to: '/admin/factory-calendar', label: 'Factory Calendar', icon: '🗓' },
        { to: '/reports', label: 'Reports', icon: '📈' },
      ],
    },
    {
      section: 'Help', icon: '📖', items: [
        { to: '/manager/guide', label: 'Guide', icon: '📚' },
      ],
    },
  ],
  quality_manager: [
    {
      section: 'Quality', icon: '🔬', defaultOpen: true, items: [
        { to: '/quality', label: 'Quality Dashboard', icon: '🔬' },
      ],
    },
  ],
  warehouse: [
    {
      section: 'Warehouse', icon: '📦', defaultOpen: true, items: [
        { to: '/warehouse', label: 'Dashboard', icon: '📊' },
        { to: '/warehouse/finished-goods', label: 'Finished Goods', icon: '✅' },
        { to: '/warehouse/reconciliations', label: 'Reconciliations', icon: '🔄' },
        { to: '/warehouse/mana-shipments', label: 'Mana Shipments', icon: '🚚' },
      ],
    },
  ],
  sorter_packer: [
    {
      section: 'Packing', icon: '📦', defaultOpen: true, items: [
        { to: '/packing', label: 'Sorting & Packing', icon: '📦' },
      ],
    },
  ],
  purchaser: [
    {
      section: 'Purchasing', icon: '🛒', defaultOpen: true, items: [
        { to: '/purchaser', label: 'Purchasing', icon: '🛒' },
      ],
    },
  ],
};

/* ── Collapsible Section ───────────────────────────────────────────── */

function SidebarSection({
  section,
  sidebarOpen,
}: {
  section: NavSection;
  sidebarOpen: boolean;
}) {
  const [expanded, setExpanded] = useState(section.defaultOpen ?? false);

  if (!sidebarOpen) {
    // Collapsed sidebar: show divider between sections
    return (
      <>
        <div className="my-1 border-t border-gray-100" />
        {section.items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            title={item.label}
            className={({ isActive }) =>
              cn(
                'flex items-center justify-center rounded-md p-2 text-lg transition-colors',
                isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:bg-gray-100',
              )
            }
          >
            {item.icon || item.label[0]}
          </NavLink>
        ))}
      </>
    );
  }

  return (
    <div className="mb-0.5">
      {/* Section header — clickable to collapse/expand */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-gray-400 hover:bg-gray-50 hover:text-gray-600 transition-colors"
      >
        <span className="text-sm">{section.icon}</span>
        <span className="flex-1 text-left">{section.section}</span>
        <span className={cn('text-[10px] text-gray-300 transition-transform', expanded ? 'rotate-0' : '-rotate-90')}>
          ▼
        </span>
      </button>

      {/* Items */}
      {expanded && (
        <div className="ml-1 space-y-0.5">
          {section.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                )
              }
            >
              <span className="w-5 text-center text-sm">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Main Sidebar ──────────────────────────────────────────────────── */

export function Sidebar() {
  const user = useAuthStore((s) => s.user);
  const { sidebarOpen, toggleSidebar } = useUiStore();
  const sections = user ? navByRole[user.role] || [] : [];

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-white transition-all',
        sidebarOpen ? 'w-60' : 'w-14',
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center justify-between border-b px-3">
        {sidebarOpen && (
          <span className="text-lg font-semibold">
            <span className="text-blue-600">Moonjar</span>{' '}
            <span className="font-bold text-gray-900">PMS</span>
          </span>
        )}
        <button
          onClick={toggleSidebar}
          className="rounded p-1 text-gray-400 hover:bg-gray-100"
        >
          {sidebarOpen ? '←' : '→'}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-1.5 py-2">
        {sections.map((section) => (
          <SidebarSection
            key={section.section}
            section={section}
            sidebarOpen={sidebarOpen}
          />
        ))}
      </nav>
    </aside>
  );
}
