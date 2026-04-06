import { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useFactory } from '@/hooks/useFactory';
import { useAuthStore } from '@/stores/authStore';
import {
  useSkillBadges,
  useUserSkills,
  useCompetitions,
  useCompetitionStandings,
  usePrizes,
  useCeoDashboard,
  useProductivityImpact,
  useSeasons,
  useStartSkill,
  useCertifySkill,
  useRevokeSkill,
  useCreateCompetition,
  useApproveCompetition,
  useUpdateScores,
  useApprovePrize,
  useRejectPrize,
  useAwardPrize,
  useGenerateMonthlyPrizes,
  useSeedSkillBadges,
  useSendCeoReport,
} from '@/hooks/useGamification';
import type { Competition, UserSkill, Prize, CompetitionStanding } from '@/api/gamification';
import { Tabs } from '@/components/ui/Tabs';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { FadeIn, ScaleIn } from '@/components/ui/AnimatedSection';
import { cn } from '@/lib/cn';

// ── Constants ────────────────────────────────────────────────────

const SKILL_CATEGORY_ICONS: Record<string, string> = {
  production: '🏭',
  quality: '🔬',
  kiln: '🔥',
  glazing: '🎨',
  leadership: '⭐',
  safety: '🛡',
};

const SKILL_STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  learning: { label: 'Learning', color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-500/10' },
  pending_certification: { label: 'Pending Review', color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-500/10' },
  certified: { label: 'Certified', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
  revoked: { label: 'Revoked', color: 'text-red-500 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-500/10' },
};

const COMPETITION_STATUS_CONFIG: Record<string, { label: string; dot: string }> = {
  proposed: { label: 'Proposed', dot: 'bg-gray-400' },
  upcoming: { label: 'Upcoming', dot: 'bg-blue-500' },
  active: { label: 'Live', dot: 'bg-emerald-500 animate-pulse' },
  completed: { label: 'Completed', dot: 'bg-stone-400' },
  cancelled: { label: 'Cancelled', dot: 'bg-red-400' },
};

const PRIZE_STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  pending: { label: 'Pending', color: 'text-amber-600 dark:text-amber-400' },
  approved: { label: 'Approved', color: 'text-blue-600 dark:text-blue-400' },
  rejected: { label: 'Rejected', color: 'text-red-500 dark:text-red-400' },
  awarded: { label: 'Awarded', color: 'text-emerald-600 dark:text-emerald-400' },
};

const RANK_DECORATIONS = [
  { emoji: '🥇', ring: 'ring-amber-400 dark:ring-amber-500', glow: 'shadow-amber-200/60 dark:shadow-amber-500/20' },
  { emoji: '🥈', ring: 'ring-gray-400 dark:ring-gray-500', glow: 'shadow-gray-200/60 dark:shadow-gray-500/20' },
  { emoji: '🥉', ring: 'ring-orange-400 dark:ring-orange-600', glow: 'shadow-orange-200/60 dark:shadow-orange-600/20' },
];

// ── Small helpers ────────────────────────────────────────────────

function formatIDR(amount: number | null | undefined) {
  if (amount == null) return '-';
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(amount);
}

function daysLeft(endDate: string) {
  const diff = Math.ceil((new Date(endDate).getTime() - Date.now()) / 86_400_000);
  return diff > 0 ? diff : 0;
}

function pctOf(value: number, max: number) {
  if (max <= 0) return 0;
  return Math.min(100, Math.round((value / max) * 100));
}

// ── Gradient Progress Bar ────────────────────────────────────────

function GradientBar({ value, max, className }: { value: number; max: number; className?: string }) {
  const pct = pctOf(value, max);
  return (
    <div className={cn('relative h-2.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-stone-800', className)}>
      <motion.div
        className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-blue-500 via-violet-500 to-fuchsia-500 dark:from-gold-600 dark:via-amber-500 dark:to-orange-400"
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
      />
      {pct >= 100 && (
        <motion.div
          className="absolute inset-0 rounded-full bg-gradient-to-r from-emerald-400/30 to-emerald-600/30"
          animate={{ opacity: [0.3, 0.7, 0.3] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
    </div>
  );
}

// ── Stat Pill ────────────────────────────────────────────────────

function StatPill({ icon, label, value }: { icon: string; label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-2 rounded-xl bg-white/70 px-3 py-2 shadow-sm ring-1 ring-gray-100 backdrop-blur dark:bg-stone-900/50 dark:ring-stone-800">
      <span className="text-lg">{icon}</span>
      <div>
        <div className="text-xs text-gray-500 dark:text-stone-500">{label}</div>
        <div className="text-sm font-bold text-gray-900 dark:text-stone-100">{value}</div>
      </div>
    </div>
  );
}

// ── Celebration Confetti (inline SVG burst) ──────────────────────

function ConfettiBurst({ show }: { show: boolean }) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center"
          initial={{ opacity: 1 }}
          animate={{ opacity: 0 }}
          transition={{ duration: 1.2, delay: 0.3 }}
        >
          {Array.from({ length: 12 }).map((_, i) => {
            const angle = (i * 30) * (Math.PI / 180);
            const dist = 40 + Math.random() * 20;
            const colors = ['#f59e0b', '#8b5cf6', '#10b981', '#f43f5e', '#3b82f6', '#ec4899'];
            return (
              <motion.div
                key={i}
                className="absolute h-2 w-2 rounded-full"
                style={{ backgroundColor: colors[i % colors.length] }}
                initial={{ x: 0, y: 0, scale: 1 }}
                animate={{ x: Math.cos(angle) * dist, y: Math.sin(angle) * dist, scale: 0, opacity: 0 }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            );
          })}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ══════════════════════════════════════════════════════════════════
//  TAB: Leaderboard
// ══════════════════════════════════════════════════════════════════

function LeaderboardTab({ factoryId }: { factoryId: string }) {
  const { data: competitions, isLoading: loadingComp } = useCompetitions(factoryId, 'active');
  const [selectedComp, setSelectedComp] = useState<string | null>(null);

  const activeCompId = selectedComp || competitions?.[0]?.id;
  const { data: standings, isLoading: loadingStandings } = useCompetitionStandings(activeCompId || undefined);
  const selectedCompetition = competitions?.find((c) => c.id === activeCompId);

  if (loadingComp) return <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>;
  if (!competitions?.length) {
    return <EmptyState title="No active competitions" description="Create a competition to see leaderboard standings" />;
  }

  return (
    <FadeIn className="space-y-6">
      {/* Competition selector */}
      {competitions.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {competitions.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedComp(c.id)}
              className={cn(
                'rounded-full px-4 py-1.5 text-sm font-medium transition-all',
                activeCompId === c.id
                  ? 'bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white shadow-md dark:from-gold-500 dark:to-amber-500 dark:text-stone-950'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-stone-800 dark:text-stone-400 dark:hover:bg-stone-700',
              )}
            >
              {c.title}
            </button>
          ))}
        </div>
      )}

      {/* Competition info header */}
      {selectedCompetition && (
        <Card variant="glass" className="flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[200px]">
            <h3 className="text-lg font-bold text-gray-900 dark:text-stone-100">{selectedCompetition.title}</h3>
            <p className="text-sm text-gray-500 dark:text-stone-500">
              {selectedCompetition.competition_type === 'team' ? 'Team' : 'Individual'} &middot; {selectedCompetition.metric}
            </p>
          </div>
          <div className="flex gap-3">
            <StatPill icon="⏳" label="Days left" value={daysLeft(selectedCompetition.end_date)} />
            {selectedCompetition.prize_budget_idr && (
              <StatPill icon="🏆" label="Prize pool" value={formatIDR(selectedCompetition.prize_budget_idr)} />
            )}
          </div>
        </Card>
      )}

      {/* Standings */}
      {loadingStandings ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : !standings?.length ? (
        <EmptyState title="No standings yet" description="Scores will appear once the competition starts" />
      ) : (
        <div className="space-y-2">
          {standings.map((s, i) => (
            <LeaderboardRow key={s.user_id} standing={s} index={i} />
          ))}
        </div>
      )}
    </FadeIn>
  );
}

function LeaderboardRow({ standing, index }: { standing: CompetitionStanding; index: number }) {
  const deco = RANK_DECORATIONS[index];
  const isTop3 = index < 3;

  return (
    <ScaleIn delay={index * 0.05}>
      <div
        className={cn(
          'group flex items-center gap-4 rounded-xl px-4 py-3 transition-all',
          isTop3
            ? 'bg-white shadow-sm ring-1 ring-gray-100 hover:shadow-md dark:bg-stone-900/60 dark:ring-stone-800'
            : 'hover:bg-gray-50 dark:hover:bg-stone-900/30',
        )}
      >
        {/* Rank */}
        <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold', isTop3 ? `ring-2 ${deco?.ring} shadow-lg ${deco?.glow}` : '')}>
          {isTop3 ? (
            <span className="text-xl">{deco?.emoji}</span>
          ) : (
            <span className="text-gray-400 dark:text-stone-600">#{standing.rank}</span>
          )}
        </div>

        {/* Name */}
        <div className="flex-1 min-w-0">
          <div className="truncate font-semibold text-gray-900 dark:text-stone-100">
            {standing.user_name}
            {standing.team_name && <span className="ml-2 text-xs text-gray-400 dark:text-stone-600">({standing.team_name})</span>}
          </div>
          <div className="flex gap-3 mt-0.5">
            <span className="text-xs text-gray-500 dark:text-stone-500">Quality: {standing.quality_score}</span>
            <span className="text-xs text-gray-500 dark:text-stone-500">Speed: {standing.speed_score}</span>
            {standing.streak_days > 0 && (
              <span className="text-xs text-orange-500 dark:text-orange-400">{'🔥'} {standing.streak_days}d streak</span>
            )}
          </div>
        </div>

        {/* Score */}
        <div className="text-right">
          <div className="text-lg font-black tabular-nums text-gray-900 dark:text-stone-100">{standing.score}</div>
          <div className="text-[10px] uppercase tracking-wider text-gray-400 dark:text-stone-600">pts</div>
        </div>
      </div>
    </ScaleIn>
  );
}

// ══════════════════════════════════════════════════════════════════
//  TAB: Skills
// ══════════════════════════════════════════════════════════════════

function SkillsTab({ factoryId }: { factoryId: string }) {
  const user = useAuthStore((s) => s.user);
  const isManager = user && ['owner', 'administrator', 'production_manager', 'ceo'].includes(user.role);
  const { data: badges, isLoading: loadingBadges } = useSkillBadges(factoryId);
  const { data: userSkills, isLoading: loadingSkills } = useUserSkills(user?.id, factoryId);
  const startSkill = useStartSkill();
  const certifySkill = useCertifySkill();
  const revokeSkill = useRevokeSkill();
  const seedSkills = useSeedSkillBadges();
  const [celebrateId, setCelebrateId] = useState<string | null>(null);

  const skillMap = useMemo(() => {
    const m = new Map<string, UserSkill>();
    userSkills?.forEach((s) => m.set(s.skill_badge_id, s));
    return m;
  }, [userSkills]);

  const handleCertify = useCallback((userSkillId: string) => {
    certifySkill.mutate(userSkillId, {
      onSuccess: () => {
        setCelebrateId(userSkillId);
        setTimeout(() => setCelebrateId(null), 1500);
      },
    });
  }, [certifySkill]);

  if (loadingBadges || loadingSkills) return <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>;

  if (!badges?.length) {
    return (
      <FadeIn className="flex flex-col items-center gap-4 py-16">
        <EmptyState title="No skill badges configured" description="Seed the default skill badges to get started" />
        {isManager && (
          <Button variant="gold" onClick={() => seedSkills.mutate(factoryId)} disabled={seedSkills.isPending}>
            {seedSkills.isPending ? 'Seeding...' : 'Seed Default Skills'}
          </Button>
        )}
      </FadeIn>
    );
  }

  // Group by category
  const grouped = badges.reduce<Record<string, typeof badges>>((acc, b) => {
    const cat = b.category || 'other';
    (acc[cat] ??= []).push(b);
    return acc;
  }, {});

  return (
    <FadeIn className="space-y-8">
      {Object.entries(grouped).map(([category, badgeList]) => (
        <div key={category}>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-gray-500 dark:text-stone-500">
            <span>{SKILL_CATEGORY_ICONS[category] || '📚'}</span>
            {category}
          </h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {badgeList.map((badge, i) => {
              const us = skillMap.get(badge.id);
              return (
                <SkillCard
                  key={badge.id}
                  badge={badge}
                  userSkill={us}
                  index={i}
                  isManager={!!isManager}
                  celebrating={celebrateId === us?.id}
                  onStart={() => startSkill.mutate(badge.id)}
                  onCertify={() => us && handleCertify(us.id)}
                  onRevoke={() => us && revokeSkill.mutate(us.id)}
                  startPending={startSkill.isPending}
                />
              );
            })}
          </div>
        </div>
      ))}
    </FadeIn>
  );
}

function SkillCard({
  badge,
  userSkill,
  index,
  isManager,
  celebrating,
  onStart,
  onCertify,
  onRevoke,
  startPending,
}: {
  badge: ReturnType<typeof useSkillBadges>['data'] extends (infer T)[] ? T : never;
  userSkill?: UserSkill;
  index: number;
  isManager: boolean;
  celebrating: boolean;
  onStart: () => void;
  onCertify: () => void;
  onRevoke: () => void;
  startPending: boolean;
}) {
  const status = userSkill?.status;
  const cfg = status ? SKILL_STATUS_CONFIG[status] : null;
  const progress = userSkill ? pctOf(userSkill.operations_completed, badge.required_operations) : 0;
  const isCertified = status === 'certified';

  return (
    <ScaleIn delay={index * 0.04}>
      <div className={cn(
        'relative overflow-hidden rounded-xl border p-4 transition-all hover:shadow-md',
        isCertified
          ? 'border-emerald-200 bg-gradient-to-br from-emerald-50/80 to-white dark:border-emerald-800/50 dark:from-emerald-950/30 dark:to-stone-900/60'
          : 'border-gray-200 bg-white dark:border-stone-800 dark:bg-stone-900/60',
      )}>
        <ConfettiBurst show={celebrating} />

        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{badge.icon || SKILL_CATEGORY_ICONS[badge.category] || '📚'}</span>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-stone-100">{badge.name}</h4>
              {badge.description && (
                <p className="text-xs text-gray-500 dark:text-stone-500 mt-0.5 line-clamp-1">{badge.description}</p>
              )}
            </div>
          </div>
          {cfg && (
            <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider', cfg.color, cfg.bg)}>
              {cfg.label}
            </span>
          )}
        </div>

        {/* Progress */}
        {userSkill && status !== 'certified' && status !== 'revoked' && (
          <div className="mt-3 space-y-1">
            <div className="flex justify-between text-xs text-gray-500 dark:text-stone-500">
              <span>{userSkill.operations_completed} / {badge.required_operations} ops</span>
              <span>{progress}%</span>
            </div>
            <GradientBar value={userSkill.operations_completed} max={badge.required_operations} />
            <div className="text-xs text-gray-400 dark:text-stone-600">
              Zero-defect: {userSkill.zero_defect_pct.toFixed(1)}% (need {badge.required_zero_defect_pct}%)
            </div>
          </div>
        )}

        {/* Certified badge decoration */}
        {isCertified && (
          <div className="mt-3 flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400">
            <span className="text-base">{'✅'}</span>
            <span className="font-medium">Certified</span>
            <span className="text-xs text-gray-400 dark:text-stone-600 ml-auto">+{badge.points_on_earn} pts</span>
          </div>
        )}

        {/* Points indicator for unstarted */}
        {!userSkill && (
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs text-gray-400 dark:text-stone-600">
              {badge.required_operations} ops &middot; {badge.required_zero_defect_pct}% zero-defect
            </span>
            <span className="text-xs font-semibold text-violet-500 dark:text-amber-500">+{badge.points_on_earn} pts</span>
          </div>
        )}

        {/* Actions */}
        <div className="mt-3 flex gap-2">
          {!userSkill && (
            <Button size="sm" variant="secondary" onClick={onStart} disabled={startPending}>
              Start Learning
            </Button>
          )}
          {isManager && status === 'pending_certification' && (
            <>
              <Button size="sm" variant="gold" onClick={onCertify}>Certify</Button>
              <Button size="sm" variant="ghost" onClick={onRevoke}>Deny</Button>
            </>
          )}
          {isManager && status === 'certified' && (
            <Button size="sm" variant="ghost" onClick={onRevoke} className="text-red-500">Revoke</Button>
          )}
        </div>
      </div>
    </ScaleIn>
  );
}

// ══════════════════════════════════════════════════════════════════
//  TAB: Competitions
// ══════════════════════════════════════════════════════════════════

function CompetitionsTab({ factoryId }: { factoryId: string }) {
  const user = useAuthStore((s) => s.user);
  const isManager = user && ['owner', 'administrator', 'production_manager', 'ceo'].includes(user.role);
  const { data: competitions, isLoading } = useCompetitions(factoryId);
  const approveComp = useApproveCompetition();
  const updateScores = useUpdateScores();
  const createComp = useCreateCompetition();
  const [showCreate, setShowCreate] = useState(false);

  if (isLoading) return <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>;
  if (!competitions?.length && !showCreate) {
    return (
      <FadeIn className="flex flex-col items-center gap-4 py-16">
        <EmptyState title="No competitions yet" description="Create the first competition to motivate your team" />
        {isManager && <Button variant="gold" onClick={() => setShowCreate(true)}>Create Competition</Button>}
      </FadeIn>
    );
  }

  // Split active vs past
  const active = competitions?.filter((c) => ['active', 'upcoming', 'proposed'].includes(c.status)) || [];
  const past = competitions?.filter((c) => ['completed', 'cancelled'].includes(c.status)) || [];

  return (
    <FadeIn className="space-y-6">
      {/* Actions bar */}
      {isManager && (
        <div className="flex flex-wrap gap-2">
          <Button variant="gold" size="sm" onClick={() => setShowCreate(true)}>+ New Competition</Button>
          <Button variant="secondary" size="sm" onClick={() => updateScores.mutate(factoryId)} disabled={updateScores.isPending}>
            {updateScores.isPending ? 'Updating...' : 'Refresh Scores'}
          </Button>
        </div>
      )}

      {/* Create form */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <CreateCompetitionForm
              factoryId={factoryId}
              onCreate={(data) => createComp.mutate({ factoryId, data }, { onSuccess: () => setShowCreate(false) })}
              onCancel={() => setShowCreate(false)}
              pending={createComp.isPending}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Active */}
      {active.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-gray-500 dark:text-stone-500">
            {'⚡'} Active & Upcoming
          </h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {active.map((c, i) => (
              <CompetitionCard
                key={c.id}
                competition={c}
                index={i}
                isManager={!!isManager}
                onApprove={() => approveComp.mutate(c.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Past */}
      {past.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-gray-500 dark:text-stone-500">
            {'📅'} Past Competitions
          </h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {past.map((c, i) => (
              <CompetitionCard key={c.id} competition={c} index={i} isManager={false} />
            ))}
          </div>
        </div>
      )}
    </FadeIn>
  );
}

function CompetitionCard({
  competition,
  index,
  isManager,
  onApprove,
}: {
  competition: Competition;
  index: number;
  isManager: boolean;
  onApprove?: () => void;
}) {
  const cfg = COMPETITION_STATUS_CONFIG[competition.status] || { label: competition.status, dot: 'bg-gray-400' };
  const days = daysLeft(competition.end_date);
  const totalDays = Math.max(1, Math.ceil((new Date(competition.end_date).getTime() - new Date(competition.start_date).getTime()) / 86_400_000));
  const elapsed = totalDays - days;
  const isActive = competition.status === 'active';

  return (
    <ScaleIn delay={index * 0.05}>
      <Card variant="glass" className={cn('relative overflow-hidden', isActive && 'ring-1 ring-emerald-300 dark:ring-emerald-700')}>
        {/* Status badge */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className={cn('h-2 w-2 rounded-full', cfg.dot)} />
            <span className="text-xs font-medium text-gray-500 dark:text-stone-500">{cfg.label}</span>
          </div>
          {competition.competition_type === 'team' && (
            <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-bold text-violet-600 dark:bg-violet-500/10 dark:text-violet-400">
              TEAM
            </span>
          )}
        </div>

        {/* Title & info */}
        <h4 className="font-bold text-gray-900 dark:text-stone-100">{competition.title}</h4>
        <p className="mt-1 text-xs text-gray-500 dark:text-stone-500">
          {new Date(competition.start_date).toLocaleDateString()} &mdash; {new Date(competition.end_date).toLocaleDateString()}
        </p>

        {/* Progress */}
        {isActive && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-gray-400 dark:text-stone-600 mb-1">
              <span>Progress</span>
              <span>{days}d left</span>
            </div>
            <GradientBar value={elapsed} max={totalDays} />
          </div>
        )}

        {/* Prize */}
        {competition.prize_description && (
          <div className="mt-3 flex items-center gap-1.5 text-sm">
            <span>{'🎁'}</span>
            <span className="text-gray-600 dark:text-stone-400">{competition.prize_description}</span>
          </div>
        )}
        {competition.prize_budget_idr && (
          <div className="text-xs text-amber-600 dark:text-amber-400 font-medium mt-1">
            {formatIDR(competition.prize_budget_idr)}
          </div>
        )}

        {/* Approve button for proposed */}
        {isManager && competition.status === 'proposed' && onApprove && (
          <div className="mt-3">
            <Button size="sm" variant="gold" onClick={onApprove}>Approve</Button>
          </div>
        )}
      </Card>
    </ScaleIn>
  );
}

function CreateCompetitionForm({
  factoryId,
  onCreate,
  onCancel,
  pending,
}: {
  factoryId: string;
  onCreate: (data: { title: string; start_date: string; end_date: string; metric: string; prize_description?: string; prize_budget_idr?: number }) => void;
  onCancel: () => void;
  pending: boolean;
}) {
  const [title, setTitle] = useState('');
  const [metric, setMetric] = useState('combined');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [prize, setPrize] = useState('');
  const [budget, setBudget] = useState('');

  return (
    <Card className="space-y-4">
      <h3 className="font-bold text-gray-900 dark:text-stone-100">New Competition</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-stone-500">Title</label>
          <input
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 focus:ring-violet-500 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100 dark:focus:ring-gold-500"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Monthly Speed Challenge"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-stone-500">Metric</label>
          <select
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
          >
            <option value="combined">Combined</option>
            <option value="quality">Quality</option>
            <option value="speed">Speed</option>
            <option value="zero_defect">Zero Defect</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-stone-500">Start Date</label>
          <input
            type="date"
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-stone-500">End Date</label>
          <input
            type="date"
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-stone-500">Prize Description</label>
          <input
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
            value={prize}
            onChange={(e) => setPrize(e.target.value)}
            placeholder="Bonus + extra day off"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-stone-500">Prize Budget (IDR)</label>
          <input
            type="number"
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder="500000"
          />
        </div>
      </div>
      <div className="flex gap-2">
        <Button
          variant="gold"
          disabled={!title || !startDate || !endDate || pending}
          onClick={() => onCreate({
            title,
            start_date: startDate,
            end_date: endDate,
            metric,
            prize_description: prize || undefined,
            prize_budget_idr: budget ? Number(budget) : undefined,
          })}
        >
          {pending ? 'Creating...' : 'Create'}
        </Button>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════════
//  TAB: Prizes
// ══════════════════════════════════════════════════════════════════

function PrizesTab({ factoryId }: { factoryId: string }) {
  const user = useAuthStore((s) => s.user);
  const isOwner = user && ['owner', 'ceo'].includes(user.role);
  const { data: prizes, isLoading } = usePrizes(factoryId);
  const generatePrizes = useGenerateMonthlyPrizes();
  const approvePrize = useApprovePrize();
  const rejectPrize = useRejectPrize();
  const awardPrize = useAwardPrize();

  if (isLoading) return <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>;

  // Group by status
  const pending = prizes?.filter((p) => p.status === 'pending') || [];
  const approved = prizes?.filter((p) => p.status === 'approved') || [];
  const awarded = prizes?.filter((p) => p.status === 'awarded') || [];
  const rejected = prizes?.filter((p) => p.status === 'rejected') || [];

  if (!prizes?.length) {
    return (
      <FadeIn className="flex flex-col items-center gap-4 py-16">
        <EmptyState title="No prizes yet" description="Generate monthly prize recommendations based on performance" />
        {isOwner && (
          <Button variant="gold" onClick={() => generatePrizes.mutate(factoryId)} disabled={generatePrizes.isPending}>
            {generatePrizes.isPending ? 'Generating...' : 'Generate Monthly Prizes'}
          </Button>
        )}
      </FadeIn>
    );
  }

  return (
    <FadeIn className="space-y-6">
      {isOwner && (
        <Button variant="gold" size="sm" onClick={() => generatePrizes.mutate(factoryId)} disabled={generatePrizes.isPending}>
          {generatePrizes.isPending ? 'Generating...' : 'Generate Monthly Prizes'}
        </Button>
      )}

      {/* Pending approval */}
      {pending.length > 0 && (
        <PrizeSection
          title={`⏳ Pending Approval (${pending.length})`}
          prizes={pending}
          isOwner={!!isOwner}
          onApprove={(id) => approvePrize.mutate(id)}
          onReject={(id) => rejectPrize.mutate(id)}
        />
      )}

      {/* Approved, ready to award */}
      {approved.length > 0 && (
        <PrizeSection
          title={`✅ Approved (${approved.length})`}
          prizes={approved}
          isOwner={!!isOwner}
          onAward={(id) => awardPrize.mutate(id)}
        />
      )}

      {/* Already awarded */}
      {awarded.length > 0 && (
        <PrizeSection title={`🏆 Awarded (${awarded.length})`} prizes={awarded} />
      )}

      {/* Rejected */}
      {rejected.length > 0 && (
        <PrizeSection title={`❌ Rejected (${rejected.length})`} prizes={rejected} />
      )}
    </FadeIn>
  );
}

function PrizeSection({
  title,
  prizes,
  isOwner,
  onApprove,
  onReject,
  onAward,
}: {
  title: string;
  prizes: Prize[];
  isOwner?: boolean;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onAward?: (id: string) => void;
}) {
  return (
    <div>
      <h3 className="mb-3 text-sm font-bold text-gray-500 dark:text-stone-500">{title}</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {prizes.map((p, i) => {
          const cfg = PRIZE_STATUS_CONFIG[p.status] || { label: p.status, color: 'text-gray-500' };
          return (
            <ScaleIn key={p.id} delay={i * 0.04}>
              <Card className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-900 dark:text-stone-100">{p.user_name}</span>
                  <span className={cn('text-xs font-bold uppercase', cfg.color)}>{cfg.label}</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-stone-400">{p.description}</p>
                {p.amount_idr && (
                  <div className="text-sm font-bold text-amber-600 dark:text-amber-400">{formatIDR(p.amount_idr)}</div>
                )}
                {p.reason && <p className="text-xs text-gray-400 dark:text-stone-600">{p.reason}</p>}
                <div className="text-[10px] text-gray-400 dark:text-stone-600">{p.month}</div>

                {/* Actions */}
                {isOwner && (
                  <div className="flex gap-2 pt-1">
                    {onApprove && <Button size="sm" variant="gold" onClick={() => onApprove(p.id)}>Approve</Button>}
                    {onReject && <Button size="sm" variant="ghost" className="text-red-500" onClick={() => onReject(p.id)}>Reject</Button>}
                    {onAward && <Button size="sm" variant="primary" onClick={() => onAward(p.id)}>Award</Button>}
                  </div>
                )}
              </Card>
            </ScaleIn>
          );
        })}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
//  TAB: CEO Dashboard
// ══════════════════════════════════════════════════════════════════

function CeoDashTab({ factoryId }: { factoryId: string }) {
  const { data: dash, isLoading } = useCeoDashboard(factoryId);
  const { data: impact, isLoading: loadingImpact } = useProductivityImpact(factoryId);
  const { data: seasons } = useSeasons(factoryId);
  const sendReport = useSendCeoReport();

  if (isLoading) return <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>;
  if (!dash) return <EmptyState title="No data yet" description="Gamification data will appear here once employees start earning points" />;

  return (
    <FadeIn className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard icon="⭐" label="Points This Month" value={dash.total_points_this_month.toLocaleString()} />
        <KpiCard icon="👥" label="Active Users" value={dash.active_users} />
        <KpiCard icon="🏆" label="Active Competitions" value={dash.active_competitions} />
        <KpiCard icon="💪" label="Skills Certified" value={dash.skills_certified_this_month} />
      </div>

      {/* Engagement gauge */}
      <Card variant="glass">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-bold text-gray-900 dark:text-stone-100">Team Engagement</h3>
          <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400">{dash.engagement_rate}%</span>
        </div>
        <GradientBar value={dash.engagement_rate} max={100} />
      </Card>

      {/* Top performers */}
      {dash.top_performers?.length > 0 && (
        <Card>
          <h3 className="mb-3 text-sm font-bold text-gray-900 dark:text-stone-100">{'🌟'} Top Performers</h3>
          <div className="space-y-2">
            {dash.top_performers.map((p, i) => (
              <div key={p.user_id} className="flex items-center gap-3">
                <span className="text-lg">{RANK_DECORATIONS[i]?.emoji || `#${i + 1}`}</span>
                <span className="flex-1 font-medium text-gray-900 dark:text-stone-100">{p.user_name}</span>
                <span className="tabular-nums font-bold text-gray-900 dark:text-stone-100">{p.points}</span>
                <span className="text-[10px] text-gray-400 dark:text-stone-600">pts</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Productivity Impact */}
      {!loadingImpact && impact && (
        <Card>
          <h3 className="mb-3 text-sm font-bold text-gray-900 dark:text-stone-100">{'📈'} Productivity Impact</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <ImpactMetric
              label="Quality"
              before={impact.before_gamification.avg_quality}
              after={impact.after_gamification.avg_quality}
              improvement={impact.improvement_pct.quality}
            />
            <ImpactMetric
              label="Speed"
              before={impact.before_gamification.avg_speed}
              after={impact.after_gamification.avg_speed}
              improvement={impact.improvement_pct.speed}
            />
            <ImpactMetric
              label="Defect Reduction"
              before={impact.before_gamification.defect_rate}
              after={impact.after_gamification.defect_rate}
              improvement={impact.improvement_pct.defect_reduction}
            />
          </div>
          {impact.roi_estimate > 0 && (
            <div className="mt-4 rounded-lg bg-emerald-50 p-3 text-center dark:bg-emerald-500/10">
              <div className="text-xs text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Estimated ROI</div>
              <div className="text-2xl font-black text-emerald-700 dark:text-emerald-300">{impact.roi_estimate.toFixed(1)}x</div>
            </div>
          )}
        </Card>
      )}

      {/* Monthly Trend */}
      {dash.monthly_trend?.length > 0 && (
        <Card>
          <h3 className="mb-3 text-sm font-bold text-gray-900 dark:text-stone-100">{'📊'} Monthly Trend</h3>
          <div className="flex items-end gap-2 h-32">
            {dash.monthly_trend.map((m) => {
              const maxPts = Math.max(...dash.monthly_trend.map((t) => t.points), 1);
              const h = Math.max(8, (m.points / maxPts) * 100);
              return (
                <div key={m.month} className="flex flex-1 flex-col items-center gap-1">
                  <motion.div
                    className="w-full rounded-t bg-gradient-to-t from-violet-500 to-fuchsia-400 dark:from-gold-600 dark:to-amber-400"
                    initial={{ height: 0 }}
                    animate={{ height: `${h}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                  />
                  <span className="text-[10px] text-gray-400 dark:text-stone-600">{m.month}</span>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Seasons */}
      {seasons && seasons.length > 0 && (
        <Card>
          <h3 className="mb-3 text-sm font-bold text-gray-900 dark:text-stone-100">{'🌍'} Seasons</h3>
          <div className="space-y-2">
            {seasons.map((s) => (
              <div key={s.id} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 dark:bg-stone-800/50">
                <div>
                  <span className="font-medium text-gray-900 dark:text-stone-100">{s.name}</span>
                  <span className="ml-2 text-xs text-gray-500 dark:text-stone-500">
                    {new Date(s.start_date).toLocaleDateString()} &mdash; {new Date(s.end_date).toLocaleDateString()}
                  </span>
                </div>
                <span className={cn(
                  'rounded-full px-2 py-0.5 text-[10px] font-bold uppercase',
                  s.status === 'active' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400' : 'bg-gray-100 text-gray-500 dark:bg-stone-800 dark:text-stone-500',
                )}>
                  {s.status}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Send report button */}
      <div className="flex justify-end">
        <Button variant="secondary" size="sm" onClick={() => sendReport.mutate(factoryId)} disabled={sendReport.isPending}>
          {sendReport.isPending ? 'Sending...' : 'Send Weekly Report to Telegram'}
        </Button>
      </div>
    </FadeIn>
  );
}

function KpiCard({ icon, label, value }: { icon: string; label: string; value: string | number }) {
  return (
    <Card variant="glass" className="text-center">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-2xl font-black text-gray-900 dark:text-stone-100">{value}</div>
      <div className="text-xs text-gray-500 dark:text-stone-500 mt-0.5">{label}</div>
    </Card>
  );
}

function ImpactMetric({ label, before, after, improvement }: { label: string; before: number; after: number; improvement: number }) {
  const positive = improvement >= 0;
  return (
    <div>
      <div className="text-xs text-gray-500 dark:text-stone-500">{label}</div>
      <div className="text-xs text-gray-400 dark:text-stone-600">{before.toFixed(1)} &rarr; {after.toFixed(1)}</div>
      <div className={cn('text-lg font-black', positive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400')}>
        {positive ? '+' : ''}{improvement.toFixed(1)}%
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
//  MAIN PAGE
// ══════════════════════════════════════════════════════════════════

const PAGE_TABS = [
  { id: 'leaderboard', label: 'Leaderboard' },
  { id: 'skills', label: 'Skills' },
  { id: 'competitions', label: 'Competitions' },
  { id: 'prizes', label: 'Prizes' },
  { id: 'dashboard', label: 'CEO Dashboard' },
];

export default function GamificationPage() {
  const { factoryId } = useFactory();
  const user = useAuthStore((s) => s.user);
  const isOwner = user && ['owner', 'ceo'].includes(user.role);

  // Filter tabs based on role (CEO Dashboard only for owner/ceo)
  const tabs = useMemo(() => {
    if (isOwner) return PAGE_TABS;
    return PAGE_TABS.filter((t) => t.id !== 'dashboard');
  }, [isOwner]);

  const [activeTab, setActiveTab] = useState('leaderboard');

  if (!factoryId) {
    return (
      <div className="flex items-center justify-center py-16">
        <EmptyState title="Select a factory" description="Choose a factory from the header to view gamification data" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-black text-gray-900 dark:text-stone-100">
          Gamification
        </h1>
        <p className="text-sm text-gray-500 dark:text-stone-500 mt-1">
          Skills, competitions, leaderboards & rewards
        </p>
      </div>

      {/* Tabs */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.2 }}
        >
          {activeTab === 'leaderboard' && <LeaderboardTab factoryId={factoryId} />}
          {activeTab === 'skills' && <SkillsTab factoryId={factoryId} />}
          {activeTab === 'competitions' && <CompetitionsTab factoryId={factoryId} />}
          {activeTab === 'prizes' && <PrizesTab factoryId={factoryId} />}
          {activeTab === 'dashboard' && isOwner && <CeoDashTab factoryId={factoryId} />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
