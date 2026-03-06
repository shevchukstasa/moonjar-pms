import { cn } from '@/lib/cn';

export function Tabs({ tabs, activeTab, onChange }: { tabs: { id: string; label: string }[]; activeTab: string; onChange: (id: string) => void }) {
  return (
    <div className="flex gap-1 border-b border-gray-200">
      {tabs.map((t) => <button key={t.id} onClick={() => onChange(t.id)} className={cn('px-4 py-2 text-sm font-medium transition-colors', activeTab === t.id ? 'border-b-2 border-primary-500 text-primary-600' : 'text-gray-500 hover:text-gray-700')}>{t.label}</button>)}
    </div>
  );
}
