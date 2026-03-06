import { useTabloStore } from '@/stores/tabloStore';
import { SearchInput } from '@/components/ui/SearchInput';
import { Button } from '@/components/ui/Button';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  // Glazing
  { value: 'planned', label: 'Planned' },
  { value: 'insufficient_materials', label: 'Insufficient Materials' },
  { value: 'awaiting_recipe', label: 'Awaiting Recipe' },
  { value: 'awaiting_color_matching', label: 'Awaiting Color Matching' },
  { value: 'glazed', label: 'Glazed' },
  { value: 'pre_kiln_check', label: 'Pre-Kiln Check' },
  // Firing
  { value: 'loaded_in_kiln', label: 'Loaded in Kiln' },
  { value: 'fired', label: 'Fired' },
  { value: 'refire', label: 'Refire' },
  // Sorting
  { value: 'transferred_to_sorting', label: 'To Sorting' },
  { value: 'packed', label: 'Packed' },
  { value: 'quality_check_done', label: 'QC Done' },
  { value: 'ready_for_shipment', label: 'Ready for Shipment' },
];

export function TabloFilters() {
  const { filters, setFilter, clearFilters, delayUnit, setDelayUnit } = useTabloStore();

  const hasFilters = Object.values(filters).some((v) => v);

  return (
    <div className="flex items-center gap-3">
      <SearchInput
        value={filters.search || ''}
        onChange={(e) => setFilter('search', e.target.value)}
        placeholder="Search order / color..."
        className="w-56"
      />

      <select
        value={filters.status || ''}
        onChange={(e) => setFilter('status', e.target.value)}
        className="rounded-md border border-gray-300 px-3 py-2 text-sm"
      >
        {STATUS_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>

      {/* Delay unit toggle */}
      <div className="flex rounded-md border border-gray-300">
        <button
          onClick={() => setDelayUnit('hours')}
          className={`px-3 py-1.5 text-xs font-medium ${
            delayUnit === 'hours'
              ? 'bg-gray-900 text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          } rounded-l-md`}
        >
          Hours
        </button>
        <button
          onClick={() => setDelayUnit('days')}
          className={`px-3 py-1.5 text-xs font-medium ${
            delayUnit === 'days'
              ? 'bg-gray-900 text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          } rounded-r-md`}
        >
          Days
        </button>
      </div>

      {hasFilters && (
        <Button variant="ghost" size="sm" onClick={clearFilters}>
          Clear
        </Button>
      )}
    </div>
  );
}
