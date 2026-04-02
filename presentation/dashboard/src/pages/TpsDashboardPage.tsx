import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  horizontalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { FactorySelector } from '@/components/layout/FactorySelector';
import { useUiStore } from '@/stores/uiStore';
import {
  tpsDashboardApi,
  PRODUCTION_STAGES,
  PRODUCTIVITY_UNITS,
  COLLECTIONS,
  APPLICATION_METHODS,
  type ProcessStepItem,
  type ProcessStepCreate,
  type CalibrationStatus,
  type CalibrationSuggestion,
  type CalibrationLogEntry,
} from '@/api/tpsDashboard';
import { cn } from '@/lib/cn';
import { useNavigate } from 'react-router-dom';

// ── Helpers ─────────────────────────────────────────────────

function driftColor(drift: number | null | undefined): string {
  if (drift == null) return 'bg-gray-100 text-gray-600';
  const abs = Math.abs(drift);
  if (abs <= 5) return 'bg-green-100 text-green-700';
  if (abs <= 15) return 'bg-yellow-100 text-yellow-700';
  return 'bg-red-100 text-red-700';
}

function driftRowBg(drift: number | null | undefined): string {
  if (drift == null) return '';
  const abs = Math.abs(drift);
  if (abs > 20) return 'bg-red-50';
  if (abs > 10) return 'bg-yellow-50';
  return '';
}

function formatDrift(drift: number | null | undefined): string {
  if (drift == null) return '--';
  const sign = drift >= 0 ? '+' : '';
  return `${sign}${drift.toFixed(1)}%`;
}

function stageLabel(stage: string | null): string {
  if (!stage) return '--';
  return PRODUCTION_STAGES.find((s) => s.value === stage)?.label ?? stage;
}

function unitLabel(unit: string | null): string {
  if (!unit) return '--';
  return PRODUCTIVITY_UNITS.find((u) => u.value === unit)?.label ?? unit;
}

const EMPTY_STEP: ProcessStepCreate = {
  name: '',
  factory_id: '',
  stage: '',
  sequence: 0,
  norm_time_minutes: undefined,
  productivity_rate: undefined,
  productivity_unit: 'sqm/hour',
  measurement_basis: undefined,
  shift_count: 1,
  applicable_collections: [],
  applicable_methods: [],
  applicable_product_types: [],
  auto_calibrate: false,
  notes: '',
};

// ── Tab config ──────────────────────────────────────────────

const PAGE_TABS = [
  { id: 'pipeline', label: 'Pipeline View' },
  { id: 'rates', label: 'Rates Table' },
  { id: 'calibration', label: 'AI Calibration' },
];

// ── Main page ───────────────────────────────────────────────

export default function TpsDashboardPage() {
  const [activeTab, setActiveTab] = useState('pipeline');
  const { activeFactoryId } = useUiStore();
  const navigate = useNavigate();

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="rounded-md p-1.5 text-gray-500 hover:bg-gray-100 dark:text-stone-400 dark:hover:bg-stone-800"
            title="Back"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">TPS Dashboard</h1>
        </div>
        <FactorySelector />
      </div>

      <Tabs tabs={PAGE_TABS} activeTab={activeTab} onChange={setActiveTab} />

      {!activeFactoryId ? (
        <Card>
          <p className="text-sm text-gray-500">Select a factory to view process steps.</p>
        </Card>
      ) : (
        <>
          {activeTab === 'pipeline' && <PipelineTab factoryId={activeFactoryId} />}
          {activeTab === 'rates' && <RatesTableTab factoryId={activeFactoryId} />}
          {activeTab === 'calibration' && <CalibrationTab factoryId={activeFactoryId} />}
        </>
      )}
    </div>
  );
}


// ════════════════════════════════════════════════════════════
// TAB 1: Pipeline View
// ════════════════════════════════════════════════════════════

