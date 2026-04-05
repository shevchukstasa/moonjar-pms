import { useState, useMemo, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  workforceApi,
  type ShiftAssignment,
  type ShiftDefinition,
  type DailyCapacity,
  type WorkerSkill,
} from '@/api/workforce';
import { usersApi } from '@/api/users';
import { useFactories } from '@/hooks/useFactories';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { Tooltip } from '@/components/ui/Tooltip';
import { cn } from '@/lib/cn';

// ── Constants ──────────────────────────────────────────────

const PRODUCTION_STAGES = [
  { key: 'engobe', label: 'Engobe', icon: '🎨' },
  { key: 'glazing', label: 'Glazing', icon: '✨' },
  { key: 'drying', label: 'Drying', icon: '☀️' },
  { key: 'firing', label: 'Firing', icon: '🔥' },
  { key: 'sorting', label: 'Sorting', icon: '📦' },
  { key: 'packing', label: 'Packing', icon: '📋' },
  { key: 'edge_cleaning', label: 'Edge Cleaning', icon: '🧹' },
  { key: 'quality_check', label: 'Quality Check', icon: '🔍' },
];

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function pad(n: number) { return n < 10 ? `0${n}` : `${n}`; }
function toISO(y: number, m: number, d: number) { return `${y}-${pad(m)}-${pad(d)}`; }

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate();
}

function isWeekend(year: number, month: number, day: number) {
  const dow = new Date(year, month - 1, day).getDay();
  return dow === 0; // Sunday only (Indonesian factories work Sat)
}

function isToday(year: number, month: number, day: number) {
  const t = new Date();
  return t.getFullYear() === year && t.getMonth() + 1 === month && t.getDate() === day;
}

// ── Minimum workers per stage (configurable thresholds) ────
const MIN_WORKERS: Record<string, number> = {
  engobe: 2,
  glazing: 3,
  drying: 1,
  firing: 2,
  sorting: 2,
  packing: 2,
  edge_cleaning: 1,
  quality_check: 1,
};

function getCapacityColor(workers: number, stage: string): string {
  const min = MIN_WORKERS[stage] ?? 1;
  if (workers === 0) return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
  if (workers < min) return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
  return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
}

function getCapacityDot(workers: number, stage: string): string {
  const min = MIN_WORKERS[stage] ?? 1;
  if (workers === 0) return 'bg-red-400';
  if (workers < min) return 'bg-amber-400';
  return 'bg-emerald-400';
}

// ── Component ──────────────────────────────────────────────

