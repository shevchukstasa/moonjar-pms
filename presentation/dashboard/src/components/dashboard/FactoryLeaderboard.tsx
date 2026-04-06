import { useState } from 'react';
import { Trophy, TrendingUp, TrendingDown, Minus, Factory } from 'lucide-react';
import { FadeIn } from '@/components/ui/AnimatedSection';
import { cn } from '@/lib/cn';
import { useFactoryLeaderboard } from '@/hooks/useAnalytics';
import type { LeaderboardFactory, LeaderboardMetric } from '@/api/analytics';

// ── Metric display config ─────────────────────────────────────

const METRIC_CONFIG: Record<string, { label: string; unit: string; decimals: number }> = {
  avg_cycle_days: { label: 'Cycle Time', unit: 'd', decimals: 1 },
  defect_rate: { label: 'Defects', unit: '%', decimals: 1 },
  on_time_pct: { label: 'On-Time', unit: '%', decimals: 0 },
  kiln_utilization: { label: 'Kiln Util.', unit: '%', decimals: 0 },
  output_sqm: { label: 'Output', unit: 'm\u00B2', decimals: 0 },
  positions_completed: { label: 'Completed', unit: 'pos', decimals: 0 },
};

const RANK_COLORS = ['', 'text-amber-500', 'text-gray-400', 'text-orange-600'];
const RANK_ICONS = ['', '\uD83E\uDD47', '\uD83E\uDD48', '\uD83E\uDD49'];

function RankBadge({ rank }: { rank: number }) {
  if (rank <= 3) {
    return <span className="text-lg">{RANK_ICONS[rank]}</span>;
  }
  return (
    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-500 dark:bg-stone-700 dark:text-gray-400">
      {rank}
    </span>
  );
}

function DeltaIndicator({ delta, lowerIsBetter }: { delta: number; lowerIsBetter: boolean }) {
  if (Math.abs(delta) < 0.1) {
    return <Minus className="h-3 w-3 text-gray-400" />;
  }
  const isPositive = lowerIsBetter ? delta < 0 : delta > 0;
  const Icon = delta > 0 ? TrendingUp : TrendingDown;
  return (
    <span className={cn('inline-flex items-center gap-0.5 text-[10px] font-medium',
      isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400',
    )}>
      <Icon className="h-3 w-3" />
      {Math.abs(delta).toFixed(delta % 1 === 0 ? 0 : 1)}
    </span>
  );
}

function MetricCell({ metric, metricKey }: { metric: LeaderboardMetric; metricKey: string }) {
  const cfg = METRIC_CONFIG[metricKey] || { label: metricKey, unit: '', decimals: 1 };
  const isTop = metric.rank === 1;

  return (
    <td className={cn(
      'px-3 py-2 text-center tabular-nums',
      isTop && 'bg-amber-50/50 dark:bg-amber-950/20',
    )}>
      <div className="flex flex-col items-center gap-0.5">
        <span className={cn(
          'text-sm font-semibold',
          isTop ? 'text-amber-600 dark:text-amber-400' : 'text-gray-900 dark:text-gray-100',
        )}>
          {metric.value.toFixed(cfg.decimals)}{cfg.unit !== 'pos' && cfg.unit !== 'm\u00B2' ? '' : ''}
          <span className="text-[10px] font-normal text-gray-400 ml-0.5">{cfg.unit}</span>
        </span>
        <DeltaIndicator delta={metric.delta} lowerIsBetter={metric.lower_is_better} />
      </div>
    </td>
  );
}

// ── Main component ────────────────────────────────────────────

export function FactoryLeaderboard({ className }: { className?: string }) {
  const [period, setPeriod] = useState<'week' | 'month'>('week');
  const { data, isLoading, isError } = useFactoryLeaderboard(period);

  if (isLoading) {
    return (
      <div className={cn('rounded-xl border border-gray-200 bg-white p-6 dark:border-stone-700 dark:bg-stone-900', className)}>
        <div className="flex items-center gap-2 mb-4">
          <Trophy className="h-5 w-5 text-amber-500" />
          <h3 className="text-base font-bold text-gray-900 dark:text-gray-100">Factory Leaderboard</h3>
        </div>
        <div className="animate-pulse space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-12 rounded-lg bg-gray-100 dark:bg-stone-800" />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return null;
  }

  const items = data.items || [];
  if (items.length === 0) {
    return null;
  }

  const metricKeys = Object.keys(METRIC_CONFIG);

  return (
    <FadeIn delay={0.15} className={className}>
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-stone-700 dark:bg-stone-900">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-stone-800">
          <div className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-amber-500" />
            <h3 className="text-base font-bold text-gray-900 dark:text-gray-100">Factory Leaderboard</h3>
          </div>
          <div className="flex rounded-lg bg-gray-100 p-0.5 dark:bg-stone-800">
            {(['week', 'month'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={cn(
                  'rounded-md px-3 py-1 text-xs font-medium transition-colors',
                  period === p
                    ? 'bg-white text-gray-900 shadow-sm dark:bg-stone-700 dark:text-gray-100'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300',
                )}
              >
                {p === 'week' ? 'Week' : 'Month'}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 text-[11px] uppercase tracking-wider text-gray-500 dark:border-stone-800 dark:text-gray-400">
                <th className="px-4 py-2 text-left font-semibold">#</th>
                <th className="px-3 py-2 text-left font-semibold">Factory</th>
                {metricKeys.map((key) => (
                  <th key={key} className="px-3 py-2 text-center font-semibold">
                    {METRIC_CONFIG[key].label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((factory) => (
                <tr
                  key={factory.factory_id}
                  className={cn(
                    'border-b border-gray-50 transition-colors hover:bg-gray-50/50 dark:border-stone-800/50 dark:hover:bg-stone-800/30',
                    factory.overall_rank === 1 && 'bg-amber-50/30 dark:bg-amber-950/10',
                  )}
                >
                  <td className="px-4 py-2">
                    <RankBadge rank={factory.overall_rank} />
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Factory className="h-4 w-4 text-gray-400" />
                      <div>
                        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {factory.factory_name}
                        </div>
                        {factory.factory_location && (
                          <div className="text-[10px] text-gray-500 dark:text-gray-400">
                            {factory.factory_location}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  {metricKeys.map((key) => (
                    <MetricCell
                      key={key}
                      metric={factory.metrics[key]}
                      metricKey={key}
                    />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </FadeIn>
  );
}
