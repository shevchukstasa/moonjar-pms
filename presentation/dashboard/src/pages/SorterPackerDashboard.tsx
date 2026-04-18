import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { Spinner } from '@/components/ui/Spinner';
import { useUiStore } from '@/stores/uiStore';
import {
  usePositions,
  useChangePositionStatus,
  useSplitPosition,
  useStockAvailability,
  type PositionItem,
} from '@/hooks/usePositions';
import { useSorterTasks, useCompleteTask } from '@/hooks/useTasks';
import type { TaskItem } from '@/api/tasks';
import { usePackingPhotos, useUploadPackingPhoto } from '@/hooks/usePackingPhotos';

/* ============================================================
   TYPES & CONSTS
   ============================================================ */

type View = 'home' | 'sort' | 'pack' | 'grind' | 'tasks';

const COLOR_DOT: Record<string, string> = {};
function colorHash(color: string): string {
  if (COLOR_DOT[color]) return COLOR_DOT[color];
  const palette = [
    '#f97316', '#ef4444', '#eab308', '#22c55e', '#14b8a6',
    '#0ea5e9', '#6366f1', '#a855f7', '#ec4899', '#78716c',
  ];
  let h = 0;
  for (let i = 0; i < color.length; i++) h = (h * 31 + color.charCodeAt(i)) >>> 0;
  return (COLOR_DOT[color] = palette[h % palette.length]);
}

function isStockCollection(collection: string | null | undefined): boolean {
  if (!collection) return false;
  const n = collection.trim().toLowerCase();
  return n === 'сток' || n === 'stock';
}

/* ============================================================
   TODAY COUNTER (localStorage — light dopamine)
   ============================================================ */

function useTodayCounter() {
  const key = useMemo(() => `sorter_today_${new Date().toISOString().slice(0, 10)}`, []);
  const [count, setCount] = useState(() => {
    if (typeof window === 'undefined') return 0;
    return parseInt(localStorage.getItem(key) || '0', 10) || 0;
  });
  const bump = (delta = 1) => {
    setCount((c) => {
      const next = c + delta;
      try { localStorage.setItem(key, String(next)); } catch { /* noop */ }
      return next;
    });
  };
  return { count, bump };
}

function useDailyGoal() {
  const [goal, setGoal] = useState<number>(() => {
    if (typeof window === 'undefined') return 50;
    return parseInt(localStorage.getItem('sorter_daily_goal') || '50', 10) || 50;
  });
  const save = (g: number) => {
    const v = Math.max(10, Math.min(500, g));
    setGoal(v);
    try { localStorage.setItem('sorter_daily_goal', String(v)); } catch { /* noop */ }
  };
  return { goal, setGoal: save };
}

/* ============================================================
   DAILY GOAL RING
   ============================================================ */

function GoalRing({ done, goal, onEdit }: { done: number; goal: number; onEdit: () => void }) {
  const pct = Math.min(1, done / Math.max(1, goal));
  const size = 120;
  const stroke = 10;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - pct * circ;
  const met = done >= goal;
  return (
    <motion.button
      whileTap={{ scale: 0.96 }}
      onClick={onEdit}
      className="relative inline-flex flex-shrink-0 items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f1f5f9" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={met ? '#10b981' : '#f59e0b'}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={false}
          animate={{ strokeDashoffset: offset }}
          transition={{ type: 'spring', stiffness: 120, damping: 20 }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-3xl font-extrabold leading-none text-gray-900">{done}</div>
        <div className="text-[10px] uppercase tracking-wide text-gray-400">dari {goal}</div>
        {met && <div className="mt-0.5 text-base">🎉</div>}
      </div>
    </motion.button>
  );
}

/* ============================================================
   CONFETTI
   ============================================================ */

function Confetti({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <div className="fixed inset-0 pointer-events-none z-[100] overflow-hidden">
      {Array.from({ length: 50 }).map((_, i) => (
        <div
          key={i}
          className="absolute w-2.5 h-2.5 rounded-full animate-confetti"
          style={{
            left: `${Math.random() * 100}%`,
            backgroundColor: ['#f59e0b', '#10b981', '#6366f1', '#f97316', '#ec4899', '#eab308'][i % 6],
            animationDelay: `${Math.random() * 0.4}s`,
            animationDuration: `${1.4 + Math.random() * 1.2}s`,
          }}
        />
      ))}
    </div>
  );
}

/* ============================================================
   MAIN
   ============================================================ */

export default function SorterPackerDashboard() {
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);
  const [view, setView] = useState<View>('home');
  const [confetti, setConfetti] = useState(false);
  const [editGoal, setEditGoal] = useState(false);
  const { count: today, bump } = useTodayCounter();
  const { goal, setGoal } = useDailyGoal();

  const sortingQ = usePositions(
    activeFactoryId
      ? { factory_id: activeFactoryId, status: 'transferred_to_sorting' }
      : { status: 'transferred_to_sorting' },
  );
  const packedQ = usePositions(
    activeFactoryId
      ? { factory_id: activeFactoryId, status: 'packed' }
      : { status: 'packed' },
  );
  const grindingQ = usePositions(
    activeFactoryId
      ? { factory_id: activeFactoryId, status: 'grinding' }
      : { status: 'grinding' },
  );
  const tasksQ = useSorterTasks(activeFactoryId || undefined);

  const sortingCount = sortingQ.data?.items.length || 0;
  const packedCount = packedQ.data?.items.length || 0;
  const grindingCount = grindingQ.data?.items.length || 0;
  const tasksCount = tasksQ.data?.items.length || 0;

  const celebrate = () => {
    setConfetti(true);
    setTimeout(() => setConfetti(false), 1800);
  };

  const fireConfetti = celebrate;

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50/40 via-white to-white pb-safe">
      <Confetti show={confetti} />

      <AnimatePresence mode="wait">
        {view === 'home' && (
          <motion.div
            key="home"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <HomeView
              today={today}
              goal={goal}
              onEditGoal={() => setEditGoal(true)}
              counts={{
                sorting: sortingCount,
                packed: packedCount,
                grinding: grindingCount,
                tasks: tasksCount,
              }}
              onNavigate={setView}
            />
          </motion.div>
        )}

        {view === 'sort' && (
          <motion.div key="sort" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.2 }}>
            <SortView
              positions={sortingQ.data?.items || []}
              isLoading={sortingQ.isLoading}
              onBack={() => setView('home')}
              onSuccess={(n, defectPct) => { bump(n); if (defectTier(defectPct).confetti) fireConfetti(); }}
            />
          </motion.div>
        )}

        {view === 'pack' && (
          <motion.div key="pack" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.2 }}>
            <PackView
              positions={packedQ.data?.items || []}
              isLoading={packedQ.isLoading}
              onBack={() => setView('home')}
              onSuccess={() => bump()}
            />
          </motion.div>
        )}

        {view === 'grind' && (
          <motion.div key="grind" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.2 }}>
            <GrindView
              positions={grindingQ.data?.items || []}
              isLoading={grindingQ.isLoading}
              onBack={() => setView('home')}
            />
          </motion.div>
        )}

        {view === 'tasks' && (
          <motion.div key="tasks" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.2 }}>
            <TasksView
              tasks={tasksQ.data?.items || []}
              isLoading={tasksQ.isLoading}
              onBack={() => setView('home')}
              onSuccess={() => bump()}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {editGoal && (
          <GoalEditor current={goal} onClose={() => setEditGoal(false)} onSave={(v) => { setGoal(v); setEditGoal(false); toast.success(`🎯 Target harian: ${v} pcs`); }} />
        )}
      </AnimatePresence>
    </div>
  );
}

