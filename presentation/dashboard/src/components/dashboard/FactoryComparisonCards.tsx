import type { FactoryComparison } from '@/api/analytics';
import { KpiCard } from './KpiCard';
import { Factory } from 'lucide-react';

interface FactoryComparisonCardsProps {
  data: FactoryComparison[];
}

export function FactoryComparisonCards({ data }: FactoryComparisonCardsProps) {
  if (!data.length) {
    return <p className="text-sm text-gray-500">No factory data available</p>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {data.map((f) => (
        <div key={f.factory_id} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center gap-2">
            <Factory className="h-4 w-4 text-gray-400" />
            <h3 className="font-semibold text-gray-900">{f.factory_name}</h3>
            {f.factory_location && (
              <span className="text-xs text-gray-500">({f.factory_location})</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <KpiCard title="Orders" value={f.orders_in_progress} color="blue" className="p-2" />
            <KpiCard title="Output m²" value={f.output_sqm.toFixed(0)} color="green" className="p-2" />
            <KpiCard title="On-Time" value={`${f.on_time_rate.toFixed(0)}%`} color={f.on_time_rate >= 90 ? 'green' : 'yellow'} className="p-2" />
            <KpiCard title="Defects" value={`${f.defect_rate.toFixed(1)}%`} color={f.defect_rate <= 5 ? 'green' : 'red'} className="p-2" />
          </div>
        </div>
      ))}
    </div>
  );
}
