import { cn } from '@/lib/cn';

export function Tabs({ tabs, activeTab, onChange }: { tabs: { id: string; label: string }[]; activeTab: string; onChange: (id: string) => void }) {
  return (
    <div className="overflow-x-auto -mx-1 scrollbar-hide">
      <div className="flex gap-1 border-b border-gray-200 min-w-max px-1">
        {tabs.map((t) => <button key={t.id} onClick={() => onChange(t.id)} className={cn('px-3 py-2.5 text-sm font-medium transition-colors whitespace-nowrap min-h-[44px]', activeTab === t.id ? 'border-b-2 border-primary-500 text-primary-600' : 'text-gray-500 hover:text-gray-700')}>{t.label}</button>)}
      </div>
    </div>
  );
}
