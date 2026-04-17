/**
 * Plan vs Fact — daily production tracking per stage.
 *
 * Shows planned qty, actual qty, carryover, and cumulative progress
 * for each position across engobe, glazing, edge cleaning, kiln loading.
 * Color-coded: green (>= plan), yellow (80-99%), red (<80%).
 *
 * Consumes GET /schedule/daily-plan
 */
import { useState, useMemo } from 'react';
import { useDailyPlan } from '@/hooks/useSchedule';
import { Spinner } from '@/components/ui/Spinner';
import { Card } from '@/components/ui/Card';

// ── Types ───────────────────────────────────────────────────────

interface PositionRow {
  position_id: string;
  position_label: string;
  order_number: string;
  client?: string | null;
  color: string;
  size: string;
  collection?: string | null;
  total_qty: number;
  planned_today: number;
  actual_today: number;
  carryover: number;
  cumulative_done: number;
  remaining: number;
  status: string;
}

interface StageTotals {
  planned: number;
  actual: number;
  carryover: number;
}

interface StageData {
  stage: string;
  stage_label: string;
  daily_capacity: number;
  positions: PositionRow[];
  totals: StageTotals;
}

interface DailyPlanResponse {
  date: string;
  factory_id: string;
  stages: StageData[];
}

// ── Helpers ─────────────────────────────────────────────────────

function todayLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Color class for the plan/fact ratio cell */
function ratioColor(planned: number, actual: number): string {
  if (planned === 0) return '';
  const pct = (actual / planned) * 100;
  if (pct >= 100) return 'bg-emerald-50 text-emerald-800';
  if (pct >= 80) return 'bg-amber-50 text-amber-800';
  return 'bg-red-50 text-red-800';
}

/** Badge class for carryover */
function carryoverBadge(val: number): string {
  if (val === 0) return 'text-gray-400';
  return 'font-semibold text-red-600';
}

/** Progress bar percent */
function progressPct(done: number, total: number): number {
  if (total <= 0) return 0;
  return Math.min(100, Math.round((done / total) * 100));
}

// Stage color accents
const STAGE_COLORS: Record<string, { bg: string; border: string; dot: string; headerBg: string }> = {
  engobe: { bg: 'bg-sky-50', border: 'border-sky-200', dot: 'bg-sky-500', headerBg: 'bg-sky-100' },
  glazing: { bg: 'bg-blue-50', border: 'border-blue-200', dot: 'bg-blue-500', headerBg: 'bg-blue-100' },
  edge_cleaning_loading: { bg: 'bg-violet-50', border: 'border-violet-200', dot: 'bg-violet-500', headerBg: 'bg-violet-100' },
  kiln_loading: { bg: 'bg-orange-50', border: 'border-orange-200', dot: 'bg-orange-500', headerBg: 'bg-orange-100' },
};

const FALLBACK_COLORS = { bg: 'bg-gray-50', border: 'border-gray-200', dot: 'bg-gray-500', headerBg: 'bg-gray-100' };

// ── Stage cascade arrows ────────────────────────────────────────

