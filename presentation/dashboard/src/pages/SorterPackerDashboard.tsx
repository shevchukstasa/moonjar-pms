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
import { usePackingPhotos, useUploadPackingPhoto, useDeletePackingPhoto } from '@/hooks/usePackingPhotos';

/* ============================================================
   TYPES & CONSTS
   ============================================================ */

type View = 'home' | 'sort' | 'pack' | 'grind' | 'photos' | 'tasks';

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
              onSuccess={(n, rate) => { bump(n); if (rate >= 85) fireConfetti(); }}
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

        {view === 'photos' && (
          <motion.div key="photos" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.2 }}>
            <PhotosView onBack={() => setView('home')} />
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
        />
        <ActionTile
          emoji="📷"
          label="Foto"
          sub="bukti packing"
          count={null}
          gradient="from-sky-400 to-blue-500"
          onClick={() => onNavigate('photos')}
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
        <div className="mx-auto max-w-xl px-4 py-4">
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
const DEFECTS: Defect[] = [
  { key: 'refire', label: 'Bakar ulang', emoji: '🔥', color: 'from-amber-400 to-orange-500', desc: 'Perlu bakar lagi' },
  { key: 'repair', label: 'Perbaikan', emoji: '🔧', color: 'from-yellow-400 to-amber-500', desc: 'Glaze ulang & bakar' },
  { key: 'color_mismatch', label: 'Warna salah', emoji: '🎨', color: 'from-rose-400 to-pink-500', desc: 'Warna tidak cocok' },
  { key: 'grinding', label: 'Gerinda', emoji: '⚙️', color: 'from-slate-400 to-slate-600', desc: 'Perlu digerinda' },
  { key: 'write_off', label: 'Rusak', emoji: '💥', color: 'from-red-500 to-rose-600', desc: 'Buang / write off' },
];

