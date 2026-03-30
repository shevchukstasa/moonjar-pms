import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { reportsApi, type ReportParams } from '@/api/reports';
import { factoriesApi } from '@/api/factories';
import { DatePicker } from '@/components/ui/DatePicker';

function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

const today = new Date();
const thirtyDaysAgo = new Date(today);
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

function utilizationColor(pct: number): string {
  if (pct >= 80) return 'bg-green-500';
  if (pct >= 50) return 'bg-yellow-500';
  return 'bg-red-500';
}

function utilizationBadge(pct: number): string {
  if (pct >= 80) return 'text-green-700 bg-green-50 ring-green-600/20';
  if (pct >= 50) return 'text-yellow-700 bg-yellow-50 ring-yellow-600/20';
  return 'text-red-700 bg-red-50 ring-red-600/20';
}

export default function ReportsPage() {
  const [factoryId, setFactoryId] = useState<string>('');
  const [dateFrom, setDateFrom] = useState(formatDate(thirtyDaysAgo));
  const [dateTo, setDateTo] = useState(formatDate(today));

  const params: ReportParams = {
    ...(factoryId ? { factory_id: factoryId } : {}),
    date_from: dateFrom,
    date_to: dateTo,
  };

  const { data: factories } = useQuery({
    queryKey: ['factories'],
    queryFn: () => factoriesApi.list(),
  });

  const {
    data: ordersSummary,
    isLoading: ordersLoading,
    error: ordersError,
  } = useQuery({
    queryKey: ['reports', 'orders-summary', params],
    queryFn: () => reportsApi.ordersSummary(params),
  });

  const {
    data: kilnLoad,
    isLoading: kilnLoading,
    error: kilnError,
  } = useQuery({
    queryKey: ['reports', 'kiln-load', params],
    queryFn: () => reportsApi.kilnLoad(params),
  });

  const factoryList = factories?.items ?? factories ?? [];

  return (
    <div className="space-y-6">
      {/* Header + Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Factory</label>
            <select
              value={factoryId}
              onChange={(e) => setFactoryId(e.target.value)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Factories</option>
              {Array.isArray(factoryList) &&
                factoryList.map((f: { id: string; name: string }) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">From</label>
            <DatePicker
              value={dateFrom}
              onChange={(v) => setDateFrom(v)}
              className="rounded-lg shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">To</label>
            <DatePicker
              value={dateTo}
              onChange={(v) => setDateTo(v)}
              className="rounded-lg shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Order Summary Cards */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-800">Orders Summary</h2>
        {ordersLoading ? (
          <div className="flex h-32 items-center justify-center text-gray-400">Loading...</div>
        ) : ordersError ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            Failed to load orders summary
          </div>
        ) : ordersSummary ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <SummaryCard
              title="Total Orders"
              value={ordersSummary.total_orders}
              subtitle={`${ordersSummary.in_progress} in progress`}
              accent="blue"
            />
            <SummaryCard
              title="Completed"
              value={ordersSummary.completed}
              subtitle={`${ordersSummary.on_time_count} on time`}
              accent="green"
            />
            <SummaryCard
              title="On-time %"
              value={`${ordersSummary.on_time_percent}%`}
              subtitle="of completed orders"
              accent={ordersSummary.on_time_percent >= 80 ? 'green' : ordersSummary.on_time_percent >= 50 ? 'yellow' : 'red'}
            />
            <SummaryCard
              title="Avg Days to Complete"
              value={ordersSummary.avg_completion_days}
              subtitle="from creation to shipped"
              accent="purple"
            />
          </div>
        ) : null}
      </section>

      {/* Kiln Utilization */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-800">Kiln Utilization</h2>
        {kilnLoading ? (
          <div className="flex h-32 items-center justify-center text-gray-400">Loading...</div>
        ) : kilnError ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            Failed to load kiln data
          </div>
        ) : kilnLoad && kilnLoad.kilns.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-sm text-gray-500">
            No kilns found for the selected filters
          </div>
        ) : kilnLoad ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {kilnLoad.kilns.map((kiln) => (
              <div
                key={kiln.kiln_id}
                className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
              >
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900">{kiln.kiln_name}</h3>
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${utilizationBadge(kiln.utilization_percent)}`}
                  >
                    {kiln.utilization_percent}%
                  </span>
                </div>

                {/* Progress bar */}
                <div className="mb-4">
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
                    <div
                      className={`h-full rounded-full transition-all ${utilizationColor(kiln.utilization_percent)}`}
                      style={{ width: `${Math.min(kiln.utilization_percent, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">Capacity</span>
                    <p className="font-medium text-gray-900">{kiln.capacity_sqm} sqm</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Avg Load</span>
                    <p className="font-medium text-gray-900">{kiln.avg_load_sqm} sqm</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Total Loaded</span>
                    <p className="font-medium text-gray-900">{kiln.total_loaded_sqm} sqm</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Batches</span>
                    <p className="font-medium text-gray-900">
                      {kiln.done_batches} / {kiln.total_batches}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}

/* ---- Helper components ---- */

const accentStyles: Record<string, { bg: string; text: string; border: string }> = {
  blue: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  green: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
  yellow: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' },
  red: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
  purple: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
};

function SummaryCard({
  title,
  value,
  subtitle,
  accent = 'blue',
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  accent?: string;
}) {
  const s = accentStyles[accent] || accentStyles.blue;
  return (
    <div className={`rounded-xl border ${s.border} ${s.bg} p-5`}>
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <p className={`mt-1 text-3xl font-bold ${s.text}`}>{value}</p>
      {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
    </div>
  );
}