function GoalEditor({ current, onClose, onSave }: { current: number; onClose: () => void; onSave: (v: number) => void }) {
  const [v, setV] = useState(current);
  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm sm:items-center"
    >
      <motion.div
        initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 40, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-t-3xl bg-white p-6 shadow-2xl sm:rounded-3xl"
      >
        <div className="text-center">
          <div className="text-4xl">🎯</div>
          <h3 className="mt-2 text-lg font-bold text-gray-900">Target harian</h3>
          <p className="text-xs text-gray-500">Berapa plitka ingin kamu sortir hari ini?</p>
        </div>
        <div className="mt-5 flex items-center justify-center gap-3">
          <motion.button whileTap={{ scale: 0.9 }} onClick={() => setV((x) => Math.max(10, x - 10))}
            className="h-14 w-14 rounded-2xl bg-gray-100 text-2xl font-bold text-gray-700">−</motion.button>
          <div className="w-28 text-center text-5xl font-extrabold text-gray-900">{v}</div>
          <motion.button whileTap={{ scale: 0.9 }} onClick={() => setV((x) => Math.min(500, x + 10))}
            className="h-14 w-14 rounded-2xl bg-gray-100 text-2xl font-bold text-gray-700">+</motion.button>
        </div>
        <div className="mt-6 flex gap-2">
          <button onClick={onClose} className="flex-1 rounded-2xl bg-gray-100 py-3 text-sm font-semibold text-gray-700">Batal</button>
          <motion.button whileTap={{ scale: 0.97 }} onClick={() => onSave(v)}
            className="flex-[2] rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 py-3 text-sm font-bold text-white shadow-lg">
            Simpan
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  );
}

/* ============================================================
   HOME
   ============================================================ */

function HomeView({
  today,
  goal,
  onEditGoal,
  counts,
  onNavigate,
}: {
  today: number;
  goal: number;
  onEditGoal: () => void;
  counts: { sorting: number; packed: number; grinding: number; tasks: number };
  onNavigate: (v: View) => void;
}) {
  const hour = new Date().getHours();
  const greet = hour < 5 ? 'Selamat malam' : hour < 12 ? 'Selamat pagi' : hour < 17 ? 'Selamat siang' : hour < 22 ? 'Selamat sore' : 'Selamat malam';
  const emoji = hour < 12 ? '🌅' : hour < 17 ? '☀️' : '🌙';
  const pct = Math.min(100, Math.round((today / Math.max(1, goal)) * 100));

  return (
    <div className="mx-auto max-w-xl px-4 pt-6 pb-10 md:pt-10">
      {/* Hero: greeting + daily goal ring */}
      <div className="rounded-3xl bg-gradient-to-br from-amber-50 via-white to-orange-50/70 p-5 shadow-sm">
        <div className="flex items-center gap-4">
          <GoalRing done={today} goal={goal} onEdit={onEditGoal} />
          <div className="min-w-0 flex-1">
            <p className="text-xs text-gray-500">{greet} {emoji}</p>
            <h1 className="mt-0.5 text-xl font-bold text-gray-900">Sortir &amp; Pak</h1>
            <p className="mt-2 text-xs text-gray-500">
              {today >= goal ? (
                <>Target tercapai! 🎉 <span className="font-semibold text-emerald-600">+{today - goal} ekstra</span></>
              ) : (
                <>Sisa <span className="font-semibold text-orange-600">{goal - today} plitka</span> lagi buat target</>
              )}
            </p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/80">
              <motion.div
                initial={false}
                animate={{ width: `${pct}%` }}
                transition={{ type: 'spring', stiffness: 120, damping: 22 }}
                className={`h-full ${today >= goal ? 'bg-gradient-to-r from-emerald-400 to-teal-500' : 'bg-gradient-to-r from-amber-400 to-orange-500'}`}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Action tiles */}
      <div className="mt-4 grid grid-cols-2 gap-3">
        <ActionTile
          emoji="🎨"
          label="Sortir"
          sub="dari kiln"
          count={counts.sorting}
          gradient="from-orange-400 to-rose-500"
          onClick={() => onNavigate('sort')}
          big
        />
        <ActionTile
          emoji="📦"
          label="Pak → QC"
          sub="siap dikirim"
          count={counts.packed}
          gradient="from-emerald-400 to-teal-500"
          onClick={() => onNavigate('pack')}
          big
        />
        <ActionTile
          emoji="⚙️"
          label="Gerinda"
          sub="tentukan rute"
          count={counts.grinding}
          gradient="from-slate-400 to-slate-600"
          onClick={() => onNavigate('grind')}
        />
        <ActionTile
          emoji="✅"
          label="Tugas"
          sub="untuk saya"
          count={counts.tasks}
          gradient="from-indigo-400 to-violet-500"
          onClick={() => onNavigate('tasks')}
          wide
        />
      </div>

      <p className="mt-6 text-center text-xs text-gray-400">
        Tap kartu untuk mulai. Tiap plitka dihitung 🔥
      </p>
    </div>
  );
}

