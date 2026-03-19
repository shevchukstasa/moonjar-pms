import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { tocApi } from '@/api/toc';
import type { BufferHealth } from '@/api/toc';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';

interface BottleneckVisualizationProps {
  factoryId?: string;
}

interface ConstraintItem {
  id: string;
  factory_id: string;
  factory_name: string | null;
  constraint_resource_id: string | null;
  constraint_resource_name: string | null;
  buffer_target_hours: number;
  rope_limit: number | null;
  rope_max_days: number;
  rope_min_days: number;
  batch_mode: string;
  current_bottleneck_utilization: number | null;
}

interface BufferZoneItem {
  order_id: string;
  order_number: string;
  zone: 'green' | 'yellow' | 'red';
  positions_total: number;
  positions_done: number;
  positions_in_progress: number;
}

function getBufferColor(health: string): string {
  switch (health) {
    case 'green':
      return 'bg-green-500';
    case 'yellow':
      return 'bg-yellow-500';
    case 'red':
      return 'bg-red-500';
    default:
      return 'bg-gray-400';
  }
}

function getBufferBgColor(health: string): string {
  switch (health) {
    case 'green':
      return 'bg-green-100';
    case 'yellow':
      return 'bg-yellow-100';
    case 'red':
      return 'bg-red-100';
    default:
      return 'bg-gray-100';
  }
}

function getBufferTextColor(health: string): string {
  switch (health) {
    case 'green':
      return 'text-green-700';
    case 'yellow':
      return 'text-yellow-700';
    case 'red':
      return 'text-red-700';
    default:
      return 'text-gray-700';
  }
}

function getUtilizationColor(pct: number): string {
  if (pct >= 90) return 'text-red-600';
  if (pct >= 70) return 'text-yellow-600';
  return 'text-green-600';
}

/**
 * Drum-Buffer-Rope visualization for TOC bottleneck management.
 *
 * Shows the constraint resource (Drum), buffer status before the constraint,
 * and the rope mechanism controlling input release.
 */
