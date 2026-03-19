import { useState } from 'react';
import {
  BarChart3, Download, TrendingUp, AlertTriangle, Percent, Flame,
  DollarSign, Factory, Clock, Package,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { KpiCard } from '@/components/dashboard/KpiCard';
import { PeriodSelector, periodToDateRange } from '@/components/dashboard/PeriodSelector';
import { FinancialBlock } from '@/components/dashboard/FinancialBlock';
import { FactoryComparisonCards } from '@/components/dashboard/FactoryComparisonCards';
import { CriticalPositionsTable } from '@/components/dashboard/CriticalPositionsTable';
import { MaterialDeficitsTable } from '@/components/dashboard/MaterialDeficitsTable';
import { OutputTrendChart } from '@/components/charts/OutputTrendChart';
import { OnTimeTrendChart } from '@/components/charts/OnTimeTrendChart';
import { DefectTrendChart } from '@/components/charts/DefectTrendChart';
import { OeeChart } from '@/components/charts/OeeChart';
import { OpexBreakdownChart } from '@/components/charts/OpexBreakdownChart';
import {
  useDashboardSummary,
  useFactoryComparison,
  useTrendData,
  useProductionMetrics,
  useMaterialMetrics,
} from '@/hooks/useAnalytics';
import { useFinancialSummary } from '@/hooks/useFinancials';
import apiClient from '@/api/client';
import type { FactoryComparison } from '@/api/analytics';
import { cn } from '@/lib/cn';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
export default function OwnerDashboard() {
  const [period, setPeriod] = useState<'week' | 'month' | 'quarter' | 'year'>('month');
  const dateRange = periodToDateRange(period);

  // Core data
  const { data: summary, isLoading: loadingSummary, isError: summaryError } = useDashboardSummary(dateRange);
  const { data: factories, isLoading: loadingFactories, isError: factoriesError } = useFactoryComparison();
  const { data: financials, isLoading: loadingFinancials } = useFinancialSummary(dateRange);
  const { data: production } = useProductionMetrics(dateRange);
  const { data: materials } = useMaterialMetrics();

  // Trend data (6 months)
  const { data: outputTrend } = useTrendData('output', undefined, 6);
  const { data: onTimeTrend } = useTrendData('on_time', undefined, 6);
  const { data: defectTrend } = useTrendData('defects', undefined, 6);
  const { data: oeeTrend } = useTrendData('oee', undefined, 6);

  const handleExportMonthly = async () => {
    try {
      const res = await apiClient.post('/export/owner-monthly', null, {
        params: { month: new Date().toISOString().slice(0, 7) },
      });
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `owner-report-${new Date().toISOString().slice(0, 7)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Handle silently
    }
  };

  // Derived data
  const overduePositions = production?.critical_positions?.filter(
    (p) => p.deadline && new Date(p.deadline) < new Date()
  ) ?? [];
  const highDefectPositions = production?.critical_positions?.filter(
    (p) => p.delay_hours > 48
  ) ?? [];
  const opexBreakdown = financials?.breakdown?.filter((b) => b.entry_type === 'opex') ?? [];

  // OEE trend: transform TrendDataPoint[] to {label, oee}[]
  const oeeChartData = oeeTrend?.map((p) => ({ label: p.label, oee: p.value })) ?? [];

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
          <h1 className="text-2xl font-bold text-gray-900">Owner Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">Strategic overview across all factories</p>
        </div>
        <div className="flex items-center gap-3">
          <PeriodSelector value={period} onChange={setPeriod} />
          <button
            onClick={handleExportMonthly}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
          >
            <Download className="h-4 w-4" />
            Export Monthly
          </button>
        </div>
      </div>

      {/* API Error Banner */}
      {(summaryError || factoriesError) && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">
            Error loading dashboard data.{summaryError ? ' Analytics API failed.' : ''}{factoriesError ? ' Factory comparison failed.' : ''}
          </p>
          <p className="mt-1 text-xs text-red-600">Try refreshing the page. If the issue persists, check backend logs.</p>
        </div>
      )}

      {/* ================================================================ */}
      {/* Section: Financial Summary Cards                                  */}
      {/* ================================================================ */}
      {financials && !loadingFinancials && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <KpiCard
            title="Revenue"
            value={formatCurrency(financials.revenue)}
            color="green"
            icon={<DollarSign className="h-4 w-4" />}
          />
          <KpiCard
            title="Expenses"
            value={formatCurrency(financials.opex_total + financials.capex_total)}
            subtitle={`OPEX ${formatCurrency(financials.opex_total)} + CAPEX ${formatCurrency(financials.capex_total)}`}
            color="red"
          />
          <KpiCard
            title="Profit Margin"
            value={`${financials.margin_percent.toFixed(1)}%`}
            subtitle={formatCurrency(financials.margin)}
            color={financials.margin_percent >= 15 ? 'green' : financials.margin_percent >= 0 ? 'yellow' : 'red'}
            icon={<Percent className="h-4 w-4" />}
          />
          <KpiCard
            title="Output m²"
            value={financials.output_sqm.toFixed(0)}
            subtitle={`Cost ${(financials.cost_per_sqm).toFixed(2)}/m²`}
            color="blue"
            icon={<Package className="h-4 w-4" />}
          />
          <KpiCard
            title="Orders Completed"
            value={summary?.total_orders ?? 0}
            subtitle={`${summary?.orders_in_progress ?? 0} in progress`}
            color="purple"
            icon={<BarChart3 className="h-4 w-4" />}
          />
        </div>
      )}

      {/* Operational KPI row (if no financials, show these as primary) */}
      {summary && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <KpiCard title="On-Time" value={`${summary.on_time_rate.toFixed(0)}%`} color={summary.on_time_rate >= 90 ? 'green' : 'yellow'} icon={<TrendingUp className="h-4 w-4" />} />
          <KpiCard title="Defect Rate" value={`${summary.defect_rate.toFixed(1)}%`} color={summary.defect_rate <= 5 ? 'green' : 'red'} icon={<AlertTriangle className="h-4 w-4" />} />
          <KpiCard title="Kiln Util." value={`${summary.kiln_utilization.toFixed(0)}%`} color={summary.kiln_utilization >= 70 ? 'green' : 'yellow'} icon={<Flame className="h-4 w-4" />} />
          <KpiCard title="OEE" value={`${summary.oee.toFixed(0)}%`} color={summary.oee >= 85 ? 'green' : 'yellow'} />
        </div>
      )}

      {/* Full Financial Block */}
      {financials && !loadingFinancials && (
        <FinancialBlock data={financials} />
      )}

      {/* ================================================================ */}
      {/* Section 1: Performance Trends                                     */}
      {/* ================================================================ */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Performance Trends (6 months)</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Card title="Output Trend">
            {outputTrend ? <OutputTrendChart data={outputTrend} /> : <Spinner />}
          </Card>
          <Card title="On-Time Rate">
            {onTimeTrend ? <OnTimeTrendChart data={onTimeTrend} /> : <Spinner />}
          </Card>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Card title="Defect Rate Trend">
            {defectTrend ? <DefectTrendChart data={defectTrend} height={250} /> : <Spinner />}
          </Card>
          <Card title="OEE Trend">
            {oeeChartData.length > 0 ? <OeeChart data={oeeChartData} height={250} /> : <Spinner />}
          </Card>
        </div>
      </div>

      {/* OPEX Breakdown Chart */}
      {opexBreakdown.length > 0 && (
        <Card title="OPEX Breakdown">
          <OpexBreakdownChart data={opexBreakdown} />
        </Card>
      )}

      {/* ================================================================ */}
      {/* Section 2: Factory Performance Matrix                             */}
      {/* ================================================================ */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Factory Performance</h2>
        <Card>
          {loadingFactories ? <Spinner /> : factories && factories.length > 0 ? (
            <>
              <FactoryComparisonCards data={factories} />

              {/* Detailed comparison table */}
              <div className="mt-4 overflow-x-auto border-t border-gray-100 pt-4">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Factory</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">Output m²</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">Quality (Defect %)</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">Efficiency (OEE)</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">Kiln Util.</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">On-Time %</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500">Active Orders</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {factories.map((f: FactoryComparison) => {
                      const bestOutput = Math.max(...factories.map((x: FactoryComparison) => x.output_sqm));
                      const bestOee = Math.max(...factories.map((x: FactoryComparison) => x.oee));
                      return (
                        <tr key={f.factory_id} className="hover:bg-gray-50">
                          <td className="px-4 py-2 font-medium text-gray-900">
                            <div className="flex items-center gap-2">
                              <Factory className="h-4 w-4 text-gray-400" />
                              {f.factory_name}
                              {f.factory_location && <span className="text-xs text-gray-400">({f.factory_location})</span>}
                            </div>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className={cn('font-medium', f.output_sqm === bestOutput && factories.length > 1 ? 'text-green-700' : 'text-gray-900')}>
                              {f.output_sqm.toFixed(0)}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className={cn('font-medium', f.defect_rate <= 3 ? 'text-green-700' : f.defect_rate <= 5 ? 'text-yellow-700' : 'text-red-600')}>
                              {f.defect_rate.toFixed(1)}%
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className={cn('font-medium', f.oee === bestOee && factories.length > 1 ? 'text-green-700' : f.oee >= 85 ? 'text-green-700' : 'text-yellow-700')}>
                              {f.oee.toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className={cn('font-medium', f.kiln_utilization >= 70 ? 'text-green-700' : 'text-yellow-700')}>
                              {f.kiln_utilization.toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className={cn('font-medium', f.on_time_rate >= 90 ? 'text-green-700' : 'text-yellow-700')}>
                              {f.on_time_rate.toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right text-gray-900">{f.orders_in_progress}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="text-sm text-gray-500">No factory data available</p>
          )}
        </Card>
      </div>

      {/* ================================================================ */}
      {/* Section 3: Top Issues                                             */}
      {/* ================================================================ */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Top Issues</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {/* Overdue positions */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <Clock className="h-4 w-4 text-red-500" />
              <h3 className="text-sm font-semibold text-gray-900">Overdue Positions</h3>
              <span className={cn('ml-auto inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold', overduePositions.length > 0 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800')}>
                {overduePositions.length}
              </span>
            </div>
            {overduePositions.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {overduePositions.slice(0, 10).map((p) => (
                  <div key={p.position_id} className="rounded border border-red-100 bg-red-50 p-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-900">{p.order_number || '--'}</span>
                      <span className="text-red-600 font-semibold">{p.delay_hours}h late</span>
                    </div>
                    <p className="text-gray-600 mt-0.5">{p.color} / {p.size} - qty {p.quantity}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">No overdue positions</p>
            )}
          </Card>

          {/* High delay positions */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              <h3 className="text-sm font-semibold text-gray-900">Severely Delayed (&gt;48h)</h3>
              <span className={cn('ml-auto inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold', highDefectPositions.length > 0 ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800')}>
                {highDefectPositions.length}
              </span>
            </div>
            {highDefectPositions.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {highDefectPositions.slice(0, 10).map((p) => (
                  <div key={p.position_id} className="rounded border border-yellow-100 bg-yellow-50 p-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-900">{p.order_number || '--'}</span>
                      <span className="text-yellow-700 font-semibold">{p.delay_hours}h</span>
                    </div>
                    <p className="text-gray-600 mt-0.5">{p.color} / {p.size} - qty {p.quantity}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">No severely delayed positions</p>
            )}
          </Card>

          {/* Material shortages */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <Package className="h-4 w-4 text-orange-500" />
              <h3 className="text-sm font-semibold text-gray-900">Material Shortages</h3>
              <span className={cn('ml-auto inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold', (materials?.deficit_count ?? 0) > 0 ? 'bg-orange-100 text-orange-800' : 'bg-green-100 text-green-800')}>
                {materials?.deficit_count ?? 0}
              </span>
            </div>
            {materials?.deficit_items && materials.deficit_items.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {materials.deficit_items.slice(0, 10).map((item) => (
                  <div key={item.material_id} className="rounded border border-orange-100 bg-orange-50 p-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-900">{item.name}</span>
                      <span className="text-red-600 font-semibold">-{item.deficit.toFixed(1)} {item.unit}</span>
                    </div>
                    <p className="text-gray-600 mt-0.5">Balance: {item.balance} / Min: {item.min_balance} {item.unit}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">All materials above minimum</p>
            )}
          </Card>
        </div>
      </div>

      {/* Full critical positions table if available */}
      {production?.critical_positions && production.critical_positions.length > 0 && (
        <Card title="All Critical Positions">
          <CriticalPositionsTable positions={production.critical_positions} />
        </Card>
      )}

      {/* Full material deficits table if available */}
      {materials?.deficit_items && materials.deficit_items.length > 0 && (
        <Card title="Material Deficit Details">
          <MaterialDeficitsTable items={materials.deficit_items} />
        </Card>
      )}
    </div>
  );
}
