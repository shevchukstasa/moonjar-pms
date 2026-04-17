import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  reportsApi,
  type ReportParams,
  type DailyProductionRow,
  type DailyProductionParams,
} from '@/api/reports';
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

function defectRateColor(pct: number): string {
  if (pct <= 15) return 'text-green-700 bg-green-50';
  if (pct <= 30) return 'text-yellow-700 bg-yellow-50';
  return 'text-red-700 bg-red-50';
}

function defectRateBorder(pct: number): string {
  if (pct <= 15) return 'border-green-200';
  if (pct <= 30) return 'border-yellow-200';
  return 'border-red-200';
}

type TabId = 'overview' | 'daily-production';

const tabs: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'daily-production', label: 'Daily Production' },
];

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [factoryId, setFactoryId] = useState<string>('');
  const [dateFrom, setDateFrom] = useState(formatDate(thirtyDaysAgo));
  const [dateTo, setDateTo] = useState(formatDate(today));

  // Daily production state
  const [dpDate, setDpDate] = useState(formatDate(today));
  const [dpFactoryId, setDpFactoryId] = useState<string>('');

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
    enabled: activeTab === 'overview',
  });

  const {
    data: kilnLoad,
    isLoading: kilnLoading,
    error: kilnError,
  } = useQuery({
    queryKey: ['reports', 'kiln-load', params],
    queryFn: () => reportsApi.kilnLoad(params),
    enabled: activeTab === 'overview',
  });

  const dpParams: DailyProductionParams | null = dpFactoryId
    ? { factory_id: dpFactoryId, date: dpDate }
    : null;

  const {
    data: dailyProduction,
    isLoading: dpLoading,
    error: dpError,
  } = useQuery({
    queryKey: ['reports', 'daily-production', dpParams],
    queryFn: () => reportsApi.dailyProduction(dpParams!),
    enabled: activeTab === 'daily-production' && !!dpParams,
  });

  const factoryList = factories?.items ?? factories ?? [];

  // Auto-select first factory for daily production if none selected
  if (!dpFactoryId && Array.isArray(factoryList) && factoryList.length > 0) {
    setDpFactoryId(factoryList[0].id);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap border-b-2 py-3 px-1 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <OverviewTab
          factoryId={factoryId}
          setFactoryId={setFactoryId}
          dateFrom={dateFrom}
          setDateFrom={setDateFrom}
          dateTo={dateTo}
          setDateTo={setDateTo}
          factoryList={factoryList}
          ordersSummary={ordersSummary}
          ordersLoading={ordersLoading}
          ordersError={ordersError}
          kilnLoad={kilnLoad}
          kilnLoading={kilnLoading}
          kilnError={kilnError}
        />
      )}

      {activeTab === 'daily-production' && (
        <DailyProductionTab
          factoryId={dpFactoryId}
          setFactoryId={setDpFactoryId}
          reportDate={dpDate}
          setReportDate={setDpDate}
          factoryList={factoryList}
          data={dailyProduction}
          isLoading={dpLoading}
          error={dpError}
        />
      )}
    </div>
  );
}

/* ===== Overview Tab ===== */

