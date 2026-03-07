import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { useUiStore } from '@/stores/uiStore';
import { usePositions, useChangePositionStatus, useSplitPosition, type PositionItem } from '@/hooks/usePositions';
import { useSorterTasks, useCompleteTask } from '@/hooks/useTasks';
import type { TaskItem } from '@/api/tasks';

const TABS = [
  { id: 'sorting', label: 'Sorting' },
  { id: 'packing', label: 'Packing' },
  { id: 'photos', label: 'Photos' },
  { id: 'tasks', label: 'Tasks' },
];

export default function SorterPackerDashboard() {
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);
  const [tab, setTab] = useState('sorting');

  // Sorting positions (transferred_to_sorting)
  const { data: sortingData, isLoading: sortingLoading } = usePositions(
    activeFactoryId
      ? { factory_id: activeFactoryId, status: 'transferred_to_sorting' }
      : { status: 'transferred_to_sorting' },
  );
  const sortingPositions = sortingData?.items || [];

  // Packed positions
  const { data: packedData, isLoading: packedLoading } = usePositions(
    activeFactoryId
      ? { factory_id: activeFactoryId, status: 'packed' }
      : { status: 'packed' },
  );
  const packedPositions = packedData?.items || [];

  // Tasks
  const { data: tasksData, isLoading: tasksLoading } = useSorterTasks(activeFactoryId || undefined);
  const tasks = tasksData?.items || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sorting & Packing</h1>
        <p className="mt-1 text-sm text-gray-500">Sort fired tiles, pack, upload photos</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="text-center">
          <p className="text-2xl font-bold text-orange-600">{sortingPositions.length}</p>
          <p className="text-xs text-gray-500">Awaiting Sorting</p>
        </Card>
        <Card className="text-center">
          <p className="text-2xl font-bold text-green-600">{packedPositions.length}</p>
          <p className="text-xs text-gray-500">Packed</p>
        </Card>
        <Card className="text-center">
          <p className="text-2xl font-bold text-blue-600">{tasks.length}</p>
          <p className="text-xs text-gray-500">Open Tasks</p>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} activeTab={tab} onChange={setTab} />

      {/* Tab Content */}
      {tab === 'sorting' && (
        <SortingTab positions={sortingPositions} isLoading={sortingLoading} />
      )}
      {tab === 'packing' && (
        <PackingTab positions={packedPositions} isLoading={packedLoading} />
      )}
      {tab === 'photos' && <PhotosTab />}
      {tab === 'tasks' && (
        <TasksTab tasks={tasks} isLoading={tasksLoading} />
      )}
    </div>
  );
}

/* ============================================================
   SORTING TAB
   ============================================================ */

