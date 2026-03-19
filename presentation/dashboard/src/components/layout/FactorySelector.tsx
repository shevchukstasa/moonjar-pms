import { useEffect } from 'react';
import { useUiStore } from '@/stores/uiStore';
import { useFactories } from '@/hooks/useFactories';
import { useCurrentUser } from '@/hooks/useCurrentUser';

export function FactorySelector() {
  const { activeFactoryId, setActiveFactory } = useUiStore();
  const { data } = useFactories();
  const user = useCurrentUser();
  const allFactories = data?.items || [];

  // For non-admin roles that have factory assignments, show only their factories.
  // Admin/owner/ceo with no factory list → show all factories.
  const userFactoryIds = user?.factories?.map((f) => f.id) ?? [];
  const factories =
    userFactoryIds.length > 0
      ? allFactories.filter((f) => userFactoryIds.includes(f.id))
      : allFactories;

  // Auto-select when the user has exactly one accessible factory and nothing is selected yet.
  // This ensures PMs assigned to a single factory always have a factory context,
  // which is required for cleanup-permission buttons to appear.
  useEffect(() => {
    if (!activeFactoryId && factories.length === 1) {
      setActiveFactory(factories[0].id);
    }
  }, [factories, activeFactoryId, setActiveFactory]);

  return (
    <select
      value={activeFactoryId || ''}
      onChange={(e) => setActiveFactory(e.target.value || null)}
      className="w-full sm:w-auto rounded-md border border-gray-300 px-3 py-2 md:py-1.5 text-sm min-h-[44px] md:min-h-0"
    >
      <option value="">All Factories</option>
      {factories.map((f) => (
        <option key={f.id} value={f.id}>{f.name}</option>
      ))}
    </select>
  );
}