export function BottleneckVisualization({ factoryId }: BottleneckVisualizationProps) {
  const params = useMemo(
    () => (factoryId ? { factory_id: factoryId } : undefined),
    [factoryId],
  );

  const { data: constraintData, isLoading: constraintLoading } = useQuery<{
    items: ConstraintItem[];
    total: number;
  }>({
    queryKey: ['toc-constraints', params],
    queryFn: () => tocApi.listConstraints(params),
    refetchInterval: 60_000,
  });

  const { data: bufferData, isLoading: bufferLoading } = useQuery<{
    items: BufferHealth[];
  }>({
    queryKey: ['toc-buffer-health', params],
    queryFn: () => tocApi.getBufferHealth(params),
    refetchInterval: 60_000,
  });

  const { data: zonesData } = useQuery<{
    items: BufferZoneItem[];
    total: number;
    summary: { green: number; yellow: number; red: number };
  }>({
    queryKey: ['toc-buffer-zones-viz', params],
    queryFn: () => tocApi.getBufferZones(params),
    refetchInterval: 60_000,
  });

  const isLoading = constraintLoading || bufferLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  const constraints = constraintData?.items || [];
  const buffers = bufferData?.items || [];
  const zoneSummary = zonesData?.summary;
  const totalPositions = zonesData?.items?.reduce((sum, z) => sum + (z.positions_total || 0), 0) ?? 0;
  const donePositions = zonesData?.items?.reduce((sum, z) => sum + (z.positions_done || 0), 0) ?? 0;
  const inProgressPositions = zonesData?.items?.reduce((sum, z) => sum + (z.positions_in_progress || 0), 0) ?? 0;

  if (constraints.length === 0 && buffers.length === 0) {
    return (
      <EmptyState
        title="No bottleneck data"
        description="Configure TOC constraints and schedule kiln batches to see the Drum-Buffer-Rope view."
      />
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">Drum-Buffer-Rope</h2>

      {/* Per-constraint DBR row */}
      {constraints.map((constraint) => {
        // Match buffer to constraint by kiln_id, or use first buffer if single
        const buffer = buffers.find(
          (b: BufferHealth) => b.kiln_id === constraint.constraint_resource_id,
        ) ?? (buffers.length === 1 ? buffers[0] : undefined);

        const bufferHours = buffer?.hours ?? 0;
        const targetHours = buffer?.target ?? constraint.buffer_target_hours;
        const bufferPct = targetHours > 0 ? Math.min((bufferHours / targetHours) * 100, 100) : 0;
        const health = buffer?.health ?? 'green';
        const utilization = constraint.current_bottleneck_utilization ?? 0;
        const bufferedCount = buffer?.buffered_count ?? 0;
        const bufferedSqm = buffer?.buffered_sqm ?? 0;

        return (
          <Card key={constraint.id} className="p-0 overflow-hidden">
            {/* Factory label */}
            {constraint.factory_name && (
              <div className="bg-gray-50 px-4 py-2 border-b border-gray-100">
                <span className="text-xs font-medium text-gray-500">{constraint.factory_name}</span>
              </div>
            )}

            {/* DBR pipeline */}
            <div className="p-4">
              <div className="flex items-center gap-3">
                {/* ROPE: Input Queue */}
                <div className="flex-shrink-0 w-28 text-center">
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div className="text-xs font-medium text-gray-500 mb-1">Rope (Input)</div>
                    <div className="text-lg font-bold text-gray-900">{inProgressPositions}</div>
                    <div className="text-xs text-gray-400">positions queued</div>
                    {constraint.rope_limit && (
                      <div className="mt-1 text-xs text-gray-400">
                        limit: {constraint.rope_limit}
                      </div>
                    )}
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex-shrink-0 text-gray-300">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </div>

                {/* BUFFER: Time buffer bar */}
                <div className="flex-1 min-w-0">
                  <div className="rounded-lg border border-gray-200 bg-white p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-500">Buffer</span>
                      <span className={`text-xs font-semibold ${getBufferTextColor(health)}`}>
                        {health.toUpperCase()}
                      </span>
                    </div>

                    {/* Buffer bar */}
                    <div className={`relative h-6 rounded-full overflow-hidden ${getBufferBgColor(health)}`}>
                      <div
                        className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${getBufferColor(health)}`}
                        style={{ width: `${Math.round(bufferPct)}%` }}
                      />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-xs font-bold text-white drop-shadow-sm">
                          {bufferHours.toFixed(1)}h / {targetHours}h
                        </span>
                      </div>
                    </div>

                    {/* Buffer details */}
                    <div className="mt-2 flex justify-between text-xs text-gray-500">
                      <span>{bufferedCount} positions</span>
                      <span>{bufferedSqm.toFixed(1)} sqm buffered</span>
                    </div>
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex-shrink-0 text-gray-300">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </div>

                {/* DRUM: Constraint resource */}
                <div className="flex-shrink-0 w-40 text-center">
                  <div className="rounded-lg border-2 border-indigo-300 bg-indigo-50 p-3">
                    <div className="text-xs font-medium text-indigo-600 mb-1">
                      Drum (Constraint)
                    </div>
                    <div className="text-sm font-bold text-gray-900 truncate">
                      {constraint.constraint_resource_name || 'Kiln'}
                    </div>
                    <div className={`text-xl font-bold mt-1 ${getUtilizationColor(utilization)}`}>
                      {utilization > 0 ? `${utilization.toFixed(0)}%` : '--'}
                    </div>
                    <div className="text-xs text-gray-400">utilization</div>
                    <div className="mt-1 text-xs text-indigo-500">
                      {constraint.batch_mode} mode
                    </div>
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex-shrink-0 text-gray-300">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </div>

                {/* OUTPUT */}
                <div className="flex-shrink-0 w-28 text-center">
                  <div className="rounded-lg border border-green-200 bg-green-50 p-3">
                    <div className="text-xs font-medium text-green-600 mb-1">Output</div>
                    <div className="text-lg font-bold text-green-700">{donePositions}</div>
                    <div className="text-xs text-green-500">
                      of {totalPositions} done
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Throughput summary bar */}
            {zoneSummary && (
              <div className="bg-gray-50 px-4 py-2 border-t border-gray-100 flex items-center gap-4 text-xs">
                <span className="text-gray-500">Zone distribution:</span>
                <span className="inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-gray-600">{zoneSummary.green} green</span>
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-yellow-500" />
                  <span className="text-gray-600">{zoneSummary.yellow} yellow</span>
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
                  <span className="text-gray-600">{zoneSummary.red} red</span>
                </span>
              </div>
            )}
          </Card>
        );
      })}

      {/* If we have buffers but no constraints, show buffer-only view */}
      {constraints.length === 0 && buffers.length > 0 && (
        <Card>
          <div className="text-sm text-gray-500 mb-3">
            Buffer health data available, but no constraint configuration found.
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {buffers.map((buffer: BufferHealth) => {
              const pct = buffer.target > 0 ? Math.round((buffer.hours / buffer.target) * 100) : 0;
              return (
                <div key={buffer.kiln_id} className="rounded-lg border border-gray-200 p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-gray-900">{buffer.kiln_name}</span>
                    <span className={`text-xs font-semibold ${getBufferTextColor(buffer.health)}`}>
                      {buffer.health.toUpperCase()}
                    </span>
                  </div>
                  <div className={`relative h-4 rounded-full overflow-hidden ${getBufferBgColor(buffer.health)}`}>
                    <div
                      className={`absolute inset-y-0 left-0 rounded-full ${getBufferColor(buffer.health)}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="mt-1 flex justify-between text-xs text-gray-500">
                    <span>{buffer.hours}h / {buffer.target}h</span>
                    <span>{buffer.buffered_count} positions</span>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