function SortingTab({ positions, isLoading }: { positions: PositionItem[]; isLoading: boolean }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = positions.find((p) => p.id === selectedId) || null;

  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  }

  if (positions.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No positions awaiting sorting</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Position list */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {positions.map((p) => (
          <button
            key={p.id}
            onClick={() => setSelectedId(p.id === selectedId ? null : p.id)}
            className={`w-full rounded-lg border p-3 text-left transition-all ${
              p.id === selectedId
                ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-500'
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">{p.order_number}</span>
              <Badge status={p.status} />
            </div>
            <p className="mt-1 text-sm text-gray-600">
              {p.color} · {p.size}
            </p>
            <p className="mt-0.5 text-lg font-bold text-gray-900">{p.quantity} pcs</p>
          </button>
        ))}
      </div>

      {/* Split form */}
      {selected && (
        <SplitForm
          position={selected}
          onDone={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}

/* ---- Split Form ---- */

function SplitForm({ position, onDone }: { position: PositionItem; onDone: () => void }) {
  const splitMutation = useSplitPosition();
  const [good, setGood] = useState(position.quantity);
  const [repair, setRepair] = useState(0);
  const [colorMismatch, setColorMismatch] = useState(0);
  const [grinding, setGrinding] = useState(0);
  const [writeOff, setWriteOff] = useState(0);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');

  const total = good + repair + colorMismatch + grinding + writeOff;
  const isValid = total === position.quantity && good >= 0;

  const handleSubmit = async () => {
    setError('');
    try {
      await splitMutation.mutateAsync({
        id: position.id,
        data: {
          good_quantity: good,
          repair_quantity: repair,
          color_mismatch_quantity: colorMismatch,
          grinding_quantity: grinding,
          write_off_quantity: writeOff,
          notes: notes || undefined,
        },
      });
      onDone();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setError(resp?.detail || 'Failed to split position');
    }
  };

  return (
    <Card className="border-primary-200 bg-primary-50/30">
      {/* Position info */}
      <div className="mb-4 flex items-center gap-3 rounded-md bg-white p-3">
        <div className="flex-1">
          <span className="text-sm font-semibold">{position.order_number}</span>
          <span className="mx-2 text-gray-300">·</span>
          <span className="text-sm text-gray-600">{position.color}</span>
          <span className="mx-2 text-gray-300">·</span>
          <span className="text-sm text-gray-600">{position.size}</span>
        </div>
        <span className="text-lg font-bold">{position.quantity} pcs</span>
      </div>

      {/* Quantity inputs — large touch targets */}
      <div className="space-y-3">
        <QtyInput label="Good" value={good} onChange={setGood} color="text-green-700" />
        <QtyInput label="Repair" value={repair} onChange={setRepair} color="text-yellow-700" />
        <QtyInput label="Color Mismatch" value={colorMismatch} onChange={setColorMismatch} color="text-orange-700" />
        <QtyInput label="Grinding" value={grinding} onChange={setGrinding} color="text-gray-700" />
        <QtyInput label="Write-off" value={writeOff} onChange={setWriteOff} color="text-red-700" />
      </div>

      {/* Total */}
      <div className={`mt-4 flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium ${
        isValid ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
      }`}>
        <span>Total</span>
        <span>{total} / {position.quantity} {isValid ? '✓' : '✗'}</span>
      </div>

      {/* Notes */}
      <textarea
        placeholder="Notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        className="mt-3 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
        rows={2}
      />

      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}

      {/* Submit */}
      <Button
        className="mt-4 w-full"
        onClick={handleSubmit}
        disabled={!isValid || splitMutation.isPending}
      >
        {splitMutation.isPending ? 'Submitting...' : 'Submit Split'}
      </Button>
    </Card>
  );
}

function QtyInput({
  label,
  value,
  onChange,
  color,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className={`w-32 text-sm font-medium ${color}`}>{label}</span>
      <input
        type="number"
        inputMode="numeric"
        min={0}
        value={value}
        onChange={(e) => onChange(Math.max(0, parseInt(e.target.value) || 0))}
        className="min-h-[44px] flex-1 rounded-md border border-gray-300 px-3 py-2 text-center text-lg font-semibold focus:border-primary-500 focus:outline-none"
      />
    </div>
  );
}

/* ============================================================
   PACKING TAB
   ============================================================ */

function PackingTab({ positions, isLoading }: { positions: PositionItem[]; isLoading: boolean }) {
  const changeStatus = useChangePositionStatus();
  const [confirmId, setConfirmId] = useState<string | null>(null);

  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  }

  if (positions.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No packed positions ready for QC</p>
      </div>
    );
  }

  const handleSendToQC = async (id: string) => {
    await changeStatus.mutateAsync({ id, status: 'sent_to_quality_check' });
  };

  return (
    <>
      <div className="space-y-3">
        {positions.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold">{p.order_number}</span>
                <Badge status={p.status} />
              </div>
              <p className="mt-0.5 text-sm text-gray-500">
                {p.color} · {p.size} · {p.quantity} pcs
              </p>
            </div>
            <Button
              size="sm"
              onClick={() => setConfirmId(p.id)}
              disabled={changeStatus.isPending}
            >
              Send to QC
            </Button>
          </div>
        ))}
      </div>
      <ConfirmDialog
        open={!!confirmId}
        onClose={() => setConfirmId(null)}
        onConfirm={() => confirmId && handleSendToQC(confirmId)}
        title="Send to Quality Check"
        message="This position will be sent for quality inspection. Continue?"
      />
    </>
  );
}

/* ============================================================
   PHOTOS TAB (placeholder)
   ============================================================ */

function PhotosTab() {
  return (
    <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-2xl">
        📷
      </div>
      <p className="text-lg font-medium text-gray-400">Packing Photos</p>
      <p className="mt-1 text-sm text-gray-400">
        Upload 1 m² photo with color sample for each position.
      </p>
      <p className="mt-3 text-xs text-gray-300">
        Requires Supabase Storage configuration — coming soon
      </p>
    </div>
  );
}

/* ============================================================
   TASKS TAB
   ============================================================ */

function TasksTab({ tasks, isLoading }: { tasks: TaskItem[]; isLoading: boolean }) {
  const completeMutation = useCompleteTask();
  const [confirmId, setConfirmId] = useState<string | null>(null);

  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  }

  if (tasks.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No open tasks assigned</p>
      </div>
    );
  }

  const handleComplete = async (id: string) => {
    await completeMutation.mutateAsync(id);
  };

  const TASK_TYPE_LABELS: Record<string, string> = {
    showroom_transfer: 'Send to Showroom',
    photographing: 'Send for Photo',
    packing_photo: 'Packing Photo',
    quality_check: 'Quality Check',
    stencil_order: 'Stencil Order',
    silk_screen_order: 'Silk Screen Order',
    color_matching: 'Color Matching',
    material_order: 'Material Order',
  };

  return (
    <>
      <div className="space-y-3">
        {tasks.map((t) => (
          <div
            key={t.id}
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
          >
            <div>
              <div className="flex items-center gap-2">
                <Badge status={t.type} label={TASK_TYPE_LABELS[t.type] || t.type.replace(/_/g, ' ')} />
                {t.blocking && (
                  <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700">
                    Blocking
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-gray-600">{t.description || 'No description'}</p>
              {t.related_order_number && (
                <p className="mt-0.5 text-xs text-gray-400">Order: {t.related_order_number}</p>
              )}
            </div>
            <Button
              size="sm"
              onClick={() => setConfirmId(t.id)}
              disabled={completeMutation.isPending}
            >
              Complete
            </Button>
          </div>
        ))}
      </div>
      <ConfirmDialog
        open={!!confirmId}
        onClose={() => setConfirmId(null)}
        onConfirm={() => confirmId && handleComplete(confirmId)}
        title="Complete Task"
        message="Mark this task as done?"
      />
    </>
  );
}
