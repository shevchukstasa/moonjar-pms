import { BarChart3, Clock, AlertTriangle, Percent, Flame, Activity, Download, Trash2 } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { KpiCard } from '@/components/dashboard/KpiCard';
import { BufferHealthTable } from '@/components/dashboard/BufferHealthTable';
import { CriticalPositionsTable } from '@/components/dashboard/CriticalPositionsTable';
import { MaterialDeficitsTable } from '@/components/dashboard/MaterialDeficitsTable';
import { ActivityFeed } from '@/components/dashboard/ActivityFeed';
import { PipelineFunnel } from '@/components/charts/PipelineFunnel';
import { DailyOutputChart } from '@/components/charts/DailyOutputChart';
import {
  useDashboardSummary,
  useProductionMetrics,
  useMaterialMetrics,
  useBufferHealth,
  useActivityFeed,
} from '@/hooks/useAnalytics';
import { useFactory } from '@/hooks/useFactory';
import { useFactories } from '@/hooks/useFactories';
import apiClient from '@/api/client';
import { useState, useEffect } from 'react';

function CleanupPermissionsCard({ factoryId }: { factoryId: string | null }) {
  const [canDeleteTasks, setCanDeleteTasks] = useState(false);
  const [canDeletePositions, setCanDeletePositions] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!factoryId) return;
    apiClient.get('/cleanup/permissions', { params: { factory_id: factoryId } })
      .then((r) => {
        setCanDeleteTasks(r.data.pm_can_delete_tasks);
        setCanDeletePositions(r.data.pm_can_delete_positions);
      })
      .catch(() => {});
  }, [factoryId]);

  const toggle = async (field: 'pm_can_delete_tasks' | 'pm_can_delete_positions', value: boolean) => {
    if (!factoryId) return;
    setSaving(true);
    try {
      const r = await apiClient.patch('/cleanup/permissions', {
        factory_id: factoryId,
        [field]: value,
      });
      setCanDeleteTasks(r.data.pm_can_delete_tasks);
      setCanDeletePositions(r.data.pm_can_delete_positions);
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
        <span className="ml-auto text-xs text-amber-600 font-medium">⚠ Temporary</span>
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
      </div>
    </Card>
  );
}

export default function CeoDashboard() {
  const { factoryId, setFactoryId } = useFactory();
  const { data: factoriesData, isError: factoriesError } = useFactories();
  const factories = factoriesData?.items ?? [];

  const params = factoryId ? { factory_id: factoryId } : undefined;

  const { data: summary, isLoading: loadingSummary, isError: summaryError } = useDashboardSummary(params);
  const { data: production, isLoading: loadingProduction } = useProductionMetrics(params);
  const { data: materials } = useMaterialMetrics(params);
  const { data: bufferData } = useBufferHealth(params);
  const { data: activity } = useActivityFeed({ factory_id: factoryId ?? undefined, limit: 20 });

  const handleExportDaily = async () => {
    try {
      const res = await apiClient.post('/export/ceo-daily', null, {
        params: { factory_id: factoryId, report_date: new Date().toISOString().split('T')[0] },
      });
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ceo-daily-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Handle silently
    }
  };

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CEO Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">Operational overview</p>
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
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
          >
            <Download className="h-4 w-4" />
            Export Daily
          </button>
        </div>
      </div>

      {/* API Error Banner */}
      {(summaryError || factoriesError) && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">
            ⚠ Error loading dashboard data.{summaryError ? ' Analytics API failed.' : ''}{factoriesError ? ' Factories API failed.' : ''}
          </p>
          <p className="mt-1 text-xs text-red-600">Try refreshing the page.</p>
        </div>
      )}

      {/* KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <KpiCard title="Active Orders" value={summary.orders_in_progress} color="blue" icon={<BarChart3 className="h-4 w-4" />} />
          <KpiCard title="Output m\u00B2" value={summary.output_sqm.toFixed(0)} subtitle="last 30 days" color="green" />
          <KpiCard title="Queue for Firing" value={bufferData?.items?.reduce((s: number, i: { buffered_count: number }) => s + i.buffered_count, 0) ?? 0} color="purple" icon={<Clock className="h-4 w-4" />} />
          <KpiCard title="On-Time" value={`${summary.on_time_rate.toFixed(0)}%`} color={summary.on_time_rate >= 90 ? 'green' : 'yellow'} icon={<Percent className="h-4 w-4" />} />
          <KpiCard title="Alerts" value={production?.critical_positions?.length ?? 0} color={production?.critical_positions?.length ? 'red' : 'green'} icon={<AlertTriangle className="h-4 w-4" />} />
          <KpiCard title="OEE" value={`${summary.oee.toFixed(0)}%`} color={summary.oee >= 85 ? 'green' : 'yellow'} icon={<Flame className="h-4 w-4" />} />
        </div>
      )}

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

      {/* PM Cleanup Permissions */}
      <div className="max-w-xs">
        <CleanupPermissionsCard factoryId={factoryId} />
      </div>
    </div>
  );
}