function OverviewTab({
  factoryId,
  setFactoryId,
  dateFrom,
  setDateFrom,
  dateTo,
  setDateTo,
  factoryList,
  ordersSummary,
  ordersLoading,
  ordersError,
  kilnLoad,
  kilnLoading,
  kilnError,
}: {
  factoryId: string;
  setFactoryId: (v: string) => void;
  dateFrom: string;
  setDateFrom: (v: string) => void;
  dateTo: string;
  setDateTo: (v: string) => void;
  factoryList: { id: string; name: string }[];
  ordersSummary: any;
  ordersLoading: boolean;
  ordersError: any;
  kilnLoad: any;
  kilnLoading: boolean;
  kilnError: any;
}) {
  return (
    <div className="space-y-6">
      {/* Filters */}
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
            {kilnLoad.kilns.map((kiln: any) => (
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

/* ===== Daily Production Tab ===== */

function DailyProductionTab({
  factoryId,
  setFactoryId,
  reportDate,
  setReportDate,
  factoryList,
  data,
  isLoading,
  error,
}: {
  factoryId: string;
  setFactoryId: (v: string) => void;
  reportDate: string;
  setReportDate: (v: string) => void;
  factoryList: { id: string; name: string }[];
  data: any;
  isLoading: boolean;
  error: any;
}) {
  // Navigate date forward/backward
  const shiftDate = (days: number) => {
    const d = new Date(reportDate);
    d.setDate(d.getDate() + days);
    setReportDate(formatDate(d));
  };

  return (
    <div className="space-y-5">
      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Factory</label>
          <select
            value={factoryId}
            onChange={(e) => setFactoryId(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {Array.isArray(factoryList) &&
              factoryList.map((f: { id: string; name: string }) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Date</label>
          <div className="flex items-center gap-1">
            <button
              onClick={() => shiftDate(-1)}
              className="rounded-lg border border-gray-300 bg-white px-2.5 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              title="Previous day"
            >
              &larr;
            </button>
            <DatePicker
              value={reportDate}
              onChange={(v) => setReportDate(v)}
              className="rounded-lg shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={() => shiftDate(1)}
              className="rounded-lg border border-gray-300 bg-white px-2.5 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              title="Next day"
            >
              &rarr;
            </button>
            <button
              onClick={() => setReportDate(formatDate(new Date()))}
              className="ml-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Today
            </button>
          </div>
        </div>
      </div>

      {/* No factory selected */}
      {!factoryId && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-sm text-gray-500">
          Select a factory to view the daily production report
        </div>
      )}

      {/* Loading */}
      {factoryId && isLoading && (
        <div className="flex h-40 items-center justify-center text-gray-400">Loading report...</div>
      )}

      {/* Error */}
      {factoryId && error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          Failed to load daily production report
        </div>
      )}

      {/* Report content */}
      {factoryId && data && !isLoading && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <MiniCard label="Sorted" value={data.summary.total_sorted} accent="blue" />
            <MiniCard label="Packed" value={data.summary.total_packed} accent="green" />
            <MiniCard label="Total Reject" value={data.summary.total_reject} accent="red" />
            <MiniCard
              label="Defect Rate"
              value={`${data.summary.defect_rate_pct}%`}
              accent={data.summary.defect_rate_pct <= 15 ? 'green' : data.summary.defect_rate_pct <= 30 ? 'yellow' : 'red'}
            />
            <MiniCard label="Write-off" value={data.summary.total_write_off} accent="purple" />
          </div>

          {/* Table */}
          {data.rows.length === 0 ? (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-sm text-gray-500">
              No production activity recorded for this date
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Order</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Color</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Method</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Size</th>
                    <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Sorted</th>
                    <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Refire</th>
                    <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Repair</th>
                    <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Grinding</th>
                    <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap">Color Mis.</th>
                    <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap">Write-off</th>
                    <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap">Total Rej.</th>
                    <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Packed</th>
                    <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap">Defect %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.rows.map((row: DailyProductionRow, idx: number) => (
                    <tr key={idx} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-3 py-2.5 text-sm font-medium text-gray-900 whitespace-nowrap">{row.order_number}</td>
                      <td className="px-3 py-2.5 text-sm text-gray-700">{row.color}</td>
                      <td className="px-3 py-2.5 text-sm text-gray-700">{row.method}</td>
                      <td className="px-3 py-2.5 text-sm text-gray-700">{row.size}</td>
                      <td className="px-3 py-2.5 text-sm text-right font-medium text-gray-900">{row.sorted || '-'}</td>
                      <td className="px-3 py-2.5 text-sm text-right text-gray-600">{row.refire || '-'}</td>
                      <td className="px-3 py-2.5 text-sm text-right text-gray-600">{row.repair || '-'}</td>
                      <td className="px-3 py-2.5 text-sm text-right text-gray-600">{row.grinding || '-'}</td>
                      <td className="px-3 py-2.5 text-sm text-right text-gray-600">{row.color_mismatch || '-'}</td>
                      <td className="px-3 py-2.5 text-sm text-right text-gray-600">{row.write_off || '-'}</td>
                      <td className="px-3 py-2.5 text-sm text-right font-semibold text-gray-900">{row.total_reject || '-'}</td>
                      <td className="px-3 py-2.5 text-sm text-right font-medium text-green-700">{row.packed || '-'}</td>
                      <td className="px-3 py-2.5 text-right">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${defectRateColor(row.defect_rate_pct)}`}>
                          {row.defect_rate_pct}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
                {/* Summary footer row */}
                <tfoot>
                  <tr className="bg-gray-50 border-t-2 border-gray-300">
                    <td colSpan={4} className="px-3 py-3 text-sm font-bold text-gray-900 uppercase">
                      Total
                    </td>
                    <td className="px-3 py-3 text-sm text-right font-bold text-gray-900">{data.summary.total_sorted}</td>
                    <td className="px-3 py-3 text-sm text-right font-bold text-gray-700">{data.summary.total_refire}</td>
                    <td className="px-3 py-3 text-sm text-right font-bold text-gray-700">{data.summary.total_repair}</td>
                    <td className="px-3 py-3 text-sm text-right font-bold text-gray-700">{data.summary.total_grinding}</td>
                    <td className="px-3 py-3 text-sm text-right font-bold text-gray-700">{data.summary.total_color_mismatch}</td>
                    <td className="px-3 py-3 text-sm text-right font-bold text-gray-700">{data.summary.total_write_off}</td>
                    <td className="px-3 py-3 text-sm text-right font-bold text-gray-900">{data.summary.total_reject}</td>
                    <td className="px-3 py-3 text-sm text-right font-bold text-green-700">{data.summary.total_packed}</td>
                    <td className="px-3 py-3 text-right">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold ${defectRateColor(data.summary.defect_rate_pct)} border ${defectRateBorder(data.summary.defect_rate_pct)}`}>
                        {data.summary.defect_rate_pct}%
                      </span>
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </>
      )}
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

function MiniCard({
  label,
  value,
  accent = 'blue',
}: {
  label: string;
  value: string | number;
  accent?: string;
}) {
  const s = accentStyles[accent] || accentStyles.blue;
  return (
    <div className={`rounded-xl border ${s.border} ${s.bg} px-4 py-3`}>
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className={`mt-0.5 text-2xl font-bold ${s.text}`}>{value}</p>
    </div>
  );
}