function CascadeArrow() {
  return (
    <div className="flex justify-center py-1">
      <svg width="24" height="20" viewBox="0 0 24 20" className="text-gray-300">
        <path d="M12 0 L12 14 M6 10 L12 16 L18 10" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

// ── Stage table component ───────────────────────────────────────

function StageTable({ stage }: { stage: StageData }) {
  const colors = STAGE_COLORS[stage.stage] || FALLBACK_COLORS;
  const hasPositions = stage.positions.length > 0;
  const totals = stage.totals;
  const totalRatioClass = ratioColor(totals.planned, totals.actual);

  return (
    <div className={`rounded-xl border ${colors.border} overflow-hidden`}>
      {/* Stage header */}
      <div className={`flex items-center justify-between px-4 py-2.5 ${colors.headerBg}`}>
        <div className="flex items-center gap-2">
          <div className={`h-3 w-3 rounded-full ${colors.dot}`} />
          <h3 className="text-sm font-bold text-gray-800">{stage.stage_label}</h3>
          {stage.daily_capacity > 0 && (
            <span className="text-xs text-gray-500">
              cap: {Math.round(stage.daily_capacity)} pcs/day
            </span>
          )}
        </div>
        {hasPositions && (
          <div className="flex items-center gap-4 text-xs">
            <span className="text-gray-600">
              Plan: <span className="font-semibold">{totals.planned}</span>
            </span>
            <span className={`rounded px-1.5 py-0.5 font-semibold ${totalRatioClass}`}>
              Fact: {totals.actual}
            </span>
            <span className={carryoverBadge(totals.carryover)}>
              Carry: {totals.carryover}
            </span>
          </div>
        )}
      </div>

      {/* Positions table */}
      {!hasPositions ? (
        <div className={`px-4 py-6 text-center text-xs text-gray-400 ${colors.bg}`}>
          No work planned for this stage today
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className={`text-[11px] font-medium uppercase text-gray-500 ${colors.bg}`}>
              <tr>
                <th className="px-3 py-2 w-16">#</th>
                <th className="px-3 py-2">Order</th>
                <th className="px-3 py-2">Color</th>
                <th className="px-3 py-2 w-16">Size</th>
                <th className="px-3 py-2 w-16 text-right">Total</th>
                <th className="px-3 py-2 w-20 text-right">Plan</th>
                <th className="px-3 py-2 w-20 text-right">Fact</th>
                <th className="px-3 py-2 w-20 text-right">Carry</th>
                <th className="px-3 py-2 w-36">Progress</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {stage.positions.map((pos) => {
                const cellClass = ratioColor(pos.planned_today, pos.actual_today);
                const pct = progressPct(pos.cumulative_done, pos.total_qty);

                return (
                  <tr key={pos.position_id} className="bg-white hover:bg-gray-50/50 transition-colors">
                    <td className="px-3 py-2">
                      <span className="font-mono text-xs font-semibold text-gray-700">{pos.position_label}</span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="text-xs font-medium text-gray-900">{pos.order_number}</div>
                      {pos.client && (
                        <div className="text-[10px] text-gray-400 truncate max-w-[120px]">{pos.client}</div>
                      )}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-700">{pos.color}</td>
                    <td className="px-3 py-2 text-xs text-gray-500">{pos.size}</td>
                    <td className="px-3 py-2 text-right text-xs text-gray-600">{pos.total_qty}</td>
                    <td className="px-3 py-2 text-right">
                      <span className="text-xs font-semibold text-gray-800">{pos.planned_today}</span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-semibold ${cellClass}`}>
                        {pos.actual_today}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className={`text-xs ${carryoverBadge(pos.carryover)}`}>{pos.carryover}</span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              pct >= 100 ? 'bg-emerald-500' : pct >= 50 ? 'bg-blue-500' : 'bg-amber-500'
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-gray-400 w-10 text-right">{pct}%</span>
                      </div>
                      <div className="text-[10px] text-gray-400 mt-0.5">
                        {pos.cumulative_done}/{pos.total_qty} done
                        {pos.remaining > 0 && <span className="ml-1">({pos.remaining} left)</span>}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            {/* Totals row */}
            <tfoot>
              <tr className={`text-xs font-semibold ${colors.bg}`}>
                <td className="px-3 py-2" colSpan={5} />
                <td className="px-3 py-2 text-right">{totals.planned}</td>
                <td className="px-3 py-2 text-right">
                  <span className={`inline-block rounded px-1.5 py-0.5 ${totalRatioClass}`}>
                    {totals.actual}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">
                  <span className={carryoverBadge(totals.carryover)}>{totals.carryover}</span>
                </td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────

interface Props {
  factoryId?: string | null;
}

export default function PlanVsFactView({ factoryId }: Props) {
  const [selectedDate, setSelectedDate] = useState(todayLocal);
  const { data, isLoading, isError } = useDailyPlan(factoryId, selectedDate);

  // Summary KPIs
  const summary = useMemo(() => {
    if (!data) return null;
    const resp = data as DailyPlanResponse;
    let totalPlan = 0;
    let totalFact = 0;
    let totalCarry = 0;
    let activeStages = 0;
    for (const stage of resp.stages) {
      totalPlan += stage.totals.planned;
      totalFact += stage.totals.actual;
      totalCarry += stage.totals.carryover;
      if (stage.positions.length > 0) activeStages++;
    }
    const fulfillmentPct = totalPlan > 0 ? Math.round((totalFact / totalPlan) * 100) : 0;
    return { totalPlan, totalFact, totalCarry, activeStages, fulfillmentPct };
  }, [data]);

  if (!factoryId) {
    return (
      <div className="py-12 text-center text-sm text-gray-500">
        Select a factory to view Plan vs Fact
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Controls bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-gray-700">Date:</label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={() => setSelectedDate(todayLocal())}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              selectedDate === todayLocal()
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Today
          </button>
          <button
            onClick={() => {
              const d = new Date(selectedDate + 'T00:00:00');
              d.setDate(d.getDate() - 1);
              setSelectedDate(d.toISOString().slice(0, 10));
            }}
            className="rounded-full px-3 py-1 text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition"
          >
            Prev day
          </button>
          <button
            onClick={() => {
              const d = new Date(selectedDate + 'T00:00:00');
              d.setDate(d.getDate() + 1);
              setSelectedDate(d.toISOString().slice(0, 10));
            }}
            className="rounded-full px-3 py-1 text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition"
          >
            Next day
          </button>
        </div>

        {/* Summary KPIs */}
        {summary && summary.totalPlan > 0 && (
          <div className="flex items-center gap-4 text-xs text-gray-600">
            <div>
              Plan: <span className="font-bold text-gray-900">{summary.totalPlan}</span>
            </div>
            <div>
              Fact:{' '}
              <span className={`font-bold ${
                summary.fulfillmentPct >= 100 ? 'text-emerald-700' :
                summary.fulfillmentPct >= 80 ? 'text-amber-700' :
                'text-red-700'
              }`}>
                {summary.totalFact}
              </span>
            </div>
            <div className={`rounded-full px-2.5 py-0.5 font-bold ${
              summary.fulfillmentPct >= 100 ? 'bg-emerald-100 text-emerald-800' :
              summary.fulfillmentPct >= 80 ? 'bg-amber-100 text-amber-800' :
              'bg-red-100 text-red-800'
            }`}>
              {summary.fulfillmentPct}%
            </div>
            {summary.totalCarry > 0 && (
              <div className="text-red-600 font-semibold">
                Carryover: {summary.totalCarry}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Loading / error states */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center text-sm text-red-700">
          Error loading Plan vs Fact data
        </div>
      )}

      {/* Stage tables with cascade arrows */}
      {data && !isLoading && (() => {
        const resp = data as DailyPlanResponse;
        const hasAnyWork = resp.stages.some((s) => s.positions.length > 0);

        if (!hasAnyWork) {
          return (
            <Card>
              <div className="py-12 text-center text-gray-400">
                <div className="text-lg mb-2">No production planned for {selectedDate}</div>
                <div className="text-sm">Select a different date or run schedule recalculation</div>
              </div>
            </Card>
          );
        }

        return (
          <div className="space-y-1">
            {resp.stages.map((stage, idx) => (
              <div key={stage.stage}>
                {idx > 0 && <CascadeArrow />}
                <StageTable stage={stage} />
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}
