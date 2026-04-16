/**
 * Daily Production View — visual calendar showing what to do each day per stage.
 * Consumes GET /schedule/production-schedule endpoint.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProductionSchedule } from '@/hooks/useSchedule';
import { Spinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';

interface StageSlice {
  stage: string;
  day_index: number;   // 1-based
  total_days: number;
  qty_per_day?: number | null;
  sqm_per_day?: number | null;
}

interface PositionItem {
  id: string;
  order_number?: string;
  client?: string;
  color?: string;
  size?: string;
  quantity?: number;
  quantity_sqm?: number;
  area_sqm?: number;
  status?: string;
  product_type?: string;
  collection?: string;
  batch_id?: string;
  stage_slice?: StageSlice | null;
}

interface BatchItem {
  id: string;
  kiln_name?: string;
  positions_count?: number;
  total_sqm?: number;
  status?: string;
}

interface DaySection {
  glazing: PositionItem[];
  kiln_loading: PositionItem[];
  firing: BatchItem[];
  cooling: BatchItem[];
  sorting: PositionItem[];
  qc: PositionItem[];
}

interface DayData {
  date: string;
  weekday: string;
  is_working_day: boolean;
  holiday_name?: string | null;
  sections: DaySection;
  metrics: {
    total_positions: number;
    total_sqm: number;
    batches_count: number;
  };
}

const SECTION_CONFIG = [
  { key: 'glazing' as const, label: 'Glazing', color: 'bg-blue-500', lightBg: 'bg-blue-50', border: 'border-blue-200' },
  { key: 'kiln_loading' as const, label: 'Kiln Loading', color: 'bg-orange-500', lightBg: 'bg-orange-50', border: 'border-orange-200' },
  { key: 'firing' as const, label: 'Firing', color: 'bg-red-500', lightBg: 'bg-red-50', border: 'border-red-200' },
  { key: 'cooling' as const, label: 'Cooling', color: 'bg-amber-500', lightBg: 'bg-amber-50', border: 'border-amber-200' },
  { key: 'sorting' as const, label: 'Sorting', color: 'bg-green-500', lightBg: 'bg-green-50', border: 'border-green-200' },
  { key: 'qc' as const, label: 'QC', color: 'bg-purple-500', lightBg: 'bg-purple-50', border: 'border-purple-200' },
];

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
}

function isToday(dateStr: string): boolean {
  // Use local date — toISOString() returns UTC and drifts a day off
  // for users in UTC+7/+8 (WITA/WIB) past midnight.
  const d = new Date();
  const local = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  return dateStr === local;
}

function StatusBadge({ status }: { status?: string }) {
  if (!status) return null;
  const colors: Record<string, string> = {
    planned: 'bg-gray-100 text-gray-700',
    in_production: 'bg-blue-100 text-blue-700',
    insufficient_materials: 'bg-red-100 text-red-700',
    awaiting_recipe: 'bg-amber-100 text-amber-700',
    glazed: 'bg-green-100 text-green-700',
    fired: 'bg-orange-100 text-orange-700',
  };
  const c = colors[status] || 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${c}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}

function PositionCard({ item, onClick }: { item: PositionItem; onClick?: () => void }) {
  const slice = item.stage_slice;
  // Multi-day stage slice: show the per-day portion instead of the total.
  // Falls back to full position qty when no stage_plan exists yet.
  const dayQty =
    slice && slice.qty_per_day != null
      ? Math.round(Number(slice.qty_per_day))
      : item.quantity || 0;
  const daySqm =
    slice && slice.sqm_per_day != null
      ? Number(slice.sqm_per_day)
      : item.quantity_sqm != null
      ? Number(item.quantity_sqm)
      : item.area_sqm != null
      ? Number(item.area_sqm)
      : null;
  const multiDay = !!(slice && slice.total_days > 1);

  return (
    <div
      onClick={onClick}
      className="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs shadow-sm transition hover:shadow cursor-pointer"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-gray-900 truncate">{item.color || '—'}</span>
          {item.size && <span className="text-gray-400">{item.size}</span>}
          {multiDay && (
            <span className="rounded bg-blue-100 px-1 py-0.5 text-[9px] font-medium text-blue-700">
              day {slice!.day_index}/{slice!.total_days}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-gray-500 mt-0.5">
          <span>#{item.order_number}</span>
          {item.client && <span className="truncate max-w-[80px]">{item.client}</span>}
          {multiDay && item.quantity ? (
            <span className="text-gray-400">of {item.quantity}</span>
          ) : null}
        </div>
      </div>
      <div className="text-right shrink-0">
        <div className="font-medium text-gray-700">{dayQty} pcs</div>
        {daySqm != null ? (
          <div className="text-[10px] text-gray-400">{daySqm.toFixed(2)} m²</div>
        ) : null}
      </div>
      <StatusBadge status={item.status} />
    </div>
  );
}

function BatchCard({ item }: { item: BatchItem }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs shadow-sm">
      <div className="min-w-0 flex-1">
        <span className="font-semibold text-gray-900">{item.kiln_name || 'Kiln'}</span>
        <div className="text-[10px] text-gray-500">{item.positions_count || 0} positions</div>
      </div>
      <div className="text-right shrink-0">
        {item.total_sqm ? (
          <div className="font-medium text-gray-700">{Number(item.total_sqm).toFixed(2)} m²</div>
        ) : null}
      </div>
      <StatusBadge status={item.status} />
    </div>
  );
}

function DayColumn({ day }: { day: DayData }) {
  const navigate = useNavigate();
  const today = isToday(day.date);
  const empty = day.metrics.total_positions === 0 && day.metrics.batches_count === 0;

  return (
    <div
      className={`flex-shrink-0 w-[280px] rounded-xl border ${
        today ? 'border-blue-400 ring-2 ring-blue-200' : 'border-gray-200'
      } ${!day.is_working_day ? 'opacity-60' : ''} bg-white overflow-hidden`}
    >
      {/* Day header */}
      <div className={`px-3 py-2 ${today ? 'bg-blue-600 text-white' : 'bg-gray-50'} border-b`}>
        <div className="flex items-center justify-between">
          <div>
            <span className={`text-sm font-bold ${today ? 'text-white' : 'text-gray-900'}`}>
              {formatDate(day.date)}
            </span>
            <span className={`ml-1.5 text-xs ${today ? 'text-blue-100' : 'text-gray-500'}`}>
              {day.weekday.slice(0, 3)}
            </span>
          </div>
          {today && (
            <span className="rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-bold">
              TODAY
            </span>
          )}
          {day.holiday_name && (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] text-amber-800">
              {day.holiday_name}
            </span>
          )}
        </div>
        {!empty && (
          <div className={`text-[10px] mt-0.5 ${today ? 'text-blue-100' : 'text-gray-400'}`}>
            {day.metrics.total_positions} pos. · {day.metrics.total_sqm} m² · {day.metrics.batches_count} firings
          </div>
        )}
      </div>

      {/* Sections */}
      <div className="p-2 space-y-2 max-h-[600px] overflow-y-auto">
        {empty ? (
          <div className="py-8 text-center text-xs text-gray-400">
            {day.is_working_day ? 'No scheduled work' : 'Day off'}
          </div>
        ) : (
          SECTION_CONFIG.map((sec) => {
            const items = day.sections[sec.key];
            if (!items || items.length === 0) return null;

            return (
              <div key={sec.key} className={`rounded-lg ${sec.lightBg} ${sec.border} border p-2`}>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <div className={`w-2 h-2 rounded-full ${sec.color}`} />
                  <span className="text-[11px] font-semibold text-gray-700">
                    {sec.label}
                  </span>
                  <span className="ml-auto text-[10px] text-gray-400">
                    {items.length}
                  </span>
                </div>
                <div className="space-y-1">
                  {sec.key === 'firing' || sec.key === 'cooling'
                    ? (items as BatchItem[]).map((b) => (
                        <BatchCard key={b.id} item={b} />
                      ))
                    : (items as PositionItem[]).map((p) => (
                        <PositionCard
                          key={p.id}
                          item={p}
                          onClick={() => {
                            // Navigate to order detail if order_number exists
                            // Positions don't have a direct detail page, use order
                          }}
                        />
                      ))
                  }
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

interface Props {
  factoryId?: string | null;
}

export default function DailyProductionView({ factoryId }: Props) {
  const [days, setDays] = useState(14);
  const { data, isLoading, isError } = useProductionSchedule(factoryId, days);

  if (!factoryId) {
    return (
      <div className="py-12 text-center text-sm text-gray-500">
        Select a factory to view the production schedule
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center text-sm text-red-700">
        Error loading production schedule
      </div>
    );
  }

  const schedule = data as {
    days: DayData[];
    warnings: string[];
    summary: {
      total_positions_scheduled: number;
      total_batches: number;
      days_with_work: number;
    };
  };

  const daysData = schedule?.days || [];
  const summary = schedule?.summary;
  const warnings = schedule?.warnings || [];

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-700">Horizon:</h3>
          {[3, 7, 14].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                days === d
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {d} days
            </button>
          ))}
        </div>
        {summary && (
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>{summary.total_positions_scheduled} positions scheduled</span>
            <span>{summary.total_batches} firings</span>
            <span>{summary.days_with_work} working days</span>
          </div>
        )}
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="text-xs font-semibold text-amber-800 mb-1">⚠ Warnings</div>
          <div className="space-y-0.5">
            {warnings.slice(0, 5).map((w, i) => (
              <div key={i} className="text-xs text-amber-700">{w}</div>
            ))}
            {warnings.length > 5 && (
              <div className="text-xs text-amber-500">... and {warnings.length - 5} more</div>
            )}
          </div>
        </div>
      )}

      {/* Timeline — horizontal scroll */}
      <div className="flex gap-3 overflow-x-auto pb-4 -mx-2 px-2">
        {daysData.map((day) => (
          <DayColumn key={day.date} day={day} />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 pt-2 border-t border-gray-100">
        {SECTION_CONFIG.map((sec) => (
          <div key={sec.key} className="flex items-center gap-1.5 text-xs text-gray-500">
            <div className={`w-2.5 h-2.5 rounded-full ${sec.color}`} />
            {sec.label}
          </div>
        ))}
      </div>
    </div>
  );
}
