import { FadeIn } from '@/components/ui/AnimatedSection';
import { cn } from '@/lib/cn';
import type { StreakItem, DailyChallengeItem } from '@/api/analytics';

// ── Streak type display config ──────────────────────────────────

const STREAK_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  on_time_delivery: {
    label: 'On-Time',
    icon: '📦',
    color: 'from-amber-400 to-orange-500',
  },
  zero_defects: {
    label: 'Zero Defects',
    icon: '✨',
    color: 'from-emerald-400 to-green-500',
  },
  daily_login: {
    label: 'Daily Login',
    icon: '📅',
    color: 'from-blue-400 to-indigo-500',
  },
  batch_utilization: {
    label: 'Kiln 80%+',
    icon: '🔥',
    color: 'from-red-400 to-rose-500',
  },
};

function getFlameLevel(streak: number): string {
  if (streak >= 30) return '🔥🔥🔥';
  if (streak >= 14) return '🔥🔥';
  if (streak >= 1) return '🔥';
  return '⚪';
}

// ── StreakPill ───────────────────────────────────────────────────

function StreakPill({ streak }: { streak: StreakItem }) {
  const cfg = STREAK_CONFIG[streak.type] || { label: streak.type, icon: '🎯', color: 'from-gray-400 to-gray-500' };
  const isActive = streak.current > 0;

  return (
    <div
      className={cn(
        'flex items-center gap-2 rounded-xl px-3 py-2 transition-all',
        isActive
          ? 'bg-gradient-to-r shadow-md text-white ' + cfg.color
          : 'bg-gray-100 dark:bg-stone-800 text-gray-500 dark:text-gray-400',
      )}
    >
      <span className="text-lg">{cfg.icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1">
          <span className="text-xs font-medium truncate">{cfg.label}</span>
          {isActive && <span className="text-xs opacity-80">{getFlameLevel(streak.current)}</span>}
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className={cn('text-lg font-bold tabular-nums', !isActive && 'text-gray-400 dark:text-gray-500')}>
            {streak.current}
          </span>
          <span className="text-[10px] opacity-70">days</span>
        </div>
      </div>
      {streak.best > 0 && (
        <div className={cn(
          'text-[10px] text-right leading-tight',
          isActive ? 'opacity-80' : 'text-gray-400 dark:text-gray-500',
        )}>
          <div className="font-medium">Best</div>
          <div className="font-bold tabular-nums">{streak.best}</div>
        </div>
      )}
    </div>
  );
}

// ── ChallengeCard ───────────────────────────────────────────────

function ChallengeCard({ challenge }: { challenge: DailyChallengeItem }) {
  const progress = challenge.target_value > 0
    ? Math.min(100, (challenge.actual_value / challenge.target_value) * 100)
    : challenge.actual_value === 0 ? 100 : 0;

  // Special handling for "zero_defects" — target 0 means success when actual = 0
  const isZeroTarget = challenge.type === 'zero_defects';
  const effectiveProgress = isZeroTarget
    ? (challenge.actual_value === 0 ? 100 : 0)
    : progress;

  return (
    <div className={cn(
      'rounded-xl border p-3 transition-all',
      challenge.completed
        ? 'border-amber-300 bg-gradient-to-br from-amber-50 to-yellow-50 dark:from-amber-950/30 dark:to-yellow-950/20 dark:border-amber-700/40'
        : 'border-gray-200 bg-white dark:bg-stone-900/40 dark:border-stone-700',
    )}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-sm">{challenge.completed ? '🏆' : '🎯'}</span>
            <span className="text-[10px] uppercase tracking-wider font-semibold text-amber-600 dark:text-amber-400">
              Daily Challenge
            </span>
          </div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 leading-snug">
            {challenge.title}
          </h4>
          {challenge.description && (
            <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5 leading-tight">
              {challenge.description}
            </p>
          )}
        </div>
        {challenge.completed && (
          <span className="shrink-0 inline-flex items-center gap-0.5 rounded-full bg-amber-100 dark:bg-amber-900/40 px-2 py-0.5 text-[10px] font-bold text-amber-700 dark:text-amber-300">
            Done!
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="mt-2.5">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-gray-500 dark:text-gray-400">Progress</span>
          <span className="text-[10px] font-medium text-gray-600 dark:text-gray-300 tabular-nums">
            {isZeroTarget
              ? `${challenge.actual_value} defects`
              : `${challenge.actual_value} / ${challenge.target_value}`
            }
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-stone-700">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500',
              challenge.completed
                ? 'bg-gradient-to-r from-amber-400 to-yellow-500'
                : 'bg-gradient-to-r from-amber-300 to-amber-400 dark:from-amber-600 dark:to-amber-500',
            )}
            style={{ width: `${effectiveProgress}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// ── Main StreakCard ──────────────────────────────────────────────

interface StreakCardProps {
  streaks: StreakItem[];
  challenge: DailyChallengeItem | null;
  className?: string;
}

export function StreakCard({ streaks, challenge, className }: StreakCardProps) {
  const totalActive = streaks.filter((s) => s.current > 0).length;
  const longestCurrent = Math.max(0, ...streaks.map((s) => s.current));

  return (
    <FadeIn delay={0.1} className={className}>
      <div className="rounded-xl border border-amber-200/60 bg-gradient-to-br from-amber-50/80 via-white to-yellow-50/50 dark:from-amber-950/20 dark:via-stone-900/60 dark:to-yellow-950/10 dark:border-amber-800/30 p-4 shadow-sm">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">{longestCurrent >= 7 ? '🔥' : '🎯'}</span>
            <div>
              <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">Streaks</h3>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">
                {totalActive > 0
                  ? `${totalActive} active streak${totalActive > 1 ? 's' : ''}`
                  : 'Start a streak today!'}
              </p>
            </div>
          </div>
          {longestCurrent > 0 && (
            <div className="text-right">
              <div className="text-lg font-bold text-amber-600 dark:text-amber-400 tabular-nums">
                {longestCurrent}
              </div>
              <div className="text-[10px] text-gray-500 dark:text-gray-400">best active</div>
            </div>
          )}
        </div>

        {/* Streak pills — 2x2 grid */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          {streaks.map((s) => (
            <StreakPill key={s.type} streak={s} />
          ))}
        </div>

        {/* Daily challenge */}
        {challenge && <ChallengeCard challenge={challenge} />}
      </div>
    </FadeIn>
  );
}