function PipelineTab({ factoryId }: { factoryId: string }) {
  const qc = useQueryClient();
  const [collectionFilter, setCollectionFilter] = useState('');
  const [methodFilter, setMethodFilter] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const filters = useMemo(
    () => ({
      collection: collectionFilter || undefined,
      method: methodFilter || undefined,
    }),
    [collectionFilter, methodFilter],
  );

  const { data, isLoading } = useQuery({
    queryKey: ['tps-pipeline', factoryId, filters],
    queryFn: () => tpsDashboardApi.getPipeline(factoryId, filters),
    enabled: !!factoryId,
  });

  const steps: ProcessStepItem[] = useMemo(() => {
    const raw = data?.items ?? [];
    return [...raw].sort((a, b) => a.sequence - b.sequence);
  }, [data]);

  const reorderMut = useMutation({
    mutationFn: (ids: string[]) => tpsDashboardApi.reorderSteps(ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tps-pipeline'] }),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => tpsDashboardApi.deleteStep(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tps-pipeline'] });
      qc.invalidateQueries({ queryKey: ['tps-steps'] });
    },
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const oldIndex = steps.findIndex((s) => s.id === active.id);
      const newIndex = steps.findIndex((s) => s.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;
      const reordered = arrayMove(steps, oldIndex, newIndex);
      reorderMut.mutate(reordered.map((s) => s.id));
    },
    [steps, reorderMut],
  );

  const collectionOptions = [{ value: '', label: 'All Collections' }, ...COLLECTIONS];
  const methodOptions = [{ value: '', label: 'All Methods' }, ...APPLICATION_METHODS];

  if (isLoading) {
    return <Card><div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div></Card>;
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-48">
            <Select label="Collection" options={collectionOptions} value={collectionFilter} onChange={(e) => setCollectionFilter(e.target.value)} />
          </div>
          <div className="w-48">
            <Select label="Method" options={methodOptions} value={methodFilter} onChange={(e) => setMethodFilter(e.target.value)} />
          </div>
        </div>
      </Card>

      {/* Pipeline cards */}
      <div className="overflow-x-auto pb-2">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={steps.map((s) => s.id)} strategy={horizontalListSortingStrategy}>
            <div className="flex items-start gap-3 min-w-max">
              {steps.map((step) => (
                <SortableStepCard
                  key={step.id}
                  step={step}
                  isExpanded={expandedId === step.id}
                  onToggle={() => setExpandedId(expandedId === step.id ? null : step.id)}
                  onDelete={() => setDeleteTarget(step.id)}
                  factoryId={factoryId}
                />
              ))}
              {/* Add Step button */}
              <button
                onClick={() => { setShowAdd(true); setExpandedId(null); }}
                className="flex h-[140px] w-48 flex-shrink-0 flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 text-gray-400 transition hover:border-primary-400 hover:text-primary-500 dark:border-stone-600 dark:hover:border-gold-500 dark:hover:text-gold-400"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                <span className="text-sm font-medium">Add Step</span>
              </button>
            </div>
          </SortableContext>
        </DndContext>
      </div>

      {/* Expanded edit form below pipeline */}
      {expandedId && (
        <StepEditForm
          stepId={expandedId}
          factoryId={factoryId}
          onClose={() => setExpandedId(null)}
        />
      )}

      {/* Add new step form */}
      {showAdd && (
        <StepCreateForm
          factoryId={factoryId}
          nextSequence={(steps.length > 0 ? steps[steps.length - 1].sequence : 0) + 1}
          onClose={() => setShowAdd(false)}
        />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => { if (deleteTarget) deleteMut.mutate(deleteTarget); setDeleteTarget(null); }}
        title="Delete Process Step"
        message="Are you sure you want to delete this process step? This action cannot be undone."
      />
    </div>
  );
}


// ── Sortable step card ──────────────────────────────────────

