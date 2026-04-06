import { cn } from '@/lib/cn';
import { Tooltip } from '@/components/ui/Tooltip';
import type { AchievementItem } from '@/api/analytics';

// Re-export for convenience
export type { AchievementItem };

// ── Achievement display config ────────────────────────────────

const ACHIEVEMENT_CONFIG: Record<string, { label: string; icon: string }> = {
  glazing_master: { label: 'Glazing Master', icon: '\uD83C\uDFA8' },
  zero_defect_hero: { label: 'Zero Defect Hero', icon: '\u2728' },
  speed_champion: { label: 'Speed Champion', icon: '\u26A1' },
  kiln_expert: { label: 'Kiln Expert', icon: '\uD83D\uDD25' },
  quality_star: { label: 'Quality Star', icon: '\u2B50' },
};

const LEVEL_COLORS: Record<number, { bg: string; border: string; text: string }> = {
  0: {
    bg: 'bg-gray-100 dark:bg-stone-800',
    border: 'border-gray-200 dark:border-stone-700',
    text: 'text-gray-400 dark:text-gray-500',
  },
  1: {
    bg: 'bg-emerald-50 dark:bg-emerald-950/20',
    border: 'border-emerald-200 dark:border-emerald-800/40',
    text: 'text-emerald-700 dark:text-emerald-400',
  },
  2: {
    bg: 'bg-blue-50 dark:bg-blue-950/20',
    border: 'border-blue-200 dark:border-blue-800/40',
    text: 'text-blue-700 dark:text-blue-400',
  },
  3: {
    bg: 'bg-purple-50 dark:bg-purple-950/20',
    border: 'border-purple-200 dark:border-purple-800/40',
    text: 'text-purple-700 dark:text-purple-400',
  },
  4: {
    bg: 'bg-gradient-to-br from-amber-50 to-yellow-50 dark:from-amber-950/30 dark:to-yellow-950/20',
    border: 'border-amber-400 dark:border-amber-600 ring-1 ring-amber-200/50 dark:ring-amber-700/30',
    text: 'text-amber-700 dark:text-amber-400',
  },
  5: {
    bg: 'bg-gradient-to-br from-amber-100 to-yellow-100 dark:from-amber-900/40 dark:to-yellow-900/30',
    border: 'border-amber-500 dark:border-amber-500 ring-2 ring-amber-300/50 dark:ring-amber-600/40',
    text: 'text-amber-800 dark:text-amber-300',
  },
};

// ── Single badge ──────────────────────────────────────────────

interface AchievementBadgeProps {
  achievement: AchievementItem;
  size?: 'sm' | 'md';
  className?: string;
}

export function AchievementBadge({ achievement, size = 'md', className }: AchievementBadgeProps) {
  const cfg = ACHIEVEMENT_CONFIG[achievement.achievement_type] || {
    label: achievement.achievement_type,
    icon: '\uD83C\uDFC6',
  };
  const colors = LEVEL_COLORS[achievement.level] || LEVEL_COLORS[0];
  const isLocked = achievement.level === 0;
  const progressPct = achievement.progress_target > 0
    ? Math.min(100, (achievement.progress_current / achievement.progress_target) * 100)
    : 0;

  const isSm = size === 'sm';

  const badge = (
    <div
      className={cn(
        'relative flex flex-col items-center rounded-xl border transition-all',
        colors.bg,
        colors.border,
        isLocked && 'opacity-50 grayscale',
        isSm ? 'p-1.5 gap-0.5' : 'p-2.5 gap-1',
        className,
      )}
    >
      {/* Icon */}
      <span className={cn(isSm ? 'text-lg' : 'text-2xl')}>
        {cfg.icon}
      </span>

      {/* Level indicator */}
      {!isLocked && (
        <div className={cn(
          'flex items-center gap-0.5',
          colors.text,
        )}>
          {Array.from({ length: achievement.level }, (_, i) => (
            <span key={i} className={cn(
              'inline-block rounded-full bg-current',
              isSm ? 'h-1 w-1' : 'h-1.5 w-1.5',
            )} />
          ))}
        </div>
      )}

      {/* Label */}
      {!isSm && (
        <span className={cn(
          'text-[10px] font-semibold text-center leading-tight',
          isLocked ? 'text-gray-400 dark:text-gray-500' : colors.text,
        )}>
          {cfg.label}
        </span>
      )}

      {/* Mini progress bar */}
      {!isLocked && !isSm && (
        <div className="w-full h-1 rounded-full bg-gray-200 dark:bg-stone-700 overflow-hidden mt-0.5">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500',
              achievement.level >= 4
                ? 'bg-gradient-to-r from-amber-400 to-yellow-500'
                : 'bg-current',
              colors.text,
            )}
            style={{ width: `${progressPct}%` }}
          />
        </div>
      )}
    </div>
  );

  const tooltipText = [
    `${cfg.label} - ${achievement.level_name}`,
    `Level ${achievement.level}/5`,
    `Progress: ${achievement.progress_current} / ${achievement.progress_target}`,
    achievement.next_target ? `Next level at: ${achievement.next_target}` : null,
  ].filter(Boolean).join(' | ');

  return (
    <Tooltip text={tooltipText}>
      {badge}
    </Tooltip>
  );
}

// ── Achievement grid ──────────────────────────────────────────

interface AchievementGridProps {
  achievements: AchievementItem[];
  size?: 'sm' | 'md';
  className?: string;
}

export function AchievementGrid({ achievements, size = 'md', className }: AchievementGridProps) {
  if (!achievements.length) return null;

  // Sort: unlocked first (by level desc), then locked
  const sorted = [...achievements].sort((a, b) => {
    if (a.level === 0 && b.level > 0) return 1;
    if (a.level > 0 && b.level === 0) return -1;
    return b.level - a.level;
  });

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {sorted.map((ach) => (
        <AchievementBadge key={ach.achievement_type} achievement={ach} size={size} />
      ))}
    </div>
  );
}
