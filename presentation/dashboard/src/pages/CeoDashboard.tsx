import { formatDate } from "@/lib/format";
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3, Clock, AlertTriangle, Percent, Flame, Activity,
  Download, Trash2, Factory, Zap, CalendarDays, Wrench,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { KpiCard } from '@/components/dashboard/KpiCard';
import { BufferHealthTable } from '@/components/dashboard/BufferHealthTable';
import { CriticalPositionsTable } from '@/components/dashboard/CriticalPositionsTable';
import { MaterialDeficitsTable } from '@/components/dashboard/MaterialDeficitsTable';
import { ActivityFeed } from '@/components/dashboard/ActivityFeed';
import { PipelineFunnel } from '@/components/charts/PipelineFunnel';
import { DailyOutputChart } from '@/components/charts/DailyOutputChart';
import { FactoryComparisonCards } from '@/components/dashboard/FactoryComparisonCards';
import {
  useDashboardSummary,
  useProductionMetrics,
  useMaterialMetrics,
  useBufferHealth,
  useActivityFeed,
  useFactoryComparison,
} from '@/hooks/useAnalytics';
import { useFactory } from '@/hooks/useFactory';
import { useFactories } from '@/hooks/useFactories';
import { useKilns, type KilnItem } from '@/hooks/useKilns';
import { useTasks } from '@/hooks/useTasks';
import { useKilnSchedule } from '@/hooks/useSchedule';
import { useChangeRequests } from '@/hooks/useOrders';
import { kilnShelvesApi, SHELF_MATERIALS, type ShelfAnalytics } from '@/api/tpsDashboard';
import apiClient from '@/api/client';
import type { FactoryComparison } from '@/api/analytics';
import type { TaskItem } from '@/api/tasks';
import { cn } from '@/lib/cn';

