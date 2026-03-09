import { useState } from 'react';
import { BarChart3, Download, TrendingUp, AlertTriangle, Percent, Flame } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { KpiCard } from '@/components/dashboard/KpiCard';
import { PeriodSelector, periodToDateRange } from '@/components/dashboard/PeriodSelector';
import { FinancialBlock } from '@/components/dashboard/FinancialBlock';
import { FactoryComparisonCards } from '@/components/dashboard/FactoryComparisonCards';
import { OutputTrendChart } from '@/components/charts/OutputTrendChart';
import { OnTimeTrendChart } from '@/components/charts/OnTimeTrendChart';
import { DefectTrendChart } from '@/components/charts/DefectTrendChart';
import { useDashboardSummary, useFactoryComparison, useTrendData } from '@/hooks/useAnalytics';
import { useFinancialSummary } from '@/hooks/useFinancials';
import apiClient from '@/api/client';

export default function OwnerDashboard() {
  const [period, setPeriod] = useState<'week' | 'month' | 'quarter' | 'year'>('month');
  const dateRange = periodToDateRange(period);

  const { data: summary, isLoading: loadingSummary, isError: summaryError } = useDashboardSummary(dateRange);
  const { data: factories, isLoading: loadingFactories, isError: factoriesError } = useFactoryComparison();
  const { data: financials, isLoading: loadingFinancials } = useFinancialSummary(dateRange);
  const { data: outputTrend } = useTrendData('output', undefined, 6);
  const { data: onTimeTrend } = useTrendData('on_time', undefined, 6);
  const { data: defectTrend } = useTrendData('defects', undefined, 6);

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
            ⚠ Error loading dashboard data.{summaryError ? ' Analytics API failed.' : ''}{factoriesError ? ' Factory comparison failed.' : ''}
          </p>
          <p className="mt-1 text-xs text-red-600">Try refreshing the page. If the issue persists, check backend logs.</p>
        </div>
      )}

      {/* KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <KpiCard title="Active Orders" value={summary.orders_in_progress} subtitle={`of ${summary.total_orders} total`} color="blue" icon={<BarChart3 className="h-4 w-4" />} />
          <KpiCard title="Output m\u00B2" value={summary.output_sqm.toFixed(0)} color="green" icon={<TrendingUp className="h-4 w-4" />} />
          <KpiCard title="On-Time" value={`${summary.on_time_rate.toFixed(0)}%`} color={summary.on_time_rate >= 90 ? 'green' : 'yellow'} icon={<Percent className="h-4 w-4" />} />
          <KpiCard title="Defect Rate" value={`${summary.defect_rate.toFixed(1)}%`} color={summary.defect_rate <= 5 ? 'green' : 'red'} icon={<AlertTriangle className="h-4 w-4" />} />
          <KpiCard title="Kiln Util." value={`${summary.kiln_utilization.toFixed(0)}%`} color={summary.kiln_utilization >= 70 ? 'green' : 'yellow'} icon={<Flame className="h-4 w-4" />} />
        </div>
      )}

      {/* Financial Block */}
      {financials && !loadingFinancials && (
        <FinancialBlock data={financials} />
      )}

      {/* Factory Comparison */}
      <Card title="Factory Comparison">
        {loadingFactories ? <Spinner /> : factories && <FactoryComparisonCards data={factories} />}
      </Card>

      {/* Trend Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Output Trend (6 months)">
          {outputTrend ? <OutputTrendChart data={outputTrend} /> : <Spinner />}
        </Card>
        <Card title="On-Time Rate (6 months)">
          {onTimeTrend ? <OnTimeTrendChart data={onTimeTrend} /> : <Spinner />}
        </Card>
      </div>

      <Card title="Defect Rate Trend (6 months)">
        {defectTrend ? <DefectTrendChart data={defectTrend} height={250} /> : <Spinner />}
      </Card>
    </div>
  );
}
