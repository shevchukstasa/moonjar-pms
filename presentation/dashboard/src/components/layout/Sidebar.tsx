import { useState, useEffect, useCallback } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useUiStore } from '@/stores/uiStore';
import { cn } from '@/lib/cn';

/* ── Types ──────────────────────────────────────────────────────────── */

type NavItem = { to: string; label: string; icon?: string };
type NavSection = { section: string; icon?: string; items: NavItem[]; defaultOpen?: boolean };

/* ── localStorage helper for section state ─────────────────────────── */

const STORAGE_KEY = 'moonjar-sidebar-sections';

function loadSectionState(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveSectionState(state: Record<string, boolean>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore
  }
}

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
        { to: '/manager/workforce', label: 'Workforce', icon: '🗓️' },
        { to: '/manager/gamification', label: 'Gamification', icon: '🏆' },
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
        { to: '/admin/tps-dashboard', label: 'TPS Dashboard', icon: '⚡' },
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
        { to: '/admin/tps-dashboard', label: 'TPS Dashboard', icon: '⚡' },
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
    {
      section: 'Help', icon: '📖', items: [
        { to: '/admin/guide', label: 'Guide', icon: '📚' },
        { to: '/admin/onboarding', label: 'Onboarding', icon: '🎓' },
      ],
    },
  ],
  ceo: [
    {
      section: 'CEO', icon: '📊', defaultOpen: true, items: [
        { to: '/ceo', label: 'Dashboard', icon: '📊' },
        { to: '/ceo/employees', label: 'Employees', icon: '👷' },
        { to: '/reports', label: 'Reports', icon: '📈' },
        { to: '/manager/gamification', label: 'Gamification', icon: '🏆' },
        { to: '/tablo', label: 'Tablo', icon: '📺' },
        { to: '/users', label: 'Users', icon: '👥' },
      ],
    },
    {
      section: 'Help', icon: '📖', items: [
        { to: '/ceo/guide', label: 'Guide', icon: '📚' },
        { to: '/ceo/onboarding', label: 'Onboarding', icon: '🎓' },
      ],
    },
  ],
  production_manager: [
    {
      section: 'Production', icon: '📊', defaultOpen: true, items: [
        { to: '/manager', label: 'Dashboard', icon: '📋' },
        { to: '/manager/schedule', label: 'Schedule', icon: '📅' },
        { to: '/manager/staff', label: 'Staff', icon: '👷' },
        { to: '/manager/workforce', label: 'Workforce', icon: '🗓️' },
        { to: '/manager/gamification', label: 'Gamification', icon: '🏆' },
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
        { to: '/manager/onboarding', label: 'Onboarding', icon: '🎓' },
      ],
    },
  ],
  quality_manager: [
    {
      section: 'Quality', icon: '🔬', defaultOpen: true, items: [
        { to: '/quality', label: 'Quality Dashboard', icon: '🔬' },
      ],
    },
    {
      section: 'Help', icon: '📖', items: [
        { to: '/quality/guide', label: 'Guide', icon: '📚' },
        { to: '/quality/onboarding', label: 'Onboarding', icon: '🎓' },
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
    {
      section: 'Help', icon: '📖', items: [
        { to: '/warehouse/guide', label: 'Guide', icon: '📚' },
        { to: '/warehouse/onboarding', label: 'Onboarding', icon: '🎓' },
      ],
    },
  ],
  sorter_packer: [
    {
      section: 'Packing', icon: '📦', defaultOpen: true, items: [
        { to: '/packing', label: 'Sorting & Packing', icon: '📦' },
      ],
    },
    {
      section: 'Help', icon: '📖', items: [
        { to: '/packing/guide', label: 'Guide', icon: '📚' },
        { to: '/packing/onboarding', label: 'Onboarding', icon: '🎓' },
      ],
    },
  ],
  purchaser: [
    {
      section: 'Purchasing', icon: '🛒', defaultOpen: true, items: [
        { to: '/purchaser', label: 'Purchasing', icon: '🛒' },
      ],
    },
    {
      section: 'Help', icon: '📖', items: [
        { to: '/purchaser/guide', label: 'Guide', icon: '📚' },
        { to: '/purchaser/onboarding', label: 'Onboarding', icon: '🎓' },
      ],
    },
  ],
};

/* ── Collapsible Section ───────────────────────────────────────────── */

function SidebarSection({
  section,
  sidebarOpen,
  isExpanded,
  onToggle,
}: {
  section: NavSection;
  sidebarOpen: boolean;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  if (!sidebarOpen) {
    // Collapsed sidebar: show divider between sections
    return (
      <>
        <div className="my-1 border-t border-gray-100 dark:border-stone-800" />
        {section.items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            title={item.label}
            className={({ isActive }) =>
              cn(
                'flex items-center justify-center rounded-md p-2 text-base transition-colors',
                isActive ? 'bg-blue-50 text-blue-700 dark:bg-gold-500/10 dark:text-gold-400' : 'text-gray-500 hover:bg-gray-100 dark:text-stone-500 dark:hover:bg-stone-800',
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
        onClick={onToggle}
        className="flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-gray-400 hover:bg-gray-50 hover:text-gray-600 transition-colors dark:text-stone-500 dark:hover:bg-stone-800 dark:hover:text-stone-300"
      >
        <span className="text-xs">{section.icon}</span>
        <span className="flex-1 text-left">{section.section}</span>
        <span className={cn('text-[9px] text-gray-300 transition-transform dark:text-stone-600', isExpanded ? 'rotate-0' : '-rotate-90')}>
          ▼
        </span>
      </button>

      {/* Items */}
      {isExpanded && (
        <div className="ml-1 space-y-px">
          {section.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 rounded-md px-3 py-1 text-[13px] font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700 dark:bg-gold-500/10 dark:text-gold-400'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-stone-400 dark:hover:bg-stone-800 dark:hover:text-stone-200',
                )
              }
            >
              <span className="w-4 text-center text-xs">{item.icon}</span>
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

  // Persistent expanded/collapsed state per section
  const [expandedMap, setExpandedMap] = useState<Record<string, boolean>>(() => {
    const saved = loadSectionState();
    const initial: Record<string, boolean> = {};
    for (const s of sections) {
      initial[s.section] = saved[s.section] ?? s.defaultOpen ?? false;
    }
    return initial;
  });

  // Re-initialize when role/sections change
  useEffect(() => {
    const saved = loadSectionState();
    const initial: Record<string, boolean> = {};
    for (const s of sections) {
      initial[s.section] = saved[s.section] ?? s.defaultOpen ?? false;
    }
    setExpandedMap(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.role]);

  const toggleSection = useCallback((sectionName: string) => {
    setExpandedMap((prev) => {
      const next = { ...prev, [sectionName]: !prev[sectionName] };
      saveSectionState(next);
      return next;
    });
  }, []);

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-white transition-all dark:border-stone-800 dark:bg-stone-950',
        sidebarOpen ? 'w-56' : 'w-14',
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center justify-between border-b px-3 dark:border-stone-800">
        {sidebarOpen && (
          <span className="text-base font-semibold">
            <span className="text-blue-600 dark:text-gold-500">Moonjar</span>{' '}
            <span className="font-bold text-gray-900 dark:text-stone-100">PMS</span>
          </span>
        )}
        <button
          onClick={toggleSidebar}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 dark:text-stone-500 dark:hover:bg-stone-800"
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
            isExpanded={expandedMap[section.section] ?? section.defaultOpen ?? false}
            onToggle={() => toggleSection(section.section)}
          />
        ))}
      </nav>
    </aside>
  );
}
