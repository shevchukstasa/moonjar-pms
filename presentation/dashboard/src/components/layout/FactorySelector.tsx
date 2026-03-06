import { useUiStore } from '@/stores/uiStore';
import { useFactories } from '@/hooks/useFactories';

export function FactorySelector() {
  const { activeFactoryId, setActiveFactory } = useUiStore();
  const { data } = useFactories();
  const factories = data?.items || [];

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