function ActionTile({
  emoji, label, sub, count, gradient, onClick, big, wide,
}: {
  emoji: string;
  label: string;
  sub: string;
  count: number | null;
  gradient: string;
  onClick: () => void;
  big?: boolean;
  wide?: boolean;
}) {
  return (
    <motion.button
      whileTap={{ scale: 0.96 }}
      whileHover={{ y: -2 }}
      transition={{ type: 'spring', stiffness: 400, damping: 22 }}
      onClick={onClick}
      className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${gradient} p-4 text-left text-white shadow-lg ${wide ? 'col-span-2' : ''} ${big ? 'min-h-[140px]' : 'min-h-[110px]'}`}
    >
      <div className="flex items-start justify-between">
        <span className={`${big ? 'text-4xl' : 'text-3xl'}`}>{emoji}</span>
        {count !== null && count > 0 && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="rounded-full bg-white/25 backdrop-blur-sm px-2.5 py-1 text-sm font-bold"
          >
            {count}
          </motion.span>
        )}
      </div>
      <div className="mt-auto pt-3">
        <div className={`${big ? 'text-xl' : 'text-lg'} font-bold`}>{label}</div>
        <div className="text-xs text-white/80">{sub}</div>
      </div>
      {/* subtle shine */}
      <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-white/10" />
    </motion.button>
  );
}

/* ============================================================
   BACK BAR
   ============================================================ */

function BackBar({ title, onBack, subtitle }: { title: string; onBack: () => void; subtitle?: string }) {
  return (
    <div className="sticky top-0 z-20 border-b border-gray-100 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-xl items-center gap-3 px-4 py-3">
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={onBack}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 text-gray-700 hover:bg-gray-200"
          aria-label="Back"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6" /></svg>
        </motion.button>
        <div className="min-w-0">
          <h2 className="truncate text-base font-bold text-gray-900">{title}</h2>
          {subtitle && <p className="truncate text-xs text-gray-500">{subtitle}</p>}
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   SORT VIEW
   ============================================================ */

function SortView({
  positions, isLoading, onBack, onSuccess,
}: {
  positions: PositionItem[];
  isLoading: boolean;
  onBack: () => void;
  onSuccess: (goodCount: number, rate: number) => void;
}) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const active = positions.find((p) => p.id === activeId) || null;

  if (active) {
    return (
      <>
        <BackBar title={active.order_number} subtitle={`${active.color} · ${active.size}`} onBack={() => setActiveId(null)} />
        <div className="mx-auto max-w-6xl px-4 py-4">
          <SplitWizard
            position={active}
            onDone={(n, rate) => {
              setActiveId(null);
              onSuccess(n, rate);
            }}
          />
        </div>
      </>
    );
  }

  return (
    <>
      <BackBar title="Sortir dari kiln" onBack={onBack} subtitle={`${positions.length} menunggu`} />
      <div className="mx-auto max-w-xl px-4 py-4">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
        ) : positions.length === 0 ? (
          <EmptyTile emoji="🎉" title="Beres semua!" sub="Tidak ada yang perlu disortir." />
        ) : (
          <div className="grid gap-3">
            {positions.map((p) => (
              <PositionCard key={p.id} p={p} onClick={() => setActiveId(p.id)} accent="from-orange-50 to-amber-50" />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function PositionCard({
  p, onClick, accent, right,
}: {
  p: PositionItem;
  onClick?: () => void;
  accent?: string;
  right?: React.ReactNode;
}) {
  const dot = colorHash(p.color);
  const stock = isStockCollection(p.collection);
  return (
    <motion.button
      whileTap={onClick ? { scale: 0.98 } : undefined}
      onClick={onClick}
      disabled={!onClick}
      className={`group flex items-center gap-4 rounded-2xl border border-gray-100 bg-gradient-to-br ${accent || 'from-white to-white'} p-4 text-left shadow-sm transition-all hover:shadow-md ${!onClick ? 'cursor-default' : ''}`}
    >
      {/* Color dot */}
      <div className="flex-shrink-0">
        <div
          className="h-14 w-14 rounded-2xl shadow-inner ring-2 ring-white"
          style={{ backgroundColor: dot }}
          aria-hidden
        />
      </div>
      {/* Info */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-bold text-gray-900">{p.order_number}</span>
          {stock && (
            <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-700">STOCK</span>
          )}
        </div>
        <p className="truncate text-xs text-gray-500">{p.color} · {p.size}</p>
        <p className="mt-1 text-2xl font-extrabold leading-none text-gray-900">
          {p.quantity}<span className="ml-1 text-sm font-medium text-gray-400">pcs</span>
        </p>
      </div>
      {right ? right : onClick ? (
        <div className="flex-shrink-0 text-gray-300 transition-transform group-hover:translate-x-0.5">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6" /></svg>
        </div>
      ) : null}
    </motion.button>
  );
}

function EmptyTile({ emoji, title, sub }: { emoji: string; title: string; sub: string }) {
  return (
    <div className="rounded-3xl bg-gradient-to-br from-gray-50 to-white p-10 text-center shadow-inner">
      <div className="mx-auto mb-3 text-5xl">{emoji}</div>
      <p className="text-lg font-bold text-gray-700">{title}</p>
      <p className="mt-1 text-sm text-gray-400">{sub}</p>
    </div>
  );
}

/* ============================================================
   SPLIT WIZARD
   ============================================================ */

type DefectKey = 'refire' | 'repair' | 'color_mismatch' | 'grinding' | 'write_off';
interface Defect {
  key: DefectKey;
  label: string;
  emoji: string;
  color: string;
  desc: string;
}
interface DefectTier { emoji: string; label: string; msg: string; color: string; confetti: boolean; }
function defectTier(pct: number): DefectTier {
  if (pct <= 3) return { emoji: '🏆', label: 'Juara!', msg: 'Kerja hebat! +poin bonus', color: 'from-emerald-500 to-teal-600', confetti: true };
  if (pct <= 5) return { emoji: '✨', label: 'Bagus', msg: 'Hasil bagus. +poin', color: 'from-green-500 to-emerald-600', confetti: true };
  if (pct <= 7) return { emoji: '😐', label: 'So-so', msg: 'Lumayan. Bisa lebih baik', color: 'from-amber-400 to-orange-500', confetti: false };
  if (pct <= 10) return { emoji: '⚠️', label: 'Hati-hati', msg: 'Cacat tinggi — periksa prosesnya', color: 'from-orange-500 to-rose-500', confetti: false };
  return { emoji: '💀', label: 'Gawat', msg: 'Cacat sangat tinggi. Lapor PM.', color: 'from-red-600 to-rose-700', confetti: false };
}

const DEFECTS: Defect[] = [
  { key: 'refire', label: 'Bakar ulang', emoji: '🔥', color: 'from-amber-400 to-orange-500', desc: 'Perlu bakar lagi' },
  { key: 'repair', label: 'Perbaikan', emoji: '🔧', color: 'from-yellow-400 to-amber-500', desc: 'Glaze ulang & bakar' },
  { key: 'color_mismatch', label: 'Warna salah', emoji: '🎨', color: 'from-rose-400 to-pink-500', desc: 'Warna tidak cocok' },
  { key: 'grinding', label: 'Gerinda', emoji: '⚙️', color: 'from-slate-400 to-slate-600', desc: 'Perlu digerinda' },
  { key: 'write_off', label: 'Rusak', emoji: '💥', color: 'from-red-500 to-rose-600', desc: 'Buang / write off' },
];

const GOOD_CAT: Defect = { key: 'good' as DefectKey, label: 'Bagus', emoji: '✓', color: 'from-emerald-400 to-teal-500', desc: 'Plitka bagus' };

type SubmitMode = 'ok' | 'partial' | 'surplus' | 'block_overflow';

function SplitWizard({ position, onDone }: { position: PositionItem; onDone: (goodCount: number, defectPct: number) => void }) {
  const splitMutation = useSplitPosition();
  const [good, setGood] = useState<number>(0);
  const [defects, setDefects] = useState<Partial<Record<DefectKey, number>>>({});
  const [notes, setNotes] = useState('');
  const [showNotes, setShowNotes] = useState(false);
  const [confirm, setConfirm] = useState<null | SubmitMode>(null);

  const defectSum = Object.values(defects).reduce((a, b) => a + (b || 0), 0);
  const total = good + defectSum;
  const qty = position.quantity;
  const diff = total - qty;
  const overflowPct = qty > 0 ? (diff / qty) * 100 : 0;

  let mode: SubmitMode;
  if (total === qty) mode = 'ok';
  else if (total < qty) mode = 'partial';
  else if (overflowPct <= 10) mode = 'surplus';
  else mode = 'block_overflow';

  const defectPct = qty > 0 ? Math.round((defectSum / qty) * 100) : 0;
  const tier = defectTier(defectPct);

  const setDefect = (k: DefectKey, v: number) => {
    setDefects((d) => {
      const next = { ...d };
      if (v <= 0) delete next[k];
      else next[k] = v;
      return next;
    });
  };

  const doSubmit = async () => {
    const payload = {
      good_quantity: good,
      refire_quantity: defects.refire || 0,
      repair_quantity: defects.repair || 0,
      color_mismatch_quantity: defects.color_mismatch || 0,
      grinding_quantity: defects.grinding || 0,
      write_off_quantity: defects.write_off || 0,
      notes: notes || undefined,
    };
    try {
      await splitMutation.mutateAsync({ id: position.id, data: payload });
      toast.success(`${tier.emoji} ${good} bagus dari ${qty} · ${defectPct}% cacat`, {
        description: tier.msg,
      });
      onDone(good, defectPct);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || (err as { message?: string })?.message
        || 'Gagal simpan';
      toast.error(msg);
    }
  };

  const attemptSubmit = () => {
    if (mode === 'block_overflow') return;
    if (mode === 'ok') { void doSubmit(); return; }
    setConfirm(mode);
  };

  return (
    <div className="space-y-4">
      {/* Position hero */}
      <div className="rounded-3xl bg-gradient-to-br from-white to-amber-50/40 p-5 shadow-sm">
        <div className="flex items-center gap-4">
          <div
            className="h-20 w-20 flex-shrink-0 rounded-3xl shadow-inner ring-2 ring-white"
            style={{ backgroundColor: colorHash(position.color) }}
          />
          <div className="min-w-0 flex-1">
            <p className="text-xs uppercase tracking-wide text-gray-400">Dari kiln</p>
            <p className="truncate text-base font-bold text-gray-900">{position.color}</p>
            <p className="truncate text-xs text-gray-500">{position.size}</p>
            <p className="mt-1 text-4xl font-extrabold leading-none text-gray-900">
              {position.quantity}<span className="ml-1.5 text-sm font-medium text-gray-400">pcs</span>
            </p>
          </div>
        </div>
        {isStockCollection(position.collection) && <StockPanel positionId={position.id} />}
      </div>

      {/* Category grid — good + 5 defects */}
      <div className="rounded-3xl border border-gray-100 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-semibold text-gray-900">
            Hitung tiap kategori:
          </p>
          {(good > 0 || defectSum > 0) && (
            <button
              onClick={() => { setGood(0); setDefects({}); }}
              className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200"
            >
              Reset
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <DefectCell defect={GOOD_CAT} value={good} onChange={setGood} />
          {DEFECTS.map((d) => (
            <DefectCell
              key={d.key}
              defect={d}
              value={defects[d.key] || 0}
              onChange={(v) => setDefect(d.key, v)}
            />
          ))}
        </div>
      </div>

      {/* Running total — validation state */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl bg-gradient-to-br from-white to-emerald-50/30 p-5 shadow-sm"
      >
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-wide text-gray-400">Total dihitung</p>
            <p className={`mt-1 text-5xl font-extrabold leading-none ${
              mode === 'block_overflow' ? 'text-red-600'
              : mode === 'surplus' ? 'text-orange-600'
              : mode === 'partial' ? 'text-amber-600'
              : 'text-emerald-600'
            }`}>
              {total}
            </p>
            <p className="mt-1 text-xs text-gray-400">di kiln: {qty}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-gray-400">Bagus</p>
            <p className="mt-1 text-5xl font-extrabold leading-none text-emerald-600">{good}</p>
            <p className="mt-1 text-xs text-gray-400">plitka OK</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wide text-gray-400">Cacat</p>
            <p className="mt-1 text-5xl font-extrabold leading-none text-amber-600">{defectSum}</p>
            <p className="mt-1 flex items-center justify-end gap-1 text-xs">
              <span className="text-base">{tier.emoji}</span>
              <span className="text-gray-500">{defectPct}% · {tier.label}</span>
            </p>
          </div>
        </div>

        {/* Status banner */}
        <StatusBanner mode={mode} total={total} qty={qty} diff={diff} overflowPct={overflowPct} />

        {/* Notes toggle */}
        <button
          onClick={() => setShowNotes((v) => !v)}
          className="mt-3 text-xs text-gray-500 hover:text-gray-700"
        >
          {showNotes ? 'Sembunyikan' : 'Tambah'} catatan (opsional)
        </button>
        {showNotes && (
          <textarea
            placeholder="mis. nempel di shelf kiln"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="mt-2 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-orange-400 focus:outline-none"
          />
        )}

        {/* Submit — big green dopamine button */}
        <motion.button
          whileTap={{ scale: mode === 'block_overflow' ? 1 : 0.97 }}
          whileHover={mode === 'block_overflow' ? undefined : { y: -1 }}
          onClick={attemptSubmit}
          disabled={mode === 'block_overflow' || total === 0 || splitMutation.isPending}
          className={`relative mt-4 w-full overflow-hidden rounded-2xl bg-gradient-to-br ${
            mode === 'block_overflow' ? 'from-red-500 to-rose-600'
            : mode === 'surplus' ? 'from-orange-500 to-amber-600'
            : mode === 'partial' ? 'from-amber-500 to-orange-500'
            : tier.color
          } px-4 py-5 text-white shadow-xl disabled:cursor-not-allowed disabled:opacity-50`}
        >
          <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-white/10" />
          <div className="relative flex items-center justify-center gap-3">
            <span className="text-2xl">
              {mode === 'block_overflow' ? '🚫' : mode === 'surplus' ? '➕' : mode === 'partial' ? '⏸️' : tier.emoji}
            </span>
            <div className="text-left">
              <div className="text-lg font-extrabold">
                {splitMutation.isPending ? 'Menyimpan…'
                  : mode === 'block_overflow' ? 'Angka tidak valid'
                  : mode === 'surplus' ? 'Simpan surplus…'
                  : mode === 'partial' ? 'Simpan sebagian…'
                  : 'Selesai & Simpan'}
              </div>
              <div className="text-xs text-white/90">
                {total} dihitung · {qty} di kiln · {defectPct}% cacat
              </div>
            </div>
          </div>
        </motion.button>
      </motion.div>

      {/* Confirm dialogs for partial / surplus */}
      <AnimatePresence>
        {confirm && (
          <ConfirmSubmitDialog
            mode={confirm}
            total={total}
            qty={qty}
            diff={diff}
            overflowPct={overflowPct}
            onClose={() => setConfirm(null)}
            onConfirm={() => { setConfirm(null); void doSubmit(); }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function StatusBanner({ mode, total, qty, diff, overflowPct }: { mode: SubmitMode; total: number; qty: number; diff: number; overflowPct: number }) {
  if (mode === 'ok' || total === 0) return null;
  if (mode === 'partial') {
    return (
      <div className="mt-3 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs">
        <span className="text-base">⏸️</span>
        <div className="text-amber-900">
          <div className="font-semibold">Kurang {qty - total} plitka dari kiln</div>
          <div className="text-amber-700">Kalau simpan sekarang, sisanya akan tetap ada di sortir — kamu bisa lanjut besok.</div>
        </div>
      </div>
    );
  }
  if (mode === 'surplus') {
    return (
      <div className="mt-3 flex items-start gap-2 rounded-xl border border-orange-200 bg-orange-50 p-3 text-xs">
        <span className="text-base">➕</span>
        <div className="text-orange-900">
          <div className="font-semibold">Lebih {diff} plitka dari yang ada di kiln ({Math.round(overflowPct)}%)</div>
          <div className="text-orange-700">Surplus produksi sampai 10% OK — konfirmasi jumlah fisik benar.</div>
        </div>
      </div>
    );
  }
  // block_overflow
  return (
    <div className="mt-3 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-xs">
      <span className="text-base">🚫</span>
      <div className="text-red-900">
        <div className="font-semibold">Terlalu banyak: {total} dihitung, kiln cuma {qty} ({Math.round(overflowPct)}% lebih)</div>
        <div className="text-red-700">Maks 10% dari {qty} = {Math.floor(qty * 1.10)}. Periksa angkanya — kemungkinan salah ketik atau hitung ulang plitka fisik.</div>
      </div>
    </div>
  );
}

function ConfirmSubmitDialog({
  mode, total, qty, diff, overflowPct, onClose, onConfirm,
}: {
  mode: SubmitMode;
  total: number;
  qty: number;
  diff: number;
  overflowPct: number;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const isPartial = mode === 'partial';
  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm sm:items-center"
    >
      <motion.div
        initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 40, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-t-3xl bg-white p-6 shadow-2xl sm:rounded-3xl"
      >
        <div className="text-center">
          <div className="text-5xl">{isPartial ? '⏸️' : '➕'}</div>
          <h3 className="mt-3 text-lg font-bold text-gray-900">
            {isPartial ? 'Kurang dari kiln' : 'Lebih dari kiln'}
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            {isPartial
              ? `Kamu hitung ${total} plitka, tapi di kiln ${qty}.`
              : `Kamu hitung ${total} plitka, di kiln ${qty} — lebih ${diff} (${Math.round(overflowPct)}%).`}
          </p>
        </div>

        <div className={`mt-4 rounded-2xl p-4 text-sm ${isPartial ? 'bg-amber-50 text-amber-900' : 'bg-orange-50 text-orange-900'}`}>
          {isPartial ? (
            <>
              <p><strong>Kalau lanjut:</strong> posisi di-split. {total} plitka masuk sortir sekarang, sisa {qty - total} tetap menunggu.</p>
              <p className="mt-2">Kamu bisa selesaikan sisanya nanti / besok.</p>
            </>
          ) : (
            <>
              <p><strong>Surplus produksi sampai 10% valid</strong> — kiln kadang menghasilkan plitka lebih banyak dari yang dimuat.</p>
              <p className="mt-2">Pastikan kamu sudah hitung ulang fisiknya.</p>
            </>
          )}
        </div>

        <div className="mt-5 flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 rounded-2xl bg-gray-100 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-200"
          >
            Periksa lagi
          </button>
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={onConfirm}
            className={`flex-[2] rounded-2xl py-3 text-sm font-bold text-white shadow-lg bg-gradient-to-br ${
              isPartial ? 'from-amber-500 to-orange-500' : 'from-orange-500 to-amber-600'
            }`}
          >
            Ya, benar — simpan
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  );
}

/* ---- Defect cell with inline editable input + steppers ---- */

function DefectCell({
  defect, value, onChange,
}: {
  defect: Defect;
  value: number;
  onChange: (v: number) => void;
}) {
  const active = value > 0;
  const [focused, setFocused] = useState(false);
  const [raw, setRaw] = useState(String(value));

  useEffect(() => { if (!focused) setRaw(String(value)); }, [value, focused]);

  const setV = (next: number) => onChange(Math.max(0, next));

  return (
    <div
      className={`relative flex flex-col overflow-hidden rounded-2xl p-3 transition-all ${
        active ? `bg-gradient-to-br ${defect.color} text-white shadow-md` : 'bg-gray-50 text-gray-700'
      }`}
    >
      {/* Header — fixed height so numbers line up across cards */}
      <div className="flex h-14 items-start gap-2">
        <span className="text-3xl leading-none">{defect.emoji}</span>
        <div className="min-w-0 flex-1">
          <div className={`text-sm font-bold leading-tight ${active ? '' : 'text-gray-900'}`}>{defect.label}</div>
          <div className={`text-[10px] leading-tight ${active ? 'text-white/80' : 'text-gray-400'}`}>{defect.desc}</div>
        </div>
      </div>

      {/* Editable value input — no cap, validation happens at submit */}
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        value={focused ? raw : String(value)}
        onFocus={(e) => { setFocused(true); setRaw(String(value)); e.currentTarget.select(); }}
        onBlur={() => {
          setFocused(false);
          const parsed = parseInt(raw.replace(/[^0-9]/g, '') || '0', 10);
          onChange(Math.max(0, parsed));
        }}
        onChange={(e) => {
          const cleaned = e.target.value.replace(/[^0-9]/g, '').slice(0, 5);
          setRaw(cleaned);
          const n = parseInt(cleaned || '0', 10);
          onChange(Math.max(0, n));
        }}
        onKeyDown={(e) => { if (e.key === 'Enter') (e.currentTarget as HTMLInputElement).blur(); }}
        className={`mt-3 w-full bg-transparent text-center text-5xl font-extrabold leading-none tracking-tight outline-none ${
          active ? 'text-white placeholder-white/40' : 'text-gray-300 focus:text-gray-900'
        }`}
        aria-label={`${defect.label} count`}
      />

      {/* Steppers */}
      <div className="mt-3 grid grid-cols-3 gap-1.5">
        <motion.button
          whileTap={{ scale: 0.88 }}
          onClick={() => setV(value - 1)}
          disabled={value <= 0}
          className={`rounded-xl py-3 text-xl font-bold disabled:opacity-30 ${
            active ? 'bg-white/25 text-white hover:bg-white/35' : 'bg-white text-gray-700 shadow-sm hover:bg-gray-100'
          }`}
        >
          −
        </motion.button>
        <motion.button
          whileTap={{ scale: 0.88 }}
          onClick={() => setV(value + 1)}
          className={`rounded-xl py-3 text-xl font-bold ${
            active ? 'bg-white/25 text-white hover:bg-white/35' : 'bg-white text-gray-700 shadow-sm hover:bg-gray-100'
          }`}
        >
          +
        </motion.button>
        <motion.button
          whileTap={{ scale: 0.88 }}
          onClick={() => setV(value + 10)}
          className={`rounded-xl py-3 text-sm font-bold ${
            active ? 'bg-white/25 text-white hover:bg-white/35' : 'bg-white text-gray-700 shadow-sm hover:bg-gray-100'
          }`}
        >
          +10
        </motion.button>
      </div>
    </div>
  );
}

/* ---- Stock panel (inline compact) ---- */

function StockPanel({ positionId }: { positionId: string }) {
  const { data } = useStockAvailability(positionId);
  if (!data || !data.is_stock) return null;
  const sufficient = data.sufficient_on_factory;
  return (
    <div className={`mt-3 rounded-2xl border p-3 text-xs ${
      sufficient ? 'border-emerald-200 bg-emerald-50/60' : 'border-amber-200 bg-amber-50/60'
    }`}>
      <div className="flex items-center justify-between">
        <span className="font-semibold text-gray-700">Stok: {data.factory_available}/{data.needed} pcs di pabrik</span>
        <span>{sufficient ? '✓' : '⚠'}</span>
      </div>
    </div>
  );
}

/* ============================================================
   PACK VIEW
   ============================================================ */

function PackView({
  positions, isLoading, onBack, onSuccess,
}: {
  positions: PositionItem[];
  isLoading: boolean;
  onBack: () => void;
  onSuccess: () => void;
}) {
  return (
    <>
      <BackBar title="Pak → QC" onBack={onBack} subtitle={`${positions.length} siap dipak`} />
      <div className="mx-auto max-w-xl px-4 py-4 space-y-3">
        <div className="flex items-start gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">
          <span className="text-base">📸</span>
          <div>
            <div className="font-semibold">Foto dulu, baru kirim ke QC</div>
            <div className="mt-0.5 text-emerald-700">Pak plitka, ambil foto dusnya, lalu kirim. Tanpa foto tidak bisa kirim.</div>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
        ) : positions.length === 0 ? (
          <EmptyTile emoji="📦" title="Beres!" sub="Tidak ada yang perlu dikirim." />
        ) : (
          <div className="grid gap-4">
            {positions.map((p) => (
              <PackCard key={p.id} p={p} onSuccess={onSuccess} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function PackCard({ p, onSuccess }: { p: PositionItem; onSuccess: () => void }) {
  const changeStatus = useChangePositionStatus();
  const { data: photosData } = usePackingPhotos({ position_id: p.id });
  const photos = photosData?.items || [];
  const hasPhoto = photos.length > 0;

  const uploadMutation = useUploadPackingPhoto();
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [expanded, setExpanded] = useState(!hasPhoto);

  useEffect(() => {
    if (!pendingFile) { setPreview(null); return; }
    const url = URL.createObjectURL(pendingFile);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [pendingFile]);

  const handleUpload = async () => {
    if (!pendingFile) return;
    try {
      await uploadMutation.mutateAsync({
        file: pendingFile,
        orderId: p.order_id,
        positionId: p.id,
        notes: undefined,
      });
      toast.success('📸 Foto tersimpan');
      setPendingFile(null);
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || 'Gagal unggah foto';
      toast.error(msg);
    }
  };

  const sendToQC = async () => {
    setSending(true);
    try {
      await changeStatus.mutateAsync({ id: p.id, status: 'sent_to_quality_check' });
      toast.success(`📦 ${p.order_number} · ${p.quantity} pcs → QC`, { description: 'Mantap! +poin' });
      onSuccess();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Gagal';
      toast.error(msg);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="rounded-3xl border border-gray-100 bg-white p-3 shadow-sm">
      <PositionCard p={p} accent="from-emerald-50/70 to-teal-50/50" />

      {/* Photo section */}
      <div className="mt-3">
        {hasPhoto && !expanded ? (
          <div className="flex items-center gap-3 rounded-2xl bg-emerald-50 p-3">
            <div className="flex h-12 w-12 flex-shrink-0 overflow-hidden rounded-xl">
              <img src={photos[0].photo_url} alt="" className="h-full w-full object-cover" />
            </div>
            <div className="flex-1 text-sm">
              <div className="font-semibold text-emerald-800">✓ Foto tersimpan ({photos.length})</div>
              <button onClick={() => setExpanded(true)} className="text-xs text-emerald-600 underline">Ganti / tambah foto</button>
            </div>
          </div>
        ) : preview ? (
          <div>
            <img src={preview} alt="preview" className="w-full rounded-2xl object-cover" />
            <div className="mt-2 flex gap-2">
              <button
                onClick={() => setPendingFile(null)}
                className="flex-1 rounded-2xl bg-gray-100 py-2.5 text-sm font-semibold text-gray-700"
              >
                Buang
              </button>
              <motion.button
                whileTap={{ scale: 0.97 }}
                onClick={handleUpload}
                disabled={uploadMutation.isPending}
                className="flex-[2] rounded-2xl bg-gradient-to-br from-sky-500 to-blue-600 py-2.5 text-sm font-bold text-white shadow-md disabled:opacity-60"
              >
                {uploadMutation.isPending ? 'Mengunggah…' : '✨ Unggah foto'}
              </motion.button>
            </div>
          </div>
        ) : (
          <label className="flex cursor-pointer items-center gap-3 rounded-2xl border-2 border-dashed border-sky-200 bg-sky-50/40 p-3 hover:border-sky-400">
            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) setPendingFile(f);
              }}
              className="hidden"
            />
            <span className="text-3xl">📷</span>
            <div className="text-sm">
              <div className="font-semibold text-gray-900">Ambil foto dus</div>
              <div className="text-xs text-gray-500">kamera atau galeri · wajib</div>
            </div>
          </label>
        )}
      </div>

      {/* Send to QC — gated on photo */}
      <motion.button
        whileTap={hasPhoto ? { scale: 0.97 } : undefined}
        onClick={sendToQC}
        disabled={!hasPhoto || sending}
        className={`mt-3 w-full rounded-2xl px-4 py-4 text-base font-bold text-white shadow-md ${
          hasPhoto
            ? 'bg-gradient-to-br from-emerald-500 to-teal-600'
            : 'cursor-not-allowed bg-gray-300'
        }`}
      >
        {sending ? 'Mengirim…' : hasPhoto ? '✨ Kirim ke QC →' : '📷 Ambil foto dulu'}
      </motion.button>
    </div>
  );
}

/* ============================================================
   GRIND VIEW
   ============================================================ */

function GrindView({
  positions, isLoading, onBack,
}: {
  positions: PositionItem[];
  isLoading: boolean;
  onBack: () => void;
}) {
  const totalQty = positions.reduce((s, p) => s + (p.quantity || 0), 0);

  return (
    <>
      <BackBar title="Stok gerinda" onBack={onBack} subtitle={`${positions.length} posisi · ${totalQty} pcs`} />
      <div className="mx-auto max-w-xl px-4 py-4 space-y-3">
        <div className="flex items-start gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
          <span className="text-base">ℹ️</span>
          <div>
            <div className="font-semibold">Ini daftar stok — bukan keputusan</div>
            <div className="mt-0.5 text-slate-500">Keputusan gerinda vs Mana diambil PM. Kamu lihat aja apa yang ada, untuk tahu kalau ditanya.</div>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
        ) : positions.length === 0 ? (
          <EmptyTile emoji="⚙️" title="Kosong" sub="Tidak ada stok gerinda." />
        ) : (
          <div className="grid gap-3">
            {positions.map((p) => (
              <PositionCard key={p.id} p={p} accent="from-slate-50 to-white" />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

/* ============================================================
   TASKS VIEW
   ============================================================ */

const TASK_TYPE_META: Record<string, { emoji: string; label: string; gradient: string }> = {
  showroom_transfer: { emoji: '🏛️', label: 'Ke showroom', gradient: 'from-amber-400 to-orange-500' },
  photographing: { emoji: '📸', label: 'Foto produk', gradient: 'from-sky-400 to-blue-500' },
  packing_photo: { emoji: '📦', label: 'Foto packing', gradient: 'from-emerald-400 to-teal-500' },
  quality_check: { emoji: '🔍', label: 'Cek kualitas', gradient: 'from-indigo-400 to-violet-500' },
  stencil_order: { emoji: '🎭', label: 'Order stencil', gradient: 'from-purple-400 to-pink-500' },
  silk_screen_order: { emoji: '🖼️', label: 'Silk screen', gradient: 'from-rose-400 to-pink-500' },
  color_matching: { emoji: '🎨', label: 'Cocokkan warna', gradient: 'from-fuchsia-400 to-pink-500' },
  material_order: { emoji: '📋', label: 'Order material', gradient: 'from-slate-400 to-slate-600' },
};

function TasksView({
  tasks, isLoading, onBack, onSuccess,
}: {
  tasks: TaskItem[];
  isLoading: boolean;
  onBack: () => void;
  onSuccess: () => void;
}) {
  const completeMutation = useCompleteTask();
  const [busy, setBusy] = useState<string | null>(null);

  const complete = async (t: TaskItem) => {
    setBusy(t.id);
    try {
      await completeMutation.mutateAsync(t.id);
      toast.success(`✅ Tugas selesai`, { description: 'Mantap! +poin' });
      onSuccess();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Gagal';
      toast.error(msg);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <BackBar title="Tugas saya" onBack={onBack} subtitle={`${tasks.length} terbuka`} />
      <div className="mx-auto max-w-xl px-4 py-4">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
        ) : tasks.length === 0 ? (
          <EmptyTile emoji="🎯" title="Selesai semua!" sub="Tidak ada tugas terbuka." />
        ) : (
          <div className="grid gap-3">
            {tasks.map((t) => {
              const meta = TASK_TYPE_META[t.type] || { emoji: '📌', label: t.type.replace(/_/g, ' '), gradient: 'from-gray-400 to-gray-600' };
              return (
                <div key={t.id} className="rounded-3xl border border-gray-100 bg-white p-4 shadow-sm">
                  <div className="flex items-start gap-3">
                    <div className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${meta.gradient} text-2xl shadow-sm`}>
                      {meta.emoji}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-gray-900">{meta.label}</span>
                        {t.blocking && (
                          <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-bold text-red-700">PENTING</span>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-gray-600">{t.description || '—'}</p>
                      {t.related_order_number && (
                        <p className="mt-0.5 text-[10px] text-gray-400">Order: {t.related_order_number}</p>
                      )}
                    </div>
                  </div>
                  <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={() => complete(t)}
                    disabled={busy === t.id}
                    className="mt-3 w-full rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 px-4 py-3.5 text-sm font-bold text-white shadow-md disabled:opacity-60"
                  >
                    {busy === t.id ? 'Menyelesaikan…' : '✨ Selesaikan'}
                  </motion.button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