function SortableStepCard({
  step,
  isExpanded,
  onToggle,
  onDelete,
  factoryId,
}: {
  step: ProcessStepItem;
  isExpanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
  factoryId: string;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: step.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="flex-shrink-0">
      <div
        className={cn(
          'w-48 rounded-lg border bg-white p-3 shadow-sm transition dark:bg-stone-900 dark:border-stone-700',
          isExpanded && 'ring-2 ring-primary-400 dark:ring-gold-500',
        )}
      >
        {/* Drag handle */}
        <div
          {...attributes}
          {...listeners}
          className="mb-2 flex cursor-grab items-center justify-between active:cursor-grabbing"
        >
          <div className="flex items-center gap-1.5">
            <svg className="h-4 w-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M7 2a2 2 0 10.001 4.001A2 2 0 007 2zm0 6a2 2 0 10.001 4.001A2 2 0 007 8zm0 6a2 2 0 10.001 4.001A2 2 0 007 14zm6-8a2 2 0 10-.001-4.001A2 2 0 0013 6zm0 2a2 2 0 10.001 4.001A2 2 0 0013 8zm0 6a2 2 0 10.001 4.001A2 2 0 0013 14z" />
            </svg>
            <span className="text-xs font-medium text-gray-400">#{step.sequence}</span>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="rounded p-0.5 text-gray-400 hover:bg-red-50 hover:text-red-500"
            title="Delete step"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Card body (clickable) */}
        <button onClick={onToggle} className="w-full text-left">
          <h4 className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100" title={step.name}>{step.name}</h4>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-stone-400">{stageLabel(step.stage)}</p>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {step.productivity_rate ?? '--'}
            </span>
            <span className="text-xs text-gray-500">{unitLabel(step.productivity_unit)}</span>
          </div>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-gray-500">{step.shift_count} shift{step.shift_count !== 1 ? 's' : ''}</span>
            <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', driftColor(step.drift_percent))}>
              {formatDrift(step.drift_percent)}
            </span>
          </div>
        </button>
      </div>
    </div>
  );
}


// ── Step edit form (inline below pipeline) ──────────────────

function StepEditForm({ stepId, factoryId, onClose }: { stepId: string; factoryId: string; onClose: () => void }) {
  const qc = useQueryClient();

  const { data: allSteps } = useQuery({
    queryKey: ['tps-pipeline', factoryId],
    queryFn: () => tpsDashboardApi.getPipeline(factoryId),
    enabled: !!factoryId,
  });

  const step = useMemo(() => {
    const items = allSteps?.items ?? [];
    return items.find((s: ProcessStepItem) => s.id === stepId);
  }, [allSteps, stepId]);

  const [form, setForm] = useState<Partial<ProcessStepCreate>>({});
  const [dirty, setDirty] = useState(false);

  // Sync form when step data loads
  useState(() => {
    if (step) {
      setForm({
        name: step.name,
        stage: step.stage ?? '',
        productivity_rate: step.productivity_rate ?? undefined,
        productivity_unit: step.productivity_unit ?? 'sqm/hour',
        shift_count: step.shift_count,
        auto_calibrate: step.auto_calibrate,
        notes: step.notes ?? '',
        applicable_collections: step.applicable_collections,
        applicable_methods: step.applicable_methods,
      });
    }
  });

  const updateMut = useMutation({
    mutationFn: (data: Partial<ProcessStepCreate>) => tpsDashboardApi.updateStep(stepId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tps-pipeline'] });
      qc.invalidateQueries({ queryKey: ['tps-steps'] });
      setDirty(false);
    },
  });

  if (!step) return null;

  function handleChange(field: string, value: unknown) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setDirty(true);
  }

  return (
    <Card className="border-primary-200 dark:border-gold-700">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Edit: {step.name}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-stone-300">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Input label="Name" value={form.name ?? ''} onChange={(e) => handleChange('name', e.target.value)} />
        <Select
          label="Stage"
          options={[{ value: '', label: '-- Select --' }, ...PRODUCTION_STAGES]}
          value={form.stage ?? ''}
          onChange={(e) => handleChange('stage', e.target.value)}
        />
        <Input
          label="Productivity Rate"
          type="number"
          step="any"
          value={form.productivity_rate ?? ''}
          onChange={(e) => handleChange('productivity_rate', e.target.value ? Number(e.target.value) : undefined)}
        />
        <Select
          label="Unit"
          options={PRODUCTIVITY_UNITS}
          value={form.productivity_unit ?? 'sqm/hour'}
          onChange={(e) => handleChange('productivity_unit', e.target.value)}
        />
        <Input
          label="Shifts"
          type="number"
          min={1}
          max={3}
          value={form.shift_count ?? 1}
          onChange={(e) => handleChange('shift_count', Number(e.target.value))}
        />
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.auto_calibrate ?? false}
              onChange={(e) => handleChange('auto_calibrate', e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            Auto-Calibrate
          </label>
        </div>
        <div className="sm:col-span-2">
          <Input label="Notes" value={form.notes ?? ''} onChange={(e) => handleChange('notes', e.target.value)} />
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={() => updateMut.mutate(form)} disabled={!dirty || updateMut.isPending}>
          {updateMut.isPending ? 'Saving...' : 'Save Changes'}
        </Button>
        <Button size="sm" variant="secondary" onClick={onClose}>Cancel</Button>
      </div>
      {updateMut.isError && <p className="mt-2 text-xs text-red-500">{(updateMut.error as Error).message}</p>}
    </Card>
  );
}


