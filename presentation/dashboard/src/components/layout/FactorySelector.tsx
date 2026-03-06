import { useUiStore } from '@/stores/uiStore';

const factories = [{ id: '', label: 'All Factories' }, { id: 'bali', label: 'Bali' }, { id: 'java', label: 'Java' }];

export function FactorySelector() {
  const { activeFactoryId, setActiveFactory } = useUiStore();
  return <select value={activeFactoryId || ''} onChange={(e) => setActiveFactory(e.target.value || null)} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm">{factories.map((f) => <option key={f.id} value={f.id}>{f.label}</option>)}</select>;
}
