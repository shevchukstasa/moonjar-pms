import { useEffect } from 'react';
import { useUiStore } from '@/stores/uiStore';
import { useFactories } from '@/hooks/useFactories';
import { useCurrentUser } from '@/hooks/useCurrentUser';

// Roles that can see ALL factories regardless of assignment
const GLOBAL_ROLES = new Set(['owner', 'administrator', 'ceo']);

export function FactorySelector() {
  const { activeFactoryId, setActiveFactory } = useUiStore();
  const { data } = useFactories();
  const user = useCurrentUser();
  const allFactories = data?.items || [];

  const role = user?.role ?? '';
  const isGlobalRole = GLOBAL_ROLES.has(role);
  const userFactoryIds = user?.factories?.map((f) => f.id) ?? [];

  // Global roles (owner, admin, ceo) → see all factories.
  // Other roles → see ONLY their assigned factories. If none assigned, show nothing.
  const factories = isGlobalRole
    ? allFactories
    : allFactories.filter((f) => userFactoryIds.includes(f.id));

  // Auto-select when the user has exactly one accessible factory and nothing is selected yet.
  // This ensures PMs assigned to a single factory always have a factory context,
  // which is required for cleanup-permission buttons to appear.
  useEffect(() => {
    if (!activeFactoryId && factories.length === 1) {
      setActiveFactory(factories[0].id);
    }
  }, [factories, activeFactoryId, setActiveFactory]);

  // Non-global roles with exactly one factory — no need to show selector at all
  if (!isGlobalRole && factories.length <= 1) {
    return null;
  }

  return (
    <select
      value={activeFactoryId || ''}
      onChange={(e) => setActiveFactory(e.target.value || null)}
      className="w-full sm:w-auto rounded-md border border-gray-300 px-3 py-2 md:py-1.5 text-sm min-h-[44px] md:min-h-0"
    >
      {isGlobalRole && <option value="">All Factories</option>}
      {factories.map((f) => (
        <option key={f.id} value={f.id}>{f.name}</option>
      ))}
    </select>
  );
}