// ── Step create form ────────────────────────────────────────

function StepCreateForm({ factoryId, nextSequence, onClose }: { factoryId: string; nextSequence: number; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<ProcessStepCreate>({ ...EMPTY_STEP, factory_id: factoryId, sequence: nextSequence });

  const createMut = useMutation({
    mutationFn: (data: ProcessStepCreate) => tpsDashboardApi.createStep(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tps-pipeline'] });
      qc.invalidateQueries({ queryKey: ['tps-steps'] });
      onClose();
    },
  });

  function handleChange(field: string, value: unknown) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <Card className="border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/20">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">New Process Step</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-stone-300">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Input label="Name" value={form.name} onChange={(e) => handleChange('name', e.target.value)} />
        <Select
          label="Stage"
          options={[{ value: '', label: '-- Select --' }, ...PRODUCTION_STAGES]}
          value={form.stage ?? ''}
          onChange={(e) => handleChange('stage', e.target.value)}
        />
        <Input
          label="Productivity Rate"
          type="number"
          step="any"
          value={form.productivity_rate ?? ''}
          onChange={(e) => handleChange('productivity_rate', e.target.value ? Number(e.target.value) : undefined)}
        />
        <Select
          label="Unit"
          options={PRODUCTIVITY_UNITS}
          value={form.productivity_unit ?? 'sqm/hour'}
          onChange={(e) => handleChange('productivity_unit', e.target.value)}
        />
        <Input
          label="Shifts"
          type="number"
          min={1}
          max={3}
          value={form.shift_count ?? 1}
          onChange={(e) => handleChange('shift_count', Number(e.target.value))}
        />
        <Input
          label="Sequence"
          type="number"
          min={1}
          value={form.sequence ?? nextSequence}
          onChange={(e) => handleChange('sequence', Number(e.target.value))}
        />
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.auto_calibrate ?? false}
              onChange={(e) => handleChange('auto_calibrate', e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            Auto-Calibrate
          </label>
        </div>
        <Input label="Notes" value={form.notes ?? ''} onChange={(e) => handleChange('notes', e.target.value)} />
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={() => createMut.mutate(form)} disabled={!form.name || createMut.isPending}>
          {createMut.isPending ? 'Creating...' : 'Create Step'}
        </Button>
        <Button size="sm" variant="secondary" onClick={onClose}>Cancel</Button>
      </div>
      {createMut.isError && <p className="mt-2 text-xs text-red-500">{(createMut.error as Error).message}</p>}
    </Card>
  );
}


// ════════════════════════════════════════════════════════════
// TAB 2: Rates Table
// ════════════════════════════════════════════════════════════

function RatesTableTab({ factoryId }: { factoryId: string }) {
  const qc = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<Partial<ProcessStepCreate>>({});

  const { data, isLoading } = useQuery({
    queryKey: ['tps-steps', factoryId],
    queryFn: () => tpsDashboardApi.listSteps(factoryId),
    enabled: !!factoryId,
  });

  // Merge calibration status for drift data
  const { data: calStatus } = useQuery({
    queryKey: ['tps-calibration-status', factoryId],
    queryFn: () => tpsDashboardApi.getCalibrationStatus(factoryId),
    enabled: !!factoryId,
  });

  const calMap = useMemo(() => {
    const map: Record<string, CalibrationStatus> = {};
    (calStatus ?? []).forEach((s) => { map[s.step_id] = s; });
    return map;
  }, [calStatus]);

  const steps: ProcessStepItem[] = useMemo(() => {
    const raw = data?.items ?? [];
    return [...raw].sort((a, b) => a.sequence - b.sequence);
  }, [data]);

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<ProcessStepCreate> }) =>
      tpsDashboardApi.updateStep(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tps-steps'] });
      qc.invalidateQueries({ queryKey: ['tps-pipeline'] });
      setEditingId(null);
    },
  });

  function startEdit(step: ProcessStepItem) {
    setEditingId(step.id);
    setEditData({
      name: step.name,
      stage: step.stage ?? '',
      productivity_rate: step.productivity_rate ?? undefined,
      productivity_unit: step.productivity_unit ?? 'sqm/hour',
      shift_count: step.shift_count,
      auto_calibrate: step.auto_calibrate,
    });
  }

  if (isLoading) {
    return <Card><div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div></Card>;
  }

  return (
    <Card>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs font-medium uppercase text-gray-500 dark:text-stone-400">
              <th className="px-3 py-2">#</th>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Stage</th>
              <th className="px-3 py-2">Rate</th>
              <th className="px-3 py-2">Unit</th>
              <th className="px-3 py-2">Shifts</th>
              <th className="px-3 py-2">Collections</th>
              <th className="px-3 py-2">Methods</th>
              <th className="px-3 py-2">Auto-Cal</th>
              <th className="px-3 py-2">Actual 7d</th>
              <th className="px-3 py-2">Drift</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step) => {
              const cal = calMap[step.id];
              const drift = cal?.drift_percent ?? step.drift_percent;
              const actual7d = cal?.actual_rate_7d ?? step.actual_rate_7d;
              const isEditing = editingId === step.id;

              return (
                <tr key={step.id} className={cn('border-b transition', driftRowBg(drift), 'hover:bg-gray-50 dark:hover:bg-stone-800/50')}>
                  <td className="px-3 py-2 text-xs text-gray-400">{step.sequence}</td>

                  {isEditing ? (
                    <>
                      <td className="px-3 py-2">
                        <input
                          type="text"
                          className="w-32 rounded border px-2 py-1 text-sm dark:bg-stone-800 dark:border-stone-600 dark:text-stone-100"
                          value={editData.name ?? ''}
                          onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                        />
                      </td>
                      <td className="px-3 py-2">
                        <select
                          className="w-28 rounded border px-1 py-1 text-sm dark:bg-stone-800 dark:border-stone-600 dark:text-stone-100"
                          value={editData.stage ?? ''}
                          onChange={(e) => setEditData({ ...editData, stage: e.target.value })}
                        >
                          <option value="">--</option>
                          {PRODUCTION_STAGES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                        </select>
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          step="any"
                          className="w-20 rounded border px-2 py-1 text-sm dark:bg-stone-800 dark:border-stone-600 dark:text-stone-100"
                          value={editData.productivity_rate ?? ''}
                          onChange={(e) => setEditData({ ...editData, productivity_rate: e.target.value ? Number(e.target.value) : undefined })}
                        />
                      </td>
                      <td className="px-3 py-2">
                        <select
                          className="w-24 rounded border px-1 py-1 text-sm dark:bg-stone-800 dark:border-stone-600 dark:text-stone-100"
                          value={editData.productivity_unit ?? ''}
                          onChange={(e) => setEditData({ ...editData, productivity_unit: e.target.value })}
                        >
                          {PRODUCTIVITY_UNITS.map((u) => <option key={u.value} value={u.value}>{u.label}</option>)}
                        </select>
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          min={1}
                          max={3}
                          className="w-14 rounded border px-2 py-1 text-sm dark:bg-stone-800 dark:border-stone-600 dark:text-stone-100"
                          value={editData.shift_count ?? 1}
                          onChange={(e) => setEditData({ ...editData, shift_count: Number(e.target.value) })}
                        />
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-500">{step.applicable_collections.join(', ') || '--'}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">{step.applicable_methods.join(', ') || '--'}</td>
                      <td className="px-3 py-2">
                        <input
                          type="checkbox"
                          checked={editData.auto_calibrate ?? false}
                          onChange={(e) => setEditData({ ...editData, auto_calibrate: e.target.checked })}
                          className="h-4 w-4 rounded border-gray-300"
                        />
                      </td>
                      <td className="px-3 py-2 text-gray-500">{actual7d != null ? actual7d.toFixed(1) : '--'}</td>
                      <td className="px-3 py-2">
                        <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', driftColor(drift))}>
                          {formatDrift(drift)}
                        </span>
                      </td>
                      <td className="px-3 py-2 space-x-1">
                        <Button size="sm" onClick={() => updateMut.mutate({ id: step.id, payload: editData })} disabled={updateMut.isPending}>
                          Save
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => setEditingId(null)}>Cancel</Button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-3 py-2 font-medium text-gray-900 dark:text-gray-100">{step.name}</td>
                      <td className="px-3 py-2 text-gray-600 dark:text-stone-400">{stageLabel(step.stage)}</td>
                      <td className="px-3 py-2 font-medium">{step.productivity_rate ?? '--'}</td>
                      <td className="px-3 py-2 text-gray-500">{unitLabel(step.productivity_unit)}</td>
                      <td className="px-3 py-2">{step.shift_count}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">{step.applicable_collections.join(', ') || '--'}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">{step.applicable_methods.join(', ') || '--'}</td>
                      <td className="px-3 py-2">{step.auto_calibrate ? 'Yes' : 'No'}</td>
                      <td className="px-3 py-2 text-gray-500">{actual7d != null ? actual7d.toFixed(1) : '--'}</td>
                      <td className="px-3 py-2">
                        <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', driftColor(drift))}>
                          {formatDrift(drift)}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <Button size="sm" variant="ghost" onClick={() => startEdit(step)}>Edit</Button>
                      </td>
                    </>
                  )}
                </tr>
              );
            })}
            {steps.length === 0 && (
              <tr>
                <td colSpan={12} className="px-3 py-8 text-center text-gray-400">
                  No process steps configured for this factory.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}


// ════════════════════════════════════════════════════════════
// TAB 3: AI Calibration
// ════════════════════════════════════════════════════════════

function CalibrationTab({ factoryId }: { factoryId: string }) {
  const qc = useQueryClient();
  const [suggestions, setSuggestions] = useState<CalibrationSuggestion[]>([]);

  // Calibration status
  const { data: calStatus, isLoading: loadingStatus } = useQuery({
    queryKey: ['tps-calibration-status', factoryId],
    queryFn: () => tpsDashboardApi.getCalibrationStatus(factoryId),
    enabled: !!factoryId,
  });

  // Calibration log
  const { data: logData, isLoading: loadingLog } = useQuery({
    queryKey: ['tps-calibration-log', factoryId],
    queryFn: () => tpsDashboardApi.getCalibrationLog(factoryId),
    enabled: !!factoryId,
  });

  const logEntries: CalibrationLogEntry[] = useMemo(() => {
    const items = logData?.items ?? [];
    return [...items].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [logData]);

  // Run calibration
  const runMut = useMutation({
    mutationFn: () => tpsDashboardApi.runCalibration(factoryId),
    onSuccess: (data) => {
      setSuggestions(data);
      qc.invalidateQueries({ queryKey: ['tps-calibration-status'] });
    },
  });

  // Apply calibration
  const applyMut = useMutation({
    mutationFn: ({ stepId, newRate }: { stepId: string; newRate: number }) =>
      tpsDashboardApi.applyCalibration(stepId, newRate),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tps-calibration-status'] });
      qc.invalidateQueries({ queryKey: ['tps-calibration-log'] });
      qc.invalidateQueries({ queryKey: ['tps-steps'] });
      qc.invalidateQueries({ queryKey: ['tps-pipeline'] });
    },
  });

  const statusItems: CalibrationStatus[] = calStatus ?? [];

  return (
    <div className="space-y-4">
      {/* Status cards */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Calibration Status</h3>
        <Button
          size="sm"
          onClick={() => runMut.mutate()}
          disabled={runMut.isPending}
        >
          {runMut.isPending ? 'Analyzing...' : 'Run Calibration'}
        </Button>
      </div>

      {loadingStatus ? (
        <div className="flex justify-center py-6"><Spinner className="h-6 w-6" /></div>
      ) : statusItems.length === 0 ? (
        <Card><p className="text-sm text-gray-500">No calibration data available. Ensure process steps are configured and production data is recorded.</p></Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {statusItems.map((item) => (
            <Card key={item.step_id} className="space-y-2">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{item.step_name}</h4>
                  <p className="text-xs text-gray-500 dark:text-stone-400">{stageLabel(item.stage)}</p>
                </div>
                <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', driftColor(item.drift_percent))}>
                  {formatDrift(item.drift_percent)}
                </span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <div>
                  <span className="text-xs text-gray-500">Planned</span>
                  <p className="font-medium text-gray-900 dark:text-gray-100">{item.planned_rate ?? '--'}</p>
                </div>
                <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
                <div>
                  <span className="text-xs text-gray-500">Actual (EMA)</span>
                  <p className="font-medium text-gray-900 dark:text-gray-100">{item.actual_rate_7d != null ? item.actual_rate_7d.toFixed(1) : '--'}</p>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-stone-400">
                <span>{item.data_points} data points</span>
                <span>{item.auto_calibrate ? 'Auto' : 'Manual'}</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Pending suggestions */}
      {suggestions.length > 0 && (
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Calibration Suggestions</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs font-medium uppercase text-gray-500 dark:text-stone-400">
                  <th className="px-3 py-2">Step</th>
                  <th className="px-3 py-2">Stage</th>
                  <th className="px-3 py-2">Current Rate</th>
                  <th className="px-3 py-2">Suggested Rate</th>
                  <th className="px-3 py-2">EMA</th>
                  <th className="px-3 py-2">Drift</th>
                  <th className="px-3 py-2">Points</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {suggestions.filter((s) => !s.applied).map((s) => (
                  <tr key={s.step_id} className="border-b hover:bg-gray-50 dark:hover:bg-stone-800/50">
                    <td className="px-3 py-2 font-medium text-gray-900 dark:text-gray-100">{s.step_name}</td>
                    <td className="px-3 py-2 text-gray-600 dark:text-stone-400">{stageLabel(s.stage)}</td>
                    <td className="px-3 py-2">{s.current_rate}</td>
                    <td className="px-3 py-2 font-semibold text-primary-600 dark:text-gold-400">{s.suggested_rate.toFixed(1)}</td>
                    <td className="px-3 py-2 text-gray-500">{s.ema_value.toFixed(1)}</td>
                    <td className="px-3 py-2">
                      <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', driftColor(s.drift_percent))}>
                        {formatDrift(s.drift_percent)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-500">{s.data_points}</td>
                    <td className="px-3 py-2 space-x-1">
                      <Button
                        size="sm"
                        onClick={() => {
                          applyMut.mutate({ stepId: s.step_id, newRate: s.suggested_rate });
                          setSuggestions((prev) => prev.map((x) => x.step_id === s.step_id ? { ...x, applied: true } : x));
                        }}
                        disabled={applyMut.isPending}
                      >
                        Accept
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setSuggestions((prev) => prev.filter((x) => x.step_id !== s.step_id))}
                      >
                        Reject
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {runMut.isError && (
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/20">
          <p className="text-sm text-red-600">Calibration failed: {(runMut.error as Error).message}</p>
        </Card>
      )}

      {/* Calibration log */}
      <Card>
        <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Calibration Log</h3>
        {loadingLog ? (
          <div className="flex justify-center py-4"><Spinner className="h-6 w-6" /></div>
        ) : logEntries.length === 0 ? (
          <p className="py-4 text-center text-sm text-gray-400">No calibration history yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs font-medium uppercase text-gray-500 dark:text-stone-400">
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Step</th>
                  <th className="px-3 py-2">Previous Rate</th>
                  <th className="px-3 py-2">New Rate</th>
                  <th className="px-3 py-2">EMA</th>
                  <th className="px-3 py-2">Points</th>
                  <th className="px-3 py-2">Trigger</th>
                  <th className="px-3 py-2">Approved By</th>
                </tr>
              </thead>
              <tbody>
                {logEntries.map((entry) => (
                  <tr key={entry.id} className="border-b hover:bg-gray-50 dark:hover:bg-stone-800/50">
                    <td className="px-3 py-2 text-xs text-gray-500 dark:text-stone-400 whitespace-nowrap">
                      {new Date(entry.created_at).toLocaleDateString()}{' '}
                      {new Date(entry.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-3 py-2 font-medium text-gray-900 dark:text-gray-100">{entry.step_name ?? entry.process_step_id.slice(0, 8)}</td>
                    <td className="px-3 py-2">{entry.previous_rate}</td>
                    <td className="px-3 py-2 font-medium">{entry.new_rate}</td>
                    <td className="px-3 py-2 text-gray-500">{entry.ema_value?.toFixed(1) ?? '--'}</td>
                    <td className="px-3 py-2 text-gray-500">{entry.data_points}</td>
                    <td className="px-3 py-2">
                      <span className={cn(
                        'inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize',
                        entry.trigger === 'auto' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700',
                      )}>
                        {entry.trigger}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-500">{entry.approved_by ?? '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
