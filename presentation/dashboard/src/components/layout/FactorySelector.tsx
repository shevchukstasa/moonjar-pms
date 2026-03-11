import { useEffect } from 'react';
import { useUiStore } from '@/stores/uiStore';
import { useFactories } from '@/hooks/useFactories';

export function FactorySelector() {
  const { activeFactoryId, setActiveFactory } = useUiStore();
  const { data } = useFactories();
  const factories = data?.items || [];

  // Auto-select when there is exactly one factory and nothing is selected yet
  useEffect(() => {
    if (!activeFactoryId && factories.length === 1) {
      setActiveFactory(factories[0].id);
    }
  }, [factories, activeFactoryId, setActiveFactory]);

  return (
    <select
      value={activeFactoryId || ''}
      onChange={(e) => setActiveFactory(e.target.value || null)}
      className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
    >
      <option value="">All Factories</option>
      {factories.map((f) => (
        <option key={f.id} value={f.id}>{f.name}</option>
      ))}
    </select>
  );
}