// ---------------------------------------------------------------------------
// Cleanup Permissions (CEO-only feature)
// ---------------------------------------------------------------------------
function CleanupPermissionsCard({ factoryId }: { factoryId: string | null }) {
  const [canDeleteTasks, setCanDeleteTasks] = useState(false);
  const [canDeletePositions, setCanDeletePositions] = useState(false);
  const [canDeleteOrders, setCanDeleteOrders] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!factoryId) return;
    apiClient.get('/cleanup/permissions', { params: { factory_id: factoryId } })
      .then((r) => {
        setCanDeleteTasks(r.data.pm_can_delete_tasks);
        setCanDeletePositions(r.data.pm_can_delete_positions);
        setCanDeleteOrders(r.data.pm_can_delete_orders);
      })
      .catch(() => {});
  }, [factoryId]);

  const toggle = async (field: 'pm_can_delete_tasks' | 'pm_can_delete_positions' | 'pm_can_delete_orders', value: boolean) => {
    if (!factoryId) return;
    setSaving(true);
    try {
      const r = await apiClient.patch('/cleanup/permissions', {
        factory_id: factoryId,
        [field]: value,
      });
      setCanDeleteTasks(r.data.pm_can_delete_tasks);
      setCanDeletePositions(r.data.pm_can_delete_positions);
      setCanDeleteOrders(r.data.pm_can_delete_orders);
    } finally {
      setSaving(false);
    }
  };

  if (!factoryId) return null;

  return (
    <Card>
      <div className="flex items-center gap-2 mb-3">
        <Trash2 className="h-4 w-4 text-red-500" />
        <span className="text-sm font-semibold text-gray-700">PM Cleanup Permissions</span>
        <span className="ml-auto text-xs text-amber-600 font-medium">Temporary</span>
      </div>
      <div className="space-y-2">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={canDeleteTasks}
            disabled={saving}
            onChange={(e) => toggle('pm_can_delete_tasks', e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
          />
          <span className="text-sm text-gray-700">PM can delete tasks</span>
        </label>
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={canDeletePositions}
            disabled={saving}
            onChange={(e) => toggle('pm_can_delete_positions', e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
          />
          <span className="text-sm text-gray-700">PM can delete positions</span>
        </label>
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={canDeleteOrders}
            disabled={saving}
            onChange={(e) => toggle('pm_can_delete_orders', e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
          />
          <span className="text-sm text-gray-700">PM can delete orders</span>
        </label>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Kiln Shelves OPEX Widget (CEO)
// ---------------------------------------------------------------------------
const MATERIAL_LABELS: Record<string, string> = Object.fromEntries(
  SHELF_MATERIALS.map((m) => [m.value, m.label]),
);

function formatIDR(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toFixed(0);
}

function ShelfOpexCard({ factoryId }: { factoryId: string | null }) {
  const { data, isLoading, isError } = useQuery<ShelfAnalytics>({
    queryKey: ['shelf-analytics', factoryId],
    queryFn: () => kilnShelvesApi.analytics(factoryId || undefined),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) return <Card title="Kiln Shelves OPEX"><Spinner /></Card>;
  if (isError || !data) return null;

  const { overview, by_material, nearing_end_of_life, projections, monthly_opex_trend } = data;

  return (
    <Card>
      <div className="flex items-center gap-2 mb-4">
        <Flame className="h-4 w-4 text-orange-500" />
        <span className="text-sm font-semibold text-gray-800">Kiln Shelves &mdash; Lifecycle &amp; OPEX</span>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-4">
        <div className="rounded-lg border border-gray-200 p-3 text-center">
          <p className="text-xs text-gray-500">Active Shelves</p>
          <p className="text-xl font-bold text-gray-900">{overview.total_active}</p>
          <p className="text-xs text-gray-400">{overview.active_area_sqm} m&sup2;</p>
        </div>
        <div className="rounded-lg border border-gray-200 p-3 text-center">
          <p className="text-xs text-gray-500">Avg Lifespan</p>
          <p className="text-xl font-bold text-gray-900">
            {overview.avg_lifespan_cycles > 0 ? `${overview.avg_lifespan_cycles.toFixed(0)}` : '--'}
          </p>
          <p className="text-xs text-gray-400">
            {overview.sample_size > 0
              ? `${overview.min_lifespan_cycles ?? '?'}–${overview.max_lifespan_cycles ?? '?'} range (${overview.sample_size} samples)`
              : 'No write-off data yet'}
          </p>
        </div>
        <div className="rounded-lg border border-gray-200 p-3 text-center">
          <p className="text-xs text-gray-500">Cost / Cycle</p>
          <p className="text-xl font-bold text-emerald-700">
            {overview.avg_cost_per_cycle_idr > 0 ? `${formatIDR(overview.avg_cost_per_cycle_idr)}` : '--'}
          </p>
          <p className="text-xs text-gray-400">IDR per firing</p>
        </div>
        <div className="rounded-lg border border-gray-200 p-3 text-center">
          <p className="text-xs text-gray-500">Total Investment</p>
          <p className="text-xl font-bold text-gray-900">{formatIDR(overview.total_investment_idr)}</p>
          <p className="text-xs text-gray-400">
            {overview.written_off_cost_idr > 0 && (
              <span className="text-red-500">{formatIDR(overview.written_off_cost_idr)} written off</span>
            )}
          </p>
        </div>
      </div>

      {/* Projections */}
      {(projections.replacements_next_30d > 0 || projections.replacements_next_90d > 0) && (
        <div className="mb-4 rounded-lg bg-amber-50 border border-amber-200 p-3">
          <p className="text-xs font-semibold text-amber-800 mb-1">Projected Replacements</p>
          <div className="flex gap-6 text-sm">
            <div>
              <span className="font-bold text-amber-900">{projections.replacements_next_30d}</span>
              <span className="text-amber-700"> in 30 days</span>
              {projections.replacement_cost_30d_idr > 0 && (
                <span className="text-xs text-amber-600 ml-1">({formatIDR(projections.replacement_cost_30d_idr)} IDR)</span>
              )}
            </div>
            <div>
              <span className="font-bold text-amber-900">{projections.replacements_next_90d}</span>
              <span className="text-amber-700"> in 90 days</span>
              {projections.replacement_cost_90d_idr > 0 && (
                <span className="text-xs text-amber-600 ml-1">({formatIDR(projections.replacement_cost_90d_idr)} IDR)</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Nearing End of Life */}
      {nearing_end_of_life.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-red-700 mb-2">
            Nearing End of Life ({nearing_end_of_life.length})
          </p>
          <div className="space-y-1.5">
            {nearing_end_of_life.slice(0, 6).map((s) => (
              <div key={s.id} className="flex items-center justify-between rounded bg-red-50 px-3 py-1.5">
                <div>
                  <span className="text-sm font-medium text-gray-800">{s.name}</span>
                  <span className="ml-2 text-xs text-gray-500">{s.kiln_name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <div className="h-1.5 w-12 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className={`h-full rounded-full ${s.percent >= 95 ? 'bg-red-600' : 'bg-red-400'}`}
                        style={{ width: `${Math.min(s.percent, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-red-700">{s.percent}%</span>
                  </div>
                  <span className="text-xs text-gray-500">{s.cycles}/{s.max_cycles}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* By Material */}
      {by_material.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-600 mb-2">By Material</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {by_material.map((m) => (
              <div key={m.material} className="rounded-lg border border-gray-100 p-2.5">
                <p className="text-xs font-medium text-gray-700">{MATERIAL_LABELS[m.material] || m.material}</p>
                <p className="text-sm font-bold text-gray-900">{m.active} active</p>
                <p className="text-xs text-gray-400">
                  {m.written_off > 0 && `${m.written_off} written off · `}
                  {m.avg_lifespan_cycles > 0 ? `avg ${m.avg_lifespan_cycles.toFixed(0)} cycles` : 'no data'}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Monthly OPEX Trend (simple bar chart) */}
      {monthly_opex_trend.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-600 mb-2">Monthly Write-off Cost</p>
          <div className="flex items-end gap-1 h-16">
            {monthly_opex_trend.map((m) => {
              const maxCost = Math.max(...monthly_opex_trend.map((t) => t.cost_idr), 1);
              const height = Math.max((m.cost_idr / maxCost) * 100, 4);
              return (
                <div key={m.month} className="flex-1 flex flex-col items-center gap-0.5">
                  <div
                    className="w-full rounded-t bg-red-400 transition-all"
                    style={{ height: `${height}%` }}
                    title={`${m.month}: ${formatIDR(m.cost_idr)} IDR (${m.write_offs} write-offs)`}
                  />
                  <span className="text-[9px] text-gray-400">{m.month.slice(5)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Kiln status colours
// ---------------------------------------------------------------------------
const KILN_STATUS_COLORS: Record<string, string> = {
  idle: 'bg-gray-100 text-gray-700',
  loading: 'bg-blue-100 text-blue-700',
  firing: 'bg-orange-100 text-orange-700',
  cooling: 'bg-cyan-100 text-cyan-700',
  unloading: 'bg-yellow-100 text-yellow-700',
  maintenance: 'bg-red-100 text-red-700',
};

const TASK_STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  cancelled: 'bg-gray-100 text-gray-600',
};

// ---------------------------------------------------------------------------
// Tab types
// ---------------------------------------------------------------------------
type CeoTab = 'pipeline' | 'factories' | 'tasks' | 'kilns';

const CEO_TABS: { id: CeoTab; label: string }[] = [
  { id: 'pipeline', label: 'Production Pipeline' },
  { id: 'factories', label: 'Cross-Factory' },
  { id: 'tasks', label: 'Tasks & Issues' },
  { id: 'kilns', label: 'Kilns & Schedule' },
];

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
export default function CeoDashboard() {
  const { factoryId, setFactoryId } = useFactory();
  const { data: factoriesData, isError: factoriesError } = useFactories();
  const factories = factoriesData?.items ?? [];

  const [activeTab, setActiveTab] = useState<CeoTab>('pipeline');

  const params = factoryId ? { factory_id: factoryId } : undefined;

  const { data: summary, isLoading: loadingSummary, isError: summaryError } = useDashboardSummary(params);
  const { data: production, isLoading: loadingProduction } = useProductionMetrics(params);
  const { data: materials } = useMaterialMetrics(params);
  const { data: bufferData } = useBufferHealth(params);
  const { data: activity } = useActivityFeed({ factory_id: factoryId ?? undefined, limit: 20 });

  // Cross-factory comparison (always all factories)
  const { data: factoryComparison, isLoading: loadingComparison } = useFactoryComparison();

  // Tasks & Issues
  const { data: blockingTasks } = useTasks({ status: 'pending,in_progress', ...(factoryId ? { factory_id: factoryId } : {}) });
  const { data: changeReqData } = useChangeRequests(factoryId ? { factory_id: factoryId } : undefined);

  // Kilns
  const { data: kilnsData, isLoading: loadingKilns } = useKilns(factoryId ? { factory_id: factoryId } : undefined);
  const { data: kilnScheduleData } = useKilnSchedule(factoryId);

  const [exporting, setExporting] = useState(false);

  const handleExportDaily = async () => {
    setExporting(true);
    try {
      const params: Record<string, string> = {
        report_date: new Date().toISOString().split('T')[0],
      };
      if (factoryId) params.factory_id = factoryId;

      const res = await apiClient.get('/export/ceo-daily/excel', {
        params,
        responseType: 'blob',
      });
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ceo-daily-${new Date().toISOString().split('T')[0]}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Handle silently
    } finally {
      setExporting(false);
    }
  };

  // Derived metrics
  const blockingTasksList: TaskItem[] = blockingTasks?.items ?? [];
  const blockingCount = blockingTasksList.filter((t) => t.blocking).length;
  const overduePositions = production?.critical_positions?.filter((p) => p.deadline && new Date(p.deadline) < new Date()) ?? [];
  const pendingChangeRequests = changeReqData?.total ?? 0;

  if (loadingSummary) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CEO Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">Operational overview across all factories</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Factory Selector */}
          <select
            value={factoryId ?? ''}
            onChange={(e) => setFactoryId(e.target.value || null)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm"
          >
            <option value="">All Factories</option>
            {factories.map((f: { id: string; name: string }) => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>
          <button
            onClick={handleExportDaily}
            disabled={exporting}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {exporting ? <Spinner className="h-4 w-4" /> : <Download className="h-4 w-4" />}
            {exporting ? 'Exporting...' : 'Export Excel'}
          </button>
        </div>
      </div>

      {/* API Error Banner */}
      {(summaryError || factoriesError) && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">
            Error loading dashboard data.{summaryError ? ' Analytics API failed.' : ''}{factoriesError ? ' Factories API failed.' : ''}
          </p>
          <p className="mt-1 text-xs text-red-600">Try refreshing the page.</p>
        </div>
      )}

      {/* KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <KpiCard title="Active Orders" value={summary.orders_in_progress} subtitle={`of ${summary.total_orders} total`} variant="glass" icon={<BarChart3 className="h-4 w-4" />} />
          <KpiCard title="Output m²" value={summary.output_sqm.toFixed(0)} subtitle="last 30 days" variant="glass" />
          <KpiCard title="On-Time" value={`${summary.on_time_rate.toFixed(0)}%`} variant="glass" icon={<Percent className="h-4 w-4" />} />
          <KpiCard title="Defect Rate" value={`${summary.defect_rate.toFixed(1)}%`} variant="glass" icon={<AlertTriangle className="h-4 w-4" />} />
          <KpiCard title="Kiln Util." value={`${summary.kiln_utilization.toFixed(0)}%`} variant="glass" icon={<Flame className="h-4 w-4" />} />
          <KpiCard title="OEE" value={`${summary.oee.toFixed(0)}%`} variant="glass" icon={<Zap className="h-4 w-4" />} />
        </div>
      )}

      {/* Tabs */}
      <Tabs tabs={CEO_TABS} activeTab={activeTab} onChange={(id) => setActiveTab(id as CeoTab)} />

      {/* ================================================================ */}
      {/* Tab 1: Production Pipeline                                       */}
      {/* ================================================================ */}
      {activeTab === 'pipeline' && (
        <div className="space-y-4">
          {/* Pipeline + Daily Output */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="Production Pipeline">
              {loadingProduction ? <Spinner /> : production?.pipeline_funnel && (
                <PipelineFunnel data={production.pipeline_funnel} />
              )}
            </Card>
            <Card title="Daily Output (30 days)">
              {loadingProduction ? <Spinner /> : production?.daily_output && (
                <DailyOutputChart data={production.daily_output} />
              )}
            </Card>
          </div>

          {/* Buffer Health + Critical Positions */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="Buffer Health (TOC)">
              {bufferData?.items ? <BufferHealthTable items={bufferData.items} /> : <Spinner />}
            </Card>
            <Card title="Critical Positions">
              {production?.critical_positions ? (
                <CriticalPositionsTable positions={production.critical_positions} />
              ) : <Spinner />}
            </Card>
          </div>

          {/* Material Deficits + Activity Feed */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="Material Deficits">
              {materials?.deficit_items ? (
                <MaterialDeficitsTable items={materials.deficit_items} />
              ) : <Spinner />}
            </Card>
            <Card title="Activity Feed">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-4 w-4 text-gray-400" />
                <span className="text-xs text-gray-500">Auto-refreshes every 30s</span>
              </div>
              {activity ? <ActivityFeed items={activity} /> : <Spinner />}
            </Card>
          </div>
        </div>
      )}

      {/* ================================================================ */}
      {/* Tab 2: Cross-Factory Comparison                                   */}
      {/* ================================================================ */}
      {activeTab === 'factories' && (
        <div className="space-y-4">
          {/* Factory comparison cards */}
          <Card title="Factory Performance Overview">
            {loadingComparison ? <Spinner /> : factoryComparison && (
              <FactoryComparisonCards data={factoryComparison} />
            )}
          </Card>

          {/* Detailed comparison table */}
          {factoryComparison && factoryComparison.length > 0 && (
            <Card title="Detailed Comparison">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Factory</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">Active Orders</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">Output m²</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">Kiln Util.</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">Defect %</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">On-Time %</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">OEE %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {factoryComparison.map((f: FactoryComparison) => {
                      // Find best/worst for color coding
                      const bestOnTime = Math.max(...factoryComparison.map((x: FactoryComparison) => x.on_time_rate));
                      const worstDefect = Math.max(...factoryComparison.map((x: FactoryComparison) => x.defect_rate));
                      return (
                        <tr key={f.factory_id} className="hover:bg-gray-50">
                          <td className="px-4 py-2 font-medium text-gray-900">
                            <div className="flex items-center gap-2">
                              <Factory className="h-4 w-4 text-gray-400" />
                              {f.factory_name}
                              {f.factory_location && <span className="text-xs text-gray-400">({f.factory_location})</span>}
                            </div>
                          </td>
                          <td className="px-4 py-2 text-right text-gray-900">{f.orders_in_progress}</td>
                          <td className="px-4 py-2 text-right text-gray-900">{f.output_sqm.toFixed(0)}</td>
                          <td className="px-4 py-2 text-right">
                            <span className={cn('font-medium', f.kiln_utilization >= 70 ? 'text-green-700' : 'text-yellow-700')}>
                              {f.kiln_utilization.toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className={cn('font-medium', f.defect_rate === worstDefect && factoryComparison.length > 1 ? 'text-red-600' : f.defect_rate <= 5 ? 'text-green-700' : 'text-yellow-700')}>
                              {f.defect_rate.toFixed(1)}%
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className={cn('font-medium', f.on_time_rate === bestOnTime && factoryComparison.length > 1 ? 'text-green-700' : f.on_time_rate >= 90 ? 'text-green-700' : 'text-yellow-700')}>
                              {f.on_time_rate.toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className={cn('font-medium', f.oee >= 85 ? 'text-green-700' : 'text-yellow-700')}>
                              {f.oee.toFixed(0)}%
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ================================================================ */}
      {/* Tab 3: Tasks & Issues                                            */}
      {/* ================================================================ */}
      {activeTab === 'tasks' && (
        <div className="space-y-4">
          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <KpiCard
              title="Blocking Tasks"
              value={blockingCount}
              color={blockingCount > 0 ? 'red' : 'green'}
              icon={<AlertTriangle className="h-4 w-4" />}
            />
            <KpiCard
              title="Overdue Positions"
              value={overduePositions.length}
              color={overduePositions.length > 0 ? 'red' : 'green'}
              icon={<Clock className="h-4 w-4" />}
            />
            <KpiCard
              title="Change Requests"
              value={pendingChangeRequests}
              color={pendingChangeRequests > 0 ? 'yellow' : 'green'}
            />
            <KpiCard
              title="Total Pending"
              value={blockingTasksList.filter((t) => t.status === 'pending').length}
              color="blue"
            />
          </div>

          {/* Blocking tasks list */}
          <Card title="Blocking Tasks">
            {blockingTasksList.filter((t) => t.blocking).length === 0 ? (
              <div className="py-6 text-center text-sm text-gray-500">
                <AlertTriangle className="mx-auto mb-2 h-8 w-8 text-green-400" />
                No blocking tasks
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Type</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Description</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Order</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Assigned</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Status</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Due</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {blockingTasksList
                      .filter((t) => t.blocking)
                      .slice(0, 20)
                      .map((t) => (
                        <tr key={t.id} className="hover:bg-gray-50">
                          <td className="px-3 py-2">
                            <span className="inline-flex rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-800 capitalize">
                              {t.type.replace(/_/g, ' ')}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-gray-700 max-w-xs truncate">{t.description || '--'}</td>
                          <td className="px-3 py-2 text-gray-600">{t.related_order_number || '--'}</td>
                          <td className="px-3 py-2 text-gray-600">{t.assigned_to_name || t.assigned_role || '--'}</td>
                          <td className="px-3 py-2">
                            <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize', TASK_STATUS_COLORS[t.status] || 'bg-gray-100 text-gray-600')}>
                              {t.status}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-gray-600 text-xs">
                            {t.due_at ? formatDate(t.due_at) : '--'}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Overdue Positions */}
          <Card title="Overdue Positions">
            {overduePositions.length === 0 ? (
              <div className="py-6 text-center text-sm text-gray-500">
                <Clock className="mx-auto mb-2 h-8 w-8 text-green-400" />
                No overdue positions
              </div>
            ) : (
              <CriticalPositionsTable positions={overduePositions} />
            )}
          </Card>
        </div>
      )}

      {/* ================================================================ */}
      {/* Tab 4: Kilns & Schedule                                          */}
      {/* ================================================================ */}
      {activeTab === 'kilns' && (
        <div className="space-y-4">
          {/* Kilns overview */}
          <Card title="All Kilns">
            {loadingKilns ? <Spinner /> : (
              <>
                {(!kilnsData?.items || kilnsData.items.length === 0) ? (
                  <p className="text-sm text-gray-500">No kilns found</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-4 py-2 text-left font-medium text-gray-500">Kiln</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-500">Factory</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-500">Type</th>
                          <th className="px-4 py-2 text-left font-medium text-gray-500">Status</th>
                          <th className="px-4 py-2 text-right font-medium text-gray-500">Capacity m²</th>
                          <th className="px-4 py-2 text-center font-medium text-gray-500">Levels</th>
                          <th className="px-4 py-2 text-center font-medium text-gray-500">Active</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {kilnsData.items.map((k: KilnItem) => (
                          <tr key={k.id} className={cn('hover:bg-gray-50', !k.is_active && 'opacity-50')}>
                            <td className="px-4 py-2 font-medium text-gray-900">{k.name}</td>
                            <td className="px-4 py-2 text-gray-600">{k.factory_name || '--'}</td>
                            <td className="px-4 py-2 text-gray-600 capitalize">{k.kiln_type}</td>
                            <td className="px-4 py-2">
                              <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-semibold capitalize', KILN_STATUS_COLORS[k.status] || 'bg-gray-100 text-gray-600')}>
                                {k.status}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-right text-gray-900">{k.capacity_sqm?.toFixed(1) ?? '--'}</td>
                            <td className="px-4 py-2 text-center text-gray-600">{k.num_levels}</td>
                            <td className="px-4 py-2 text-center">
                              {k.is_active ? (
                                <span className="inline-flex h-2 w-2 rounded-full bg-green-500" />
                              ) : (
                                <span className="inline-flex h-2 w-2 rounded-full bg-gray-300" />
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </Card>

          {/* Kiln status summary cards */}
          {kilnsData?.items && kilnsData.items.length > 0 && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              {(['idle', 'loading', 'firing', 'cooling', 'unloading', 'maintenance'] as const).map((status) => {
                const count = kilnsData.items.filter((k: KilnItem) => k.status === status).length;
                return (
                  <div key={status} className={cn('rounded-lg border p-3 text-center', KILN_STATUS_COLORS[status])}>
                    <p className="text-xs font-medium uppercase tracking-wide">{status}</p>
                    <p className="mt-1 text-2xl font-bold">{count}</p>
                  </div>
                );
              })}
            </div>
          )}

          {/* Firing schedule */}
          <Card title="Kiln Schedule">
            <div className="flex items-center gap-2 mb-3">
              <CalendarDays className="h-4 w-4 text-gray-400" />
              <span className="text-xs text-gray-500">Today and upcoming batches</span>
            </div>
            {kilnScheduleData?.items && kilnScheduleData.items.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Date</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Kiln</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Status</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-500">Positions</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-500">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {kilnScheduleData.items.slice(0, 15).map((batch: any) => (
                      <tr key={batch.id} className="hover:bg-gray-50">
                        <td className="px-3 py-2 text-gray-900">{batch.batch_date || batch.date || '--'}</td>
                        <td className="px-3 py-2 text-gray-700">{batch.resource_name || batch.kiln_name || '--'}</td>
                        <td className="px-3 py-2">
                          <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize', batch.status === 'completed' ? 'bg-green-100 text-green-800' : batch.status === 'in_progress' ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800')}>
                            {batch.status || 'scheduled'}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right text-gray-900">{batch.position_count ?? batch.positions?.length ?? '--'}</td>
                        <td className="px-3 py-2 text-gray-500 text-xs max-w-xs truncate">{batch.notes || '--'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-6 text-center text-sm text-gray-500">
                <Wrench className="mx-auto mb-2 h-8 w-8 text-gray-300" />
                No scheduled batches found
              </div>
            )}
          </Card>

          {/* Kiln Shelves OPEX */}
          <ShelfOpexCard factoryId={factoryId} />

          {/* Buffer Health in kilns tab context */}
          <Card title="Buffer Health (TOC)">
            {bufferData?.items ? <BufferHealthTable items={bufferData.items} /> : <Spinner />}
          </Card>
        </div>
      )}

      {/* PM Cleanup Permissions */}
      <div className="max-w-xs">
        <CleanupPermissionsCard factoryId={factoryId} />
      </div>
    </div>
  );
}
