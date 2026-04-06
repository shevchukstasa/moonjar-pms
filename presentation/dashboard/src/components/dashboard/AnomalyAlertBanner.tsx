import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi, type AnomalyItem } from '@/api/analytics';

interface AnomalyAlertBannerProps {
  factoryId?: string;
}

const SEVERITY_STYLES = {
  critical: 'border-red-400 bg-gradient-to-r from-red-50 to-red-100 text-red-900',
  warning: 'border-amber-300 bg-gradient-to-r from-amber-50 to-yellow-50 text-amber-900',
};

const SEVERITY_BADGE = {
  critical: 'bg-red-200 text-red-800',
  warning: 'bg-amber-200 text-amber-800',
};

const TYPE_LABELS: Record<string, string> = {
  defect_spike: 'Defect Spike',
  throughput_drop: 'Throughput Drop',
  cycle_time: 'Cycle Time',
  material_excess: 'Material Excess',
  kiln_anomaly: 'Kiln Anomaly',
};

export function AnomalyAlertBanner({ factoryId }: AnomalyAlertBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const { data } = useQuery({
    queryKey: ['analytics', 'anomalies', factoryId],
    queryFn: () =>
      analyticsApi.getAnomalies({
        ...(factoryId ? { factory_id: factoryId } : {}),
      }),
    refetchInterval: 120_000, // 2 minutes
    staleTime: 60_000,
  });

  const total = data?.total ?? 0;
  const criticalCount = data?.critical_count ?? 0;
  const items = data?.items ?? [];

  if (dismissed || total === 0) return null;

  const hasCritical = criticalCount > 0;
  const bannerStyle = hasCritical ? SEVERITY_STYLES.critical : SEVERITY_STYLES.warning;

  return (
    <div className={`rounded-lg border px-4 py-3 ${bannerStyle}`}>
      <div className="flex items-center justify-between gap-3">
        <div
          className="flex items-center gap-2 cursor-pointer flex-1"
          onClick={() => setExpanded(!expanded)}
        >
          <span className="text-lg">{hasCritical ? '⚠️' : '⚡'}</span>
          <span className="text-sm font-medium">
            {total} anomal{total === 1 ? 'y' : 'ies'} detected
            {criticalCount > 0 && ` (${criticalCount} critical)`}
          </span>
          <span className="text-xs underline ml-1 opacity-75">
            {expanded ? 'Collapse' : 'Details'}
          </span>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            setDismissed(true);
          }}
          className="rounded p-1 hover:bg-black/5"
          title="Dismiss"
        >
          &times;
        </button>
      </div>

      {expanded && items.length > 0 && (
        <div className="mt-3 space-y-2 border-t border-black/10 pt-3">
          {items.slice(0, 10).map((item: AnomalyItem, idx: number) => (
            <div
              key={idx}
              className="flex items-start gap-2 text-xs"
            >
              <span
                className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                  SEVERITY_BADGE[item.severity as keyof typeof SEVERITY_BADGE] ?? SEVERITY_BADGE.warning
                }`}
              >
                {item.severity}
              </span>
              <span className="font-medium text-[11px]">
                {TYPE_LABELS[item.type] ?? item.type}
              </span>
              <span className="flex-1 opacity-80">{item.description}</span>
              <span className="whitespace-nowrap font-mono text-[10px] opacity-60">
                z={item.z_score}
              </span>
            </div>
          ))}
          {items.length > 10 && (
            <div className="text-[11px] opacity-60">
              ... and {items.length - 10} more
            </div>
          )}
        </div>
      )}
    </div>
  );
}
