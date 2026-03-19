import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { tasksApi } from '@/api/tasks';

interface DefectAlertBannerProps {
  factoryId?: string;
  onNavigateToTasks: () => void;
}

export function DefectAlertBanner({ factoryId, onNavigateToTasks }: DefectAlertBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  const { data: qualityTasks } = useQuery<{ items: { id: string; status: string }[]; total: number }>({
    queryKey: ['tasks', 'quality-check-pending', factoryId],
    queryFn: () =>
      tasksApi.list({
        task_type: 'quality_check',
        status: 'pending',
        ...(factoryId ? { factory_id: factoryId } : {}),
      }),
    refetchInterval: 60_000,
  });

  const pendingCount = qualityTasks?.total ?? 0;

  if (dismissed || pendingCount === 0) return null;

  return (
    <div className="rounded-lg border border-red-300 bg-gradient-to-r from-red-50 to-orange-50 px-4 py-3 flex items-center justify-between gap-3">
      <div
        className="flex items-center gap-2 cursor-pointer flex-1"
        onClick={onNavigateToTasks}
      >
        <span className="text-lg">&#9888;&#65039;</span>
        <span className="text-sm font-medium text-red-800">
          Defect threshold exceeded: {pendingCount} position{pendingCount > 1 ? 's' : ''} require{pendingCount === 1 ? 's' : ''} 5-Why analysis
        </span>
        <span className="text-xs text-red-600 underline ml-1">View tasks</span>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); setDismissed(true); }}
        className="rounded p-1 text-red-400 hover:bg-red-100 hover:text-red-600"
        title="Dismiss"
      >
        &times;
      </button>
    </div>
  );
}