function SplitWizard({ position, onDone }: { position: PositionItem; onDone: (goodCount: number, rate: number) => void }) {
  const splitMutation = useSplitPosition();
  const [defects, setDefects] = useState<Partial<Record<DefectKey, number>>>({});
  const [pad, setPad] = useState<DefectKey | null>(null);
  const [notes, setNotes] = useState('');
  const [showNotes, setShowNotes] = useState(false);

  const defectSum = Object.values(defects).reduce((a, b) => a + (b || 0), 0);
  const good = position.quantity - defectSum;
  const overflow = defectSum > position.quantity;
  const isValid = !overflow && good >= 0;

  const submit = async (allGood = false) => {
    const payload = {
      good_quantity: allGood ? position.quantity : good,
      refire_quantity: allGood ? 0 : defects.refire || 0,
      repair_quantity: allGood ? 0 : defects.repair || 0,
      color_mismatch_quantity: allGood ? 0 : defects.color_mismatch || 0,
      grinding_quantity: allGood ? 0 : defects.grinding || 0,
      write_off_quantity: allGood ? 0 : defects.write_off || 0,
      notes: notes || undefined,
    };
    try {
      await splitMutation.mutateAsync({ id: position.id, data: payload });
      const rate = Math.round((payload.good_quantity / position.quantity) * 100);
      const emoji = rate >= 95 ? '🏆' : rate >= 85 ? '🎉' : rate >= 70 ? '👍' : '💪';
      toast.success(`${emoji} ${payload.good_quantity} bagus dari ${position.quantity} (${rate}%)`, {
        description: rate >= 95 ? 'Kerja hebat! +poin bonus' : 'Tersimpan. +poin',
      });
      onDone(payload.good_quantity, rate);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || (err as { message?: string })?.message
        || 'Gagal simpan';
      toast.error(msg);
    }
  };

  const setDefect = (k: DefectKey, v: number) => {
    setDefects((d) => {
      const next = { ...d };
      if (v <= 0) delete next[k];
      else next[k] = v;
      return next;
    });
  };

  const hasDefects = defectSum > 0;

  const rate = Math.round((good / position.quantity) * 100);

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

      {/* Defect reporter — primary path */}
      <div className="rounded-3xl border border-gray-100 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-semibold text-gray-900">
            {hasDefects ? 'Cacat dilaporkan' : 'Cek tiap plitka · tap kategori kalo ada cacat:'}
          </p>
          {hasDefects && (
            <button
              onClick={() => setDefects({})}
              className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200"
            >
              Reset
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          {DEFECTS.map((d) => {
            const v = defects[d.key] || 0;
            const active = v > 0;
            return (
              <motion.button
                key={d.key}
                whileTap={{ scale: 0.95 }}
                onClick={() => setPad(d.key)}
                className={`relative overflow-hidden rounded-2xl p-3 text-left transition-all ${
                  active
                    ? `bg-gradient-to-br ${d.color} text-white shadow-md`
                    : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-2xl">{d.emoji}</span>
                  {active && (
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="rounded-full bg-white/30 px-2 py-0.5 text-sm font-bold"
                    >
                      {v}
                    </motion.span>
                  )}
                </div>
                <div className="mt-2">
                  <div className={`text-sm font-bold ${active ? '' : 'text-gray-900'}`}>{d.label}</div>
                  <div className={`text-[10px] ${active ? 'text-white/80' : 'text-gray-400'}`}>{d.desc}</div>
                </div>
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Running total — ALWAYS visible */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl bg-gradient-to-br from-white to-emerald-50/30 p-5 shadow-sm"
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-wide text-gray-400">Bagus (auto)</p>
            <p className={`mt-1 text-5xl font-extrabold leading-none ${overflow ? 'text-red-600' : 'text-emerald-600'}`}>
              {overflow ? '!!' : good}
            </p>
            <p className="mt-1 text-xs text-gray-400">dari {position.quantity}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wide text-gray-400">Cacat</p>
            <p className="mt-1 text-5xl font-extrabold leading-none text-amber-600">{defectSum}</p>
            <p className="mt-1 text-xs text-gray-400">{hasDefects ? `${Math.round((defectSum / position.quantity) * 100)}%` : 'belum ada'}</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-gray-100">
          <motion.div
            initial={false}
            animate={{ width: `${Math.min(100, (good / Math.max(1, position.quantity)) * 100)}%` }}
            transition={{ type: 'spring', stiffness: 200, damping: 24 }}
            className={`h-full ${overflow ? 'bg-red-500' : 'bg-gradient-to-r from-emerald-400 to-teal-500'}`}
          />
        </div>

        {overflow && (
          <p className="mt-2 text-xs text-red-600">
            Total cacat ({defectSum}) lebih dari {position.quantity}. Perbaiki angkanya.
          </p>
        )}

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
          whileTap={{ scale: 0.97 }}
          whileHover={{ y: -1 }}
          onClick={() => submit(false)}
          disabled={!isValid || splitMutation.isPending}
          className="relative mt-4 w-full overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-500 via-green-500 to-teal-600 px-4 py-5 text-white shadow-xl disabled:cursor-not-allowed disabled:opacity-50"
        >
          <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-white/10" />
          <div className="relative flex items-center justify-center gap-3">
            <span className="text-2xl">{rate >= 95 ? '🏆' : rate >= 85 ? '✨' : '✓'}</span>
            <div className="text-left">
              <div className="text-lg font-extrabold">
                {splitMutation.isPending ? 'Menyimpan…' : 'Selesai & Simpan'}
              </div>
              <div className="text-xs text-white/90">{good} bagus · {defectSum} cacat · {rate}%</div>
            </div>
          </div>
        </motion.button>
      </motion.div>

      {/* Numpad modal */}
      <AnimatePresence>
        {pad && (
          <NumPad
            defect={DEFECTS.find((d) => d.key === pad)!}
            max={position.quantity - defectSum + (defects[pad] || 0)}
            initial={defects[pad] || 0}
            onClose={() => setPad(null)}
            onSave={(v) => {
              setDefect(pad, v);
              setPad(null);
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function NumPad({
  defect, max, initial, onClose, onSave,
}: {
  defect: Defect;
  max: number;
  initial: number;
  onClose: () => void;
  onSave: (v: number) => void;
}) {
  const [v, setV] = useState<string>(initial > 0 ? String(initial) : '');
  const n = parseInt(v || '0', 10);
  const overflow = n > max;

  const press = (key: string) => {
    if (key === 'del') {
      setV((s) => s.slice(0, -1));
      return;
    }
    if (key === 'clear') {
      setV('');
      return;
    }
    setV((s) => (s.length >= 4 ? s : (s === '0' ? key : s + key)));
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm sm:items-center"
    >
      <motion.div
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 40, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 320, damping: 28 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-t-3xl bg-white p-5 shadow-2xl sm:rounded-3xl"
      >
        {/* Header */}
        <div className={`rounded-2xl bg-gradient-to-br ${defect.color} p-4 text-white`}>
          <div className="flex items-center gap-3">
            <span className="text-3xl">{defect.emoji}</span>
            <div>
              <div className="text-base font-bold">{defect.label}</div>
              <div className="text-xs text-white/80">{defect.desc}</div>
            </div>
          </div>
        </div>

        {/* Display */}
        <div className="mt-4 text-center">
          <div className={`text-6xl font-extrabold ${overflow ? 'text-red-600' : 'text-gray-900'}`}>
            {v || '0'}
          </div>
          <div className="mt-1 text-xs text-gray-400">maks {max} pcs</div>
        </div>

        {/* Keypad */}
        <div className="mt-4 grid grid-cols-3 gap-2">
          {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((k) => (
            <motion.button
              key={k}
              whileTap={{ scale: 0.92 }}
              onClick={() => press(k)}
              className="rounded-2xl bg-gray-100 py-4 text-2xl font-bold text-gray-900 hover:bg-gray-200"
            >
              {k}
            </motion.button>
          ))}
          <motion.button whileTap={{ scale: 0.92 }} onClick={() => press('clear')}
            className="rounded-2xl bg-gray-100 py-4 text-sm font-bold text-gray-600 hover:bg-gray-200">
            C
          </motion.button>
          <motion.button whileTap={{ scale: 0.92 }} onClick={() => press('0')}
            className="rounded-2xl bg-gray-100 py-4 text-2xl font-bold text-gray-900 hover:bg-gray-200">
            0
          </motion.button>
          <motion.button whileTap={{ scale: 0.92 }} onClick={() => press('del')}
            className="rounded-2xl bg-gray-100 py-4 text-xl font-bold text-gray-600 hover:bg-gray-200">
            ⌫
          </motion.button>
        </div>

        {/* Actions */}
        <div className="mt-4 flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 rounded-2xl bg-gray-100 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-200"
          >
            Batal
          </button>
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={() => onSave(Math.max(0, Math.min(max, n)))}
            disabled={overflow}
            className={`flex-[2] rounded-2xl py-3 text-sm font-bold text-white shadow-lg disabled:opacity-50 bg-gradient-to-br ${defect.color}`}
          >
            Simpan {n > 0 ? `${Math.min(max, n)} pcs` : ''}
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
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
  const changeStatus = useChangePositionStatus();
  const [sending, setSending] = useState<string | null>(null);

  const sendToQC = async (p: PositionItem) => {
    setSending(p.id);
    try {
      await changeStatus.mutateAsync({ id: p.id, status: 'sent_to_quality_check' });
      toast.success(`📦 ${p.order_number} · ${p.quantity} pcs → QC`, {
        description: 'Mantap! +poin',
      });
      onSuccess();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Gagal';
      toast.error(msg);
    } finally {
      setSending(null);
    }
  };

  return (
    <>
      <BackBar title="Pak → QC" onBack={onBack} subtitle={`${positions.length} siap`} />
      <div className="mx-auto max-w-xl px-4 py-4">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
        ) : positions.length === 0 ? (
          <EmptyTile emoji="📦" title="Beres!" sub="Tidak ada yang perlu dikirim." />
        ) : (
          <div className="grid gap-3">
            {positions.map((p) => (
              <div key={p.id} className="space-y-2">
                <PositionCard p={p} accent="from-emerald-50/70 to-teal-50/50" />
                <motion.button
                  whileTap={{ scale: 0.97 }}
                  onClick={() => sendToQC(p)}
                  disabled={sending === p.id}
                  className="w-full rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 px-4 py-4 text-base font-bold text-white shadow-md disabled:opacity-60"
                >
                  {sending === p.id ? 'Mengirim…' : '✨ Kirim ke QC →'}
                </motion.button>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
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
  const changeStatus = useChangePositionStatus();
  const [busy, setBusy] = useState<string | null>(null);

  const decide = async (p: PositionItem, action: 'grind' | 'mana') => {
    setBusy(p.id);
    const newStatus = action === 'grind' ? 'awaiting_reglaze' : 'mana_confirmation';
    try {
      await changeStatus.mutateAsync({ id: p.id, status: newStatus, notes: `Grinding decision: ${action}` });
      toast.success(
        action === 'grind' ? `⚙️ ${p.order_number} → reglaze` : `💥 ${p.order_number} → Mana`,
      );
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Gagal';
      toast.error(msg);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <BackBar title="Stok gerinda" onBack={onBack} subtitle={`${positions.length} perlu diputuskan`} />
      <div className="mx-auto max-w-xl px-4 py-4">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
        ) : positions.length === 0 ? (
          <EmptyTile emoji="⚙️" title="Tidak ada keputusan" sub="Stok gerinda kosong." />
        ) : (
          <div className="grid gap-4">
            {positions.map((p) => (
              <div key={p.id} className="rounded-3xl border border-gray-100 bg-white p-3 shadow-sm">
                <PositionCard p={p} accent="from-slate-50 to-white" />
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <motion.button
                    whileTap={{ scale: 0.96 }}
                    onClick={() => decide(p, 'grind')}
                    disabled={busy === p.id}
                    className="rounded-2xl bg-gradient-to-br from-slate-500 to-slate-700 px-4 py-4 text-sm font-bold text-white shadow-md disabled:opacity-60"
                  >
                    ⚙️ Gerinda
                  </motion.button>
                  <motion.button
                    whileTap={{ scale: 0.96 }}
                    onClick={() => decide(p, 'mana')}
                    disabled={busy === p.id}
                    className="rounded-2xl bg-gradient-to-br from-red-500 to-rose-600 px-4 py-4 text-sm font-bold text-white shadow-md disabled:opacity-60"
                  >
                    💥 Mana
                  </motion.button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

/* ============================================================
   PHOTOS VIEW
   ============================================================ */

function PhotosView({ onBack }: { onBack: () => void }) {
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: posData } = usePositions(
    activeFactoryId
      ? { factory_id: activeFactoryId, status: 'packed,transferred_to_sorting,sent_to_quality_check', per_page: 200 }
      : { status: 'packed,transferred_to_sorting,sent_to_quality_check', per_page: 200 },
  );
  const positions = posData?.items || [];
  const selected = positions.find((p) => p.id === selectedId) || null;

  if (selected) {
    return (
      <>
        <BackBar
          title="Foto packing"
          onBack={() => setSelectedId(null)}
          subtitle={`${selected.order_number} · ${selected.color}`}
        />
        <div className="mx-auto max-w-xl px-4 py-4">
          <PhotoEditor position={selected} />
        </div>
      </>
    );
  }

  return (
    <>
      <BackBar title="Foto packing" onBack={onBack} subtitle="Tap posisi untuk foto" />
      <div className="mx-auto max-w-xl px-4 py-4">
        {positions.length === 0 ? (
          <EmptyTile emoji="📷" title="Tidak ada posisi" sub="Belum ada yang perlu difoto." />
        ) : (
          <div className="grid gap-3">
            {positions.map((p) => (
              <PositionCard
                key={p.id}
                p={p}
                onClick={() => setSelectedId(p.id)}
                accent="from-sky-50 to-blue-50"
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function PhotoEditor({ position }: { position: PositionItem }) {
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [notes, setNotes] = useState('');
  const uploadMutation = useUploadPackingPhoto();
  const deleteMutation = useDeletePackingPhoto();
  const { data, isLoading } = usePackingPhotos({ position_id: position.id });
  const photos = data?.items || [];

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
        orderId: position.order_id,
        positionId: position.id,
        notes: notes || undefined,
      });
      toast.success('📸 Foto terunggah');
      setPendingFile(null);
      setNotes('');
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || 'Gagal unggah';
      toast.error(msg);
    }
  };

  return (
    <div className="space-y-4">
      {/* Camera input */}
      <div className="rounded-3xl bg-white p-4 shadow-sm">
        {!preview ? (
          <label className="block cursor-pointer rounded-2xl border-2 border-dashed border-gray-200 bg-gradient-to-br from-sky-50/40 to-blue-50/40 p-8 text-center hover:border-sky-300">
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
            <div className="text-5xl">📷</div>
            <p className="mt-2 text-base font-bold text-gray-900">Ambil foto</p>
            <p className="text-xs text-gray-500">atau pilih dari galeri</p>
          </label>
        ) : (
          <div>
            <img src={preview} alt="preview" className="w-full rounded-2xl object-cover" />
            <textarea
              placeholder="Catatan (opsional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="mt-3 w-full rounded-2xl border border-gray-200 px-3 py-2 text-sm focus:border-sky-400 focus:outline-none"
            />
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => setPendingFile(null)}
                className="flex-1 rounded-2xl bg-gray-100 py-3 text-sm font-semibold text-gray-700"
              >
                Buang
              </button>
              <motion.button
                whileTap={{ scale: 0.97 }}
                onClick={handleUpload}
                disabled={uploadMutation.isPending}
                className="flex-[2] rounded-2xl bg-gradient-to-br from-sky-500 to-blue-600 py-3 text-sm font-bold text-white shadow-md disabled:opacity-60"
              >
                {uploadMutation.isPending ? 'Mengunggah…' : '✨ Unggah'}
              </motion.button>
            </div>
          </div>
        )}
      </div>

      {/* Gallery */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase text-gray-500">
          Sudah diunggah · {photos.length}
        </p>
        {isLoading ? (
          <div className="flex justify-center py-8"><Spinner className="h-6 w-6" /></div>
        ) : photos.length === 0 ? (
          <p className="text-xs text-gray-400">Belum ada foto.</p>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {photos.map((ph) => (
              <div key={ph.id} className="group relative aspect-square overflow-hidden rounded-xl border border-gray-100">
                <img src={ph.photo_url} alt="" className="h-full w-full object-cover" />
                <button
                  onClick={() => {
                    if (confirm('Hapus foto ini?')) deleteMutation.mutate(ph.id);
                  }}
                  className="absolute right-1 top-1 rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-bold text-white opacity-90"
                  disabled={deleteMutation.isPending}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
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
