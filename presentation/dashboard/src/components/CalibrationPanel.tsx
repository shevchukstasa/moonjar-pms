import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tpsDashboardApi, type CalibrationStatus } from '@/api/tpsDashboard';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn } from '@/lib/cn';

// ── Drift color coding ─────────────────────────────────────────

function driftColor(drift: number | null): string {
  if (drift === null) return 'text-gray-400 dark:text-stone-500';
  const abs = Math.abs(drift);
  if (abs < 5) return 'text-emerald-600 dark:text-emerald-400';
  if (abs < 15) return 'text-amber-600 dark:text-amber-400';
  return 'text-red-600 dark:text-red-400';
}

function driftBg(drift: number | null): string {
  if (drift === null) return '';
  const abs = Math.abs(drift);
  if (abs < 5) return 'bg-emerald-50 dark:bg-emerald-950/30';
  if (abs < 15) return 'bg-amber-50 dark:bg-amber-950/30';
  return 'bg-red-50 dark:bg-red-950/30';
}

function driftBadge(drift: number | null): string {
  if (drift === null) return 'N/A';
  const abs = Math.abs(drift);
  const sign = drift >= 0 ? '+' : '';
  const label = abs < 5 ? 'OK' : abs < 15 ? 'WARN' : 'ALERT';
  return `${sign}${drift.toFixed(1)}% ${label}`;
}

// ── Toggle Switch ───────────────────────────────────────────────

function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={onChange}
      className={cn(
        'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
        checked
          ? 'bg-emerald-500 dark:bg-emerald-600'
          : 'bg-gray-300 dark:bg-stone-600',
        disabled && 'opacity-50 cursor-not-allowed',
      )}
    >
      <span
        className={cn(
          'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition-transform duration-200 mt-0.5',
          checked ? 'translate-x-4 ml-0.5' : 'translate-x-0 ml-0.5',
        )}
      />
    </button>
  );
}

// ── Main Panel ──────────────────────────────────────────────────

interface CalibrationPanelProps {
  factoryId: string;
}

export function CalibrationPanel({ factoryId }: CalibrationPanelProps) {
  const queryClient = useQueryClient();
  const [applyingStepId, setApplyingStepId] = useState<string | null>(null);

  // Fetch calibration status
  const { data: items, isLoading, error } = useQuery({
    queryKey: ['calibration-status', factoryId],
    queryFn: () => tpsDashboardApi.getCalibrationStatus(factoryId),
    enabled: !!factoryId,
    refetchInterval: 60_000,
  });

  // Toggle auto-calibrate mutation
  const toggleMutation = useMutation({
    mutationFn: (stepId: string) => tpsDashboardApi.toggleStepAutoCalibrate(stepId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calibration-status', factoryId] });
    },
  });

  // Apply calibration mutation
  const applyMutation = useMutation({
    mutationFn: (stepId: string) => tpsDashboardApi.applyCalibrationForStep(stepId),
    onSuccess: () => {
      setApplyingStepId(null);
      queryClient.invalidateQueries({ queryKey: ['calibration-status', factoryId] });
    },
    onError: () => {
      setApplyingStepId(null);
    },
  });

  const handleToggle = useCallback((stepId: string) => {
    toggleMutation.mutate(stepId);
  }, [toggleMutation]);

  const handleApply = useCallback((stepId: string) => {
    setApplyingStepId(stepId);
    applyMutation.mutate(stepId);
  }, [applyMutation]);

  if (isLoading) {
    return (
      <Card title="Calibration">
        <div className="flex items-center justify-center py-8">
          <Spinner />
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="Calibration">
        <p className="text-sm text-red-500 py-4">Failed to load calibration data</p>
      </Card>
    );
  }

  if (!items || items.length === 0) {
    return (
      <Card title="Calibration">
        <EmptyState message="No process steps configured for this factory" />
      </Card>
    );
  }

  return (
    <Card title="Auto-Calibration">
      <p className="text-xs text-gray-500 dark:text-stone-400 mb-3">
        Compares planned rates vs actual EMA (7-day). Toggle auto-calibrate to let the system adjust rates automatically.
      </p>

      <div className="overflow-x-auto -mx-4 px-4">
        <table className="w-full text-sm" role="table" aria-label="Calibration status">
          <thead>
            <tr className="border-b border-gray-200 dark:border-stone-700 text-left text-xs font-medium text-gray-500 dark:text-stone-400 uppercase tracking-wider">
              <th className="pb-2 pr-3">Stage</th>
              <th className="pb-2 pr-3 text-right">Planned</th>
              <th className="pb-2 pr-3 text-right">Actual (EMA)</th>
              <th className="pb-2 pr-3 text-right">Drift</th>
              <th className="pb-2 pr-3 text-center">Auto</th>
              <th className="pb-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item: CalibrationStatus) => {
              const isApplying = applyingStepId === item.step_id;
              const hasData = item.data_points > 0 && item.actual_rate_7d !== null;

              return (
                <tr
                  key={item.step_id}
                  className={cn(
                    'border-b border-gray-100 dark:border-stone-800 transition-colors',
                    driftBg(item.drift_percent),
                  )}
                >
                  {/* Stage name */}
                  <td className="py-2.5 pr-3">
                    <div className="font-medium text-gray-900 dark:text-stone-100">
                      {item.step_name}
                    </div>
                    <div className="text-xs text-gray-400 dark:text-stone-500">
                      {item.stage || 'N/A'}
                      {item.data_points > 0 && (
                        <span className="ml-1">({item.data_points} pts)</span>
                      )}
                    </div>
                  </td>

                  {/* Planned rate */}
                  <td className="py-2.5 pr-3 text-right tabular-nums text-gray-700 dark:text-stone-300">
                    {item.planned_rate !== null ? item.planned_rate.toFixed(1) : '--'}
                    {item.productivity_unit && (
                      <span className="text-xs text-gray-400 dark:text-stone-500 ml-0.5">
                        {item.productivity_unit}
                      </span>
                    )}
                  </td>

                  {/* Actual EMA */}
                  <td className="py-2.5 pr-3 text-right tabular-nums">
                    {hasData ? (
                      <span className="text-gray-700 dark:text-stone-300">
                        {item.actual_rate_7d!.toFixed(1)}
                      </span>
                    ) : (
                      <span className="text-gray-400 dark:text-stone-500">--</span>
                    )}
                  </td>

                  {/* Drift % */}
                  <td className="py-2.5 pr-3 text-right">
                    <span className={cn('font-mono text-xs font-semibold', driftColor(item.drift_percent))}>
                      {driftBadge(item.drift_percent)}
                    </span>
                  </td>

                  {/* Auto-calibrate toggle */}
                  <td className="py-2.5 pr-3 text-center">
                    <Toggle
                      checked={item.auto_calibrate}
                      onChange={() => handleToggle(item.step_id)}
                      disabled={toggleMutation.isPending}
                    />
                  </td>

                  {/* Apply button (manual) */}
                  <td className="py-2.5 text-right">
                    {!item.auto_calibrate && hasData && item.drift_percent !== null && Math.abs(item.drift_percent) >= 5 ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={isApplying || applyMutation.isPending}
                        onClick={() => handleApply(item.step_id)}
                      >
                        {isApplying ? 'Applying...' : 'Apply'}
                      </Button>
                    ) : (
                      <span className="text-xs text-gray-300 dark:text-stone-600">--</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex gap-4 mt-3 text-xs text-gray-500 dark:text-stone-400">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" /> {'<5% OK'}
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-500" /> 5-15% Warn
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-red-500" /> {'>15% Alert'}
        </span>
      </div>
    </Card>
  );
}