export default function WorkforceAssignmentPage() {
  const queryClient = useQueryClient();
  const today = new Date();
  const user = useCurrentUser();

  // State
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [factoryId, setFactoryId] = useState<string>('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedCell, setSelectedCell] = useState<{ stage: string; date: string } | null>(null);
  const [assignUserId, setAssignUserId] = useState('');
  const [assignShiftId, setAssignShiftId] = useState('');
  const [assignIsLead, setAssignIsLead] = useState(false);
  const [formError, setFormError] = useState('');
  const [shiftDialogOpen, setShiftDialogOpen] = useState(false);
  const [newShiftName, setNewShiftName] = useState('');
  const [newShiftStart, setNewShiftStart] = useState('07:00');
  const [newShiftEnd, setNewShiftEnd] = useState('16:00');

  // Factories
  const { data: factoriesData, isLoading: factoriesLoading } = useFactories();
  const allFactories = factoriesData?.items ?? [];
  const GLOBAL_ROLES = new Set(['owner', 'administrator', 'ceo']);
  const isGlobal = user && GLOBAL_ROLES.has(user.role);
  const userFactoryIds = user?.factories?.map((f: { id?: string; factory_id?: string }) => f.id || f.factory_id) || [];
  const factories = isGlobal ? allFactories : allFactories.filter((f: { id: string }) => userFactoryIds.includes(f.id));

  useEffect(() => {
    if (!factoryId && factories.length > 0) {
      setFactoryId(factories[0].id);
    }
  }, [factories, factoryId]);

  // Days in month
  const daysInMonth = getDaysInMonth(year, month);
  const dayNumbers = useMemo(() => Array.from({ length: daysInMonth }, (_, i) => i + 1), [daysInMonth]);

  // Fetch daily capacity for all days in the month (batch individual queries)
  const dateStrings = useMemo(
    () => dayNumbers.map((d) => toISO(year, month, d)),
    [dayNumbers, year, month],
  );

  // We fetch capacity for each day — use a single query that fetches all days
  const capacityQueries = useQuery({
    queryKey: ['workforce-capacity-month', factoryId, year, month],
    queryFn: async () => {
      const results: Record<string, DailyCapacity> = {};
      // Fetch in parallel batches of 7 to avoid overwhelming the server
      for (let i = 0; i < dateStrings.length; i += 7) {
        const batch = dateStrings.slice(i, i + 7);
        const batchResults = await Promise.all(
          batch.map((date) =>
            workforceApi.getDailyCapacity(factoryId, date).catch(() => ({
              factory_id: factoryId,
              date,
              total_workers: 0,
              stages: {},
            })),
          ),
        );
        for (const r of batchResults) {
          results[r.date] = r;
        }
      }
      return results;
    },
    enabled: !!factoryId,
    staleTime: 30_000,
  });

  const capacityMap = capacityQueries.data ?? {};

  // Shifts
  const { data: shifts = [] } = useQuery({
    queryKey: ['workforce-shifts', factoryId],
    queryFn: () => workforceApi.listShifts(factoryId),
    enabled: !!factoryId,
    staleTime: 60_000,
  });
  const activeShifts = shifts.filter((s: ShiftDefinition) => s.is_active);

  // Auto-select first shift
  useEffect(() => {
    if (!assignShiftId && activeShifts.length > 0) {
      setAssignShiftId(activeShifts[0].id);
    }
  }, [activeShifts, assignShiftId]);

  // Workers (factory users)
  const { data: usersData } = useQuery({
    queryKey: ['workforce-users', factoryId],
    queryFn: () => usersApi.list({ factory_id: factoryId, is_active: true, per_page: 200 }),
    enabled: !!factoryId,
    staleTime: 60_000,
  });
  const workers = usersData?.items ?? [];
  const workerMap = useMemo(() => {
    const m = new Map<string, { id: string; name: string; role: string }>();
    for (const w of workers) m.set(w.id, w);
    return m;
  }, [workers]);

  // Skills for the factory
  const { data: skills = [] } = useQuery<WorkerSkill[]>({
    queryKey: ['workforce-skills', factoryId],
    queryFn: () => workforceApi.listSkills(factoryId),
    enabled: !!factoryId,
    staleTime: 60_000,
  });

  // Skills index: stage -> user_id[]
  const skillsByStage = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const s of skills) {
      if (!m.has(s.stage)) m.set(s.stage, new Set());
      m.get(s.stage)!.add(s.user_id);
    }
    return m;
  }, [skills]);

  // Assignments for the selected cell date
  const { data: cellAssignments = [] } = useQuery<ShiftAssignment[]>({
    queryKey: ['workforce-assignments', factoryId, selectedCell?.date],
    queryFn: () => workforceApi.listAssignments(factoryId, selectedCell!.date),
    enabled: !!factoryId && !!selectedCell?.date,
    staleTime: 10_000,
  });

  const cellStageAssignments = useMemo(
    () => cellAssignments.filter((a) => a.stage === selectedCell?.stage),
    [cellAssignments, selectedCell?.stage],
  );

  // ── Mutations ──────────────────────────────────────────────

  const assignMutation = useMutation({
    mutationFn: (data: { factory_id: string; user_id: string; shift_definition_id: string; date: string; stage: string; is_lead?: boolean }) =>
      workforceApi.createAssignment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workforce-capacity-month'] });
      queryClient.invalidateQueries({ queryKey: ['workforce-assignments'] });
      setAssignUserId('');
      setAssignIsLead(false);
      setFormError('');
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to create assignment');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => workforceApi.deleteAssignment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workforce-capacity-month'] });
      queryClient.invalidateQueries({ queryKey: ['workforce-assignments'] });
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to remove assignment');
    },
  });

  const createShiftMutation = useMutation({
    mutationFn: (data: { factory_id: string; name: string; start_time: string; end_time: string }) =>
      workforceApi.createShift(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workforce-shifts'] });
      setShiftDialogOpen(false);
      setNewShiftName('');
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to create shift');
    },
  });

  // ── Handlers ───────────────────────────────────────────────

  const openCellDialog = useCallback((stage: string, day: number) => {
    const date = toISO(year, month, day);
    setSelectedCell({ stage, date });
    setDialogOpen(true);
    setFormError('');
    setAssignUserId('');
    setAssignIsLead(false);
  }, [year, month]);

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setSelectedCell(null);
    setFormError('');
  }, []);

  const handleAssign = useCallback(() => {
    if (!assignUserId || !assignShiftId || !selectedCell) return;
    assignMutation.mutate({
      factory_id: factoryId,
      user_id: assignUserId,
      shift_definition_id: assignShiftId,
      date: selectedCell.date,
      stage: selectedCell.stage,
      is_lead: assignIsLead,
    });
  }, [assignUserId, assignShiftId, selectedCell, factoryId, assignIsLead, assignMutation]);

  const handleRemoveAssignment = useCallback((id: string) => {
    deleteMutation.mutate(id);
  }, [deleteMutation]);

  const handleCreateShift = useCallback(() => {
    if (!newShiftName) return;
    createShiftMutation.mutate({
      factory_id: factoryId,
      name: newShiftName,
      start_time: newShiftStart,
      end_time: newShiftEnd,
    });
  }, [newShiftName, newShiftStart, newShiftEnd, factoryId, createShiftMutation]);

  const navigateMonth = useCallback((delta: number) => {
    let m = month + delta;
    let y = year;
    if (m < 1) { m = 12; y -= 1; }
    if (m > 12) { m = 1; y += 1; }
    setMonth(m);
    setYear(y);
  }, [month, year]);

  // Skilled workers for the selected stage
  const skilledWorkerIds = selectedCell ? skillsByStage.get(selectedCell.stage) : undefined;
  const assignedUserIds = new Set(cellStageAssignments.map((a) => a.user_id));

  const availableWorkers = useMemo(() => {
    // Show skilled workers first, then all others
    const skilled: typeof workers = [];
    const others: typeof workers = [];
    for (const w of workers) {
      if (assignedUserIds.has(w.id)) continue; // already assigned
      if (skilledWorkerIds?.has(w.id)) {
        skilled.push(w);
      } else {
        others.push(w);
      }
    }
    return { skilled, others };
  }, [workers, assignedUserIds, skilledWorkerIds]);

  // ── Stage summary for header ───────────────────────────────

  const stageSummary = useMemo(() => {
    const summary: Record<string, { total: number; understaffed: number; empty: number }> = {};
    for (const stage of PRODUCTION_STAGES) {
      let total = 0, understaffed = 0, empty = 0;
      for (const day of dayNumbers) {
        const dateStr = toISO(year, month, day);
        const cap = capacityMap[dateStr];
        const count = cap?.stages?.[stage.key]?.workers ?? 0;
        total += count;
        const min = MIN_WORKERS[stage.key] ?? 1;
        if (count === 0 && !isWeekend(year, month, day)) empty++;
        else if (count < min && !isWeekend(year, month, day)) understaffed++;
      }
      summary[stage.key] = { total, understaffed, empty };
    }
    return summary;
  }, [capacityMap, dayNumbers, year, month]);

  // ── Loading state ──────────────────────────────────────────

  if (factoriesLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────

  const stageLabel = PRODUCTION_STAGES.find((s) => s.key === selectedCell?.stage);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-stone-100">
            Workforce Assignment
          </h1>
          <p className="text-sm text-gray-500 dark:text-stone-400">
            Assign workers to production stages for each shift
          </p>
        </div>
        <div className="flex items-center gap-2">
          {factories.length > 1 && (
            <Select
              value={factoryId}
              onChange={(e) => setFactoryId(e.target.value)}
              options={factories.map((f: { id: string; name: string }) => ({ value: f.id, label: f.name }))}
              className="w-44"
            />
          )}
          <Button variant="secondary" size="sm" onClick={() => setShiftDialogOpen(true)}>
            + Shift
          </Button>
        </div>
      </div>

      {/* Month navigation */}
      <Card className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => navigateMonth(-1)}>
          &larr; Prev
        </Button>
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-gray-900 dark:text-stone-100">
            {MONTH_NAMES[month - 1]} {year}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setYear(today.getFullYear()); setMonth(today.getMonth() + 1); }}
            className="text-xs"
          >
            Today
          </Button>
        </div>
        <Button variant="ghost" size="sm" onClick={() => navigateMonth(1)}>
          Next &rarr;
        </Button>
      </Card>

      {/* Shift legend */}
      {activeShifts.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-stone-400">
          <span className="font-medium">Shifts:</span>
          {activeShifts.map((s: ShiftDefinition) => (
            <span key={s.id} className="rounded-full bg-gray-100 px-2 py-0.5 dark:bg-stone-800">
              {s.name} ({s.start_time?.slice(0, 5)} - {s.end_time?.slice(0, 5)})
            </span>
          ))}
          <span className="ml-2 flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" /> Staffed
            <span className="ml-1 inline-block h-2.5 w-2.5 rounded-full bg-amber-400" /> Low
            <span className="ml-1 inline-block h-2.5 w-2.5 rounded-full bg-red-400" /> Empty
          </span>
        </div>
      )}

      {/* Calendar Grid */}
      <Card className="overflow-x-auto p-0">
        {capacityQueries.isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spinner className="h-8 w-8" />
          </div>
        ) : (
          <table className="w-full min-w-[900px] border-collapse text-xs">
            <thead>
              <tr className="border-b border-gray-200 dark:border-stone-700">
                <th className="sticky left-0 z-10 min-w-[140px] bg-white px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:bg-[var(--bg-card)] dark:text-stone-400">
                  Stage
                </th>
                {dayNumbers.map((d) => {
                  const dow = new Date(year, month - 1, d).getDay();
                  const dayName = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][dow];
                  const isSun = dow === 0;
                  const isTod = isToday(year, month, d);
                  return (
                    <th
                      key={d}
                      className={cn(
                        'min-w-[36px] px-0.5 py-2 text-center font-medium',
                        isSun && 'text-red-400',
                        isTod && 'bg-amber-50 dark:bg-amber-900/20',
                        !isSun && !isTod && 'text-gray-500 dark:text-stone-400',
                      )}
                    >
                      <div className="text-[10px] leading-tight">{dayName}</div>
                      <div className={cn('leading-tight', isTod && 'font-bold text-amber-600 dark:text-gold-400')}>
                        {d}
                      </div>
                    </th>
                  );
                })}
                <th className="min-w-[60px] px-2 py-2 text-center text-xs font-semibold text-gray-500 dark:text-stone-400">
                  Summary
                </th>
              </tr>
            </thead>
            <tbody>
              {PRODUCTION_STAGES.map((stage) => {
                const summary = stageSummary[stage.key];
                return (
                  <tr
                    key={stage.key}
                    className="border-b border-gray-100 transition-colors hover:bg-gray-50/50 dark:border-stone-800 dark:hover:bg-stone-800/30"
                  >
                    {/* Stage label */}
                    <td className="sticky left-0 z-10 bg-white px-3 py-1.5 dark:bg-[var(--bg-card)]">
                      <div className="flex items-center gap-1.5">
                        <span className="text-base leading-none">{stage.icon}</span>
                        <span className="font-medium text-gray-800 dark:text-stone-200">
                          {stage.label}
                        </span>
                      </div>
                      <div className="mt-0.5 text-[10px] text-gray-400 dark:text-stone-500">
                        min {MIN_WORKERS[stage.key] ?? 1} workers
                      </div>
                    </td>
                    {/* Day cells */}
                    {dayNumbers.map((d) => {
                      const dateStr = toISO(year, month, d);
                      const cap = capacityMap[dateStr];
                      const stageData = cap?.stages?.[stage.key];
                      const count = stageData?.workers ?? 0;
                      const leads = stageData?.leads ?? 0;
                      const isSun = isWeekend(year, month, d);
                      const isTod = isToday(year, month, d);
                      const userNames = (stageData?.user_ids ?? [])
                        .map((uid: string) => workerMap.get(uid)?.name ?? uid.slice(0, 6))
                        .join(', ');

                      return (
                        <td
                          key={d}
                          className={cn(
                            'relative px-0.5 py-1 text-center',
                            isTod && 'bg-amber-50/50 dark:bg-amber-900/10',
                            isSun && 'bg-gray-50 dark:bg-stone-900/50',
                          )}
                        >
                          <Tooltip text={count > 0 ? `${count} workers: ${userNames}${leads > 0 ? ` (${leads} lead)` : ''}` : 'No workers assigned'}>
                            <button
                              onClick={() => openCellDialog(stage.key, d)}
                              className={cn(
                                'mx-auto flex h-7 w-7 items-center justify-center rounded-md text-[11px] font-semibold transition-all',
                                'hover:scale-110 hover:shadow-md active:scale-95',
                                isSun
                                  ? 'bg-gray-100 text-gray-400 dark:bg-stone-800 dark:text-stone-500'
                                  : getCapacityColor(count, stage.key),
                              )}
                            >
                              {count > 0 ? count : ''}
                            </button>
                          </Tooltip>
                          {leads > 0 && (
                            <div className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-amber-500" title="Has lead" />
                          )}
                        </td>
                      );
                    })}
                    {/* Summary */}
                    <td className="px-2 py-1.5 text-center">
                      <div className="text-[11px] font-semibold text-gray-700 dark:text-stone-300">
                        {summary?.total ?? 0} total
                      </div>
                      {(summary?.empty ?? 0) > 0 && (
                        <div className="text-[10px] text-red-500">{summary.empty} empty</div>
                      )}
                      {(summary?.understaffed ?? 0) > 0 && (
                        <div className="text-[10px] text-amber-500">{summary.understaffed} low</div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      {/* Stats cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {PRODUCTION_STAGES.slice(0, 4).map((stage) => {
          const summary = stageSummary[stage.key];
          const total = summary?.total ?? 0;
          const workingDays = dayNumbers.filter((d) => !isWeekend(year, month, d)).length;
          const avg = workingDays > 0 ? (total / workingDays).toFixed(1) : '0';
          return (
            <Card key={stage.key} className="text-center">
              <div className="text-2xl">{stage.icon}</div>
              <div className="mt-1 text-sm font-semibold text-gray-800 dark:text-stone-200">
                {stage.label}
              </div>
              <div className="mt-1 text-lg font-bold text-gray-900 dark:text-stone-100">
                {avg}
              </div>
              <div className="text-[10px] text-gray-400 dark:text-stone-500">avg/day</div>
              <div className="mt-1 flex justify-center gap-1">
                {(summary?.empty ?? 0) > 0 && (
                  <span className="rounded-full bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-600 dark:bg-red-900/30 dark:text-red-400">
                    {summary!.empty} empty
                  </span>
                )}
                {(summary?.understaffed ?? 0) > 0 && (
                  <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-600 dark:bg-amber-900/30 dark:text-amber-400">
                    {summary!.understaffed} low
                  </span>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      {/* ── Assignment Dialog ──────────────────────────────────── */}
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        title={`${stageLabel?.icon ?? ''} ${stageLabel?.label ?? selectedCell?.stage ?? ''} — ${selectedCell?.date ?? ''}`}
        className="w-[480px] max-w-[95vw]"
      >
        <div className="space-y-4">
          {/* Current assignments */}
          <div>
            <h4 className="mb-2 text-sm font-medium text-gray-700 dark:text-stone-300">
              Current Assignments
            </h4>
            {cellStageAssignments.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-stone-500 italic">
                No workers assigned for this stage on this day
              </p>
            ) : (
              <div className="space-y-1.5">
                {cellStageAssignments.map((a) => {
                  const w = workerMap.get(a.user_id);
                  const shift = activeShifts.find((s: ShiftDefinition) => s.id === a.shift_definition_id);
                  return (
                    <div
                      key={a.id}
                      className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 dark:bg-stone-800"
                    >
                      <div className="flex items-center gap-2">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-amber-600 text-xs font-bold text-white">
                          {(w?.name ?? '?').charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <span className="text-sm font-medium text-gray-800 dark:text-stone-200">
                            {w?.name ?? a.user_id.slice(0, 8)}
                          </span>
                          {a.is_lead && (
                            <span className="ml-1.5 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
                              Lead
                            </span>
                          )}
                          <div className="text-[10px] text-gray-400 dark:text-stone-500">
                            {shift?.name ?? 'Unknown shift'} ({shift?.start_time?.slice(0, 5)} - {shift?.end_time?.slice(0, 5)})
                          </div>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 text-red-400 hover:text-red-600"
                        onClick={() => handleRemoveAssignment(a.id)}
                        disabled={deleteMutation.isPending}
                      >
                        &times;
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Add new assignment */}
          <div className="border-t border-gray-200 pt-3 dark:border-stone-700">
            <h4 className="mb-2 text-sm font-medium text-gray-700 dark:text-stone-300">
              Add Worker
            </h4>

            {activeShifts.length === 0 ? (
              <div className="rounded-lg bg-amber-50 p-3 text-xs text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
                No shift definitions found. Create a shift first.
                <Button variant="secondary" size="sm" className="ml-2" onClick={() => { closeDialog(); setShiftDialogOpen(true); }}>
                  + Create Shift
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {/* Shift selector */}
                <Select
                  label="Shift"
                  value={assignShiftId}
                  onChange={(e) => setAssignShiftId(e.target.value)}
                  options={activeShifts.map((s: ShiftDefinition) => ({
                    value: s.id,
                    label: `${s.name} (${s.start_time?.slice(0, 5)} - ${s.end_time?.slice(0, 5)})`,
                  }))}
                />

                {/* Worker selector */}
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">
                    Worker
                  </label>
                  <select
                    value={assignUserId}
                    onChange={(e) => setAssignUserId(e.target.value)}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100 dark:focus:border-gold-500"
                  >
                    <option value="">Select worker...</option>
                    {availableWorkers.skilled.length > 0 && (
                      <optgroup label="Skilled for this stage">
                        {availableWorkers.skilled.map((w: { id: string; name: string; role: string }) => (
                          <option key={w.id} value={w.id}>
                            {w.name} ({w.role})
                          </option>
                        ))}
                      </optgroup>
                    )}
                    {availableWorkers.others.length > 0 && (
                      <optgroup label="Other workers">
                        {availableWorkers.others.map((w: { id: string; name: string; role: string }) => (
                          <option key={w.id} value={w.id}>
                            {w.name} ({w.role})
                          </option>
                        ))}
                      </optgroup>
                    )}
                  </select>
                </div>

                {/* Lead toggle */}
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-stone-300">
                  <input
                    type="checkbox"
                    checked={assignIsLead}
                    onChange={(e) => setAssignIsLead(e.target.checked)}
                    className="rounded border-gray-300 text-amber-500 focus:ring-amber-500 dark:border-stone-600"
                  />
                  Assign as shift lead
                </label>

                {formError && (
                  <p className="text-xs text-red-500">{formError}</p>
                )}

                <Button
                  onClick={handleAssign}
                  disabled={!assignUserId || !assignShiftId || assignMutation.isPending}
                  size="sm"
                  className="w-full"
                >
                  {assignMutation.isPending ? 'Assigning...' : 'Assign Worker'}
                </Button>
              </div>
            )}
          </div>
        </div>
      </Dialog>

      {/* ── Shift Definition Dialog ───────────────────────────── */}
      <Dialog
        open={shiftDialogOpen}
        onClose={() => setShiftDialogOpen(false)}
        title="Create Shift Definition"
        className="w-[400px] max-w-[95vw]"
      >
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">
              Shift Name
            </label>
            <input
              type="text"
              value={newShiftName}
              onChange={(e) => setNewShiftName(e.target.value)}
              placeholder="e.g. Morning Shift"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">
                Start Time
              </label>
              <input
                type="time"
                value={newShiftStart}
                onChange={(e) => setNewShiftStart(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">
                End Time
              </label>
              <input
                type="time"
                value={newShiftEnd}
                onChange={(e) => setNewShiftEnd(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
              />
            </div>
          </div>
          {formError && <p className="text-xs text-red-500">{formError}</p>}
          <Button
            onClick={handleCreateShift}
            disabled={!newShiftName || createShiftMutation.isPending}
            size="sm"
            className="w-full"
          >
            {createShiftMutation.isPending ? 'Creating...' : 'Create Shift'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
