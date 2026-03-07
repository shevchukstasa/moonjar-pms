import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { useUiStore } from '@/stores/uiStore';
import { usePositionsForQc, useQualityStats, useCreateInspection, type QcPositionItem } from '@/hooks/useQuality';
import { useQmBlocks, useResolveQmBlock, type QmBlockItem } from '@/hooks/useQmBlocks';
import { useProblemCards, useCreateProblemCard, useUpdateProblemCard, type ProblemCardItem } from '@/hooks/useProblemCards';
import apiClient from '@/api/client';

interface DefectCause { id: string; code: string; description: string }

const TABS = [
  { id: 'queue', label: 'QC Queue' },
  { id: 'blocks', label: 'QM Blocks' },
  { id: 'cards', label: 'Problem Cards' },
];

export default function QualityManagerDashboard() {
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);
  const [tab, setTab] = useState('queue');

  const { data: qcData, isLoading: qcLoading } = usePositionsForQc(activeFactoryId || undefined);
  const qcPositions = qcData?.items || [];
  const { data: stats } = useQualityStats(activeFactoryId || undefined);
  const { data: blocksData, isLoading: blocksLoading } = useQmBlocks(activeFactoryId || undefined);
  const blocks = blocksData?.items || [];
  const { data: cardsData, isLoading: cardsLoading } = useProblemCards(activeFactoryId || undefined);
  const problemCards = cardsData?.items || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Quality Manager</h1>
        <p className="mt-1 text-sm text-gray-500">Inspections, defects, problem cards</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="text-center">
          <p className="text-2xl font-bold text-orange-600">{stats?.pending_qc ?? 0}</p>
          <p className="text-xs text-gray-500">Pending QC</p>
        </Card>
        <Card className="text-center">
          <p className="text-2xl font-bold text-red-600">{stats?.blocked ?? 0}</p>
          <p className="text-xs text-gray-500">Blocked</p>
        </Card>
        <Card className="text-center">
          <p className="text-2xl font-bold text-yellow-600">{stats?.open_problem_cards ?? 0}</p>
          <p className="text-xs text-gray-500">Problem Cards</p>
        </Card>
        <Card className="text-center">
          <p className="text-2xl font-bold text-green-600">{stats?.inspections_today ?? 0}</p>
          <p className="text-xs text-gray-500">Today's Checks</p>
        </Card>
      </div>

      <Tabs tabs={TABS} activeTab={tab} onChange={setTab} />

      {tab === 'queue' && <QcQueueTab positions={qcPositions} isLoading={qcLoading} />}
      {tab === 'blocks' && <QmBlocksTab blocks={blocks} isLoading={blocksLoading} />}
      {tab === 'cards' && (
        <ProblemCardsTab cards={problemCards} isLoading={cardsLoading} activeFactoryId={activeFactoryId} />
      )}
    </div>
  );
}

/* ---------- QC QUEUE TAB ---------- */

function QcQueueTab({ positions, isLoading }: { positions: QcPositionItem[]; isLoading: boolean }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = positions.find((p) => p.id === selectedId) || null;

  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  }
  if (positions.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No positions awaiting quality check</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
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
            <p className="mt-1 text-sm text-gray-600">{p.color} · {p.size}</p>
            <p className="mt-0.5 text-lg font-bold text-gray-900">{p.quantity} pcs</p>
          </button>
        ))}
      </div>

      {selected && <InspectionForm position={selected} onDone={() => setSelectedId(null)} />}
    </div>
  );
}

/* ---- Inspection Form ---- */

function InspectionForm({ position, onDone }: { position: QcPositionItem; onDone: () => void }) {
  const createInspection = useCreateInspection();
  const [result, setResult] = useState<'ok' | 'defect' | null>(null);
  const [defectCauseId, setDefectCauseId] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');

  const { data: defectCausesData } = useQuery<{ items: DefectCause[] }>({
    queryKey: ['defect-causes'],
    queryFn: () => apiClient.get('/defects').then((r) => r.data),
  });
  const defectCauses = defectCausesData?.items || [];
  const isValid = result !== null && (result === 'ok' || defectCauseId !== '');

  const handleSubmit = async () => {
    if (!result) return;
    setError('');
    try {
      await createInspection.mutateAsync({
        position_id: position.id,
        factory_id: position.factory_id,
        stage: 'sorting',
        result,
        defect_cause_id: result === 'defect' ? defectCauseId : undefined,
        notes: notes || undefined,
      });
      onDone();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setError(resp?.detail || 'Failed to submit inspection');
    }
  };

  return (
    <Card className="border-primary-200 bg-primary-50/30">
      <div className="mb-4 flex items-center gap-3 rounded-md bg-white p-3">
        <div className="flex-1 text-sm">
          <span className="font-semibold">{position.order_number}</span>
          <span className="mx-2 text-gray-300">·</span>
          <span className="text-gray-600">{position.color}</span>
          <span className="mx-2 text-gray-300">·</span>
          <span className="text-gray-600">{position.size}</span>
        </div>
        <span className="text-lg font-bold">{position.quantity} pcs</span>
      </div>

      {/* Result buttons */}
      <div className="flex gap-3">
        {(['ok', 'defect'] as const).map((r) => (
          <button key={r} type="button" onClick={() => setResult(r)} className={`flex-1 rounded-md border-2 px-4 py-3 text-sm font-semibold transition-colors ${
            result === r
              ? r === 'ok' ? 'border-green-500 bg-green-50 text-green-700' : 'border-red-500 bg-red-50 text-red-700'
              : r === 'ok' ? 'border-gray-300 text-gray-600 hover:border-green-300' : 'border-gray-300 text-gray-600 hover:border-red-300'
          }`}>
            {r === 'ok' ? 'OK' : 'Defect'}
          </button>
        ))}
      </div>

      {/* Defect cause selector */}
      {result === 'defect' && (
        <select
          value={defectCauseId}
          onChange={(e) => setDefectCauseId(e.target.value)}
          className="mt-3 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
        >
          <option value="">Select defect cause...</option>
          {defectCauses.map((dc) => (
            <option key={dc.id} value={dc.id}>{dc.code} — {dc.description}</option>
          ))}
        </select>
      )}

      <textarea
        placeholder="Notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        className="mt-3 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
        rows={2}
      />

      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}

      <Button
        className="mt-4 w-full"
        onClick={handleSubmit}
        disabled={!isValid || createInspection.isPending}
      >
        {createInspection.isPending ? 'Submitting...' : 'Submit Inspection'}
      </Button>
    </Card>
  );
}

/* ---------- QM BLOCKS TAB ---------- */

function QmBlocksTab({ blocks, isLoading }: { blocks: QmBlockItem[]; isLoading: boolean }) {
  const resolveMutation = useResolveQmBlock();
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [resolutionNote, setResolutionNote] = useState('');
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const activeBlocks = blocks.filter((b) => b.resolved_at === null);

  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  }
  if (activeBlocks.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <p className="text-gray-400">No active blocks</p>
      </div>
    );
  }

  const handleResolve = async (id: string) => {
    await resolveMutation.mutateAsync({
      id,
      data: { resolved_by: '', resolved_at: new Date().toISOString(), resolution_note: resolutionNote },
    });
    setResolvingId(null);
    setResolutionNote('');
  };

  const SEV: Record<string, string> = { critical: 'bg-red-100 text-red-700', high: 'bg-orange-100 text-orange-700', medium: 'bg-yellow-100 text-yellow-700', low: 'bg-gray-100 text-gray-700' };

  return (
    <>
      <div className="space-y-3">
        {activeBlocks.map((b) => (
          <div key={b.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">{b.reason}</span>
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${SEV[b.severity] || SEV.low}`}>
                    {b.severity}
                  </span>
                </div>
                <p className="mt-0.5 text-sm text-gray-500">
                  {b.block_type.replace(/_/g, ' ')} · {new Date(b.created_at).toLocaleDateString()}
                </p>
              </div>
              {resolvingId !== b.id && (
                <Button size="sm" onClick={() => { setResolvingId(b.id); setResolutionNote(''); }} disabled={resolveMutation.isPending}>
                  Resolve
                </Button>
              )}
            </div>
            {resolvingId === b.id && (
              <div className="mt-3 space-y-2">
                <textarea
                  placeholder="Resolution note..."
                  value={resolutionNote}
                  onChange={(e) => setResolutionNote(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  rows={2}
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => setConfirmId(b.id)} disabled={resolveMutation.isPending || !resolutionNote.trim()}>
                    {resolveMutation.isPending ? 'Resolving...' : 'Confirm'}
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => { setResolvingId(null); setResolutionNote(''); }}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      <ConfirmDialog
        open={!!confirmId}
        onClose={() => setConfirmId(null)}
        onConfirm={() => confirmId && handleResolve(confirmId)}
        title="Resolve Block"
        message="Mark this block as resolved? This action cannot be undone."
      />
    </>
  );
}

/* ---------- PROBLEM CARDS TAB ---------- */

function ProblemCardsTab({
  cards, isLoading, activeFactoryId,
}: {
  cards: ProblemCardItem[]; isLoading: boolean; activeFactoryId: string | null;
}) {
  const createMutation = useCreateProblemCard();
  const updateMutation = useUpdateProblemCard();
  const [showForm, setShowForm] = useState(false);
  const [location, setLocation] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [confirmCloseId, setConfirmCloseId] = useState<string | null>(null);

  const SC: Record<string, string> = { open: 'bg-yellow-100 text-yellow-700', in_progress: 'bg-blue-100 text-blue-700', resolved: 'bg-green-100 text-green-700', closed: 'bg-gray-100 text-gray-600' };

  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>;
  }

  const handleCreate = async () => {
    if (!description.trim()) return;
    setError('');
    try {
      await createMutation.mutateAsync({
        factory_id: activeFactoryId || '',
        location: location || undefined,
        description,
      });
      setShowForm(false);
      setLocation('');
      setDescription('');
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setError(resp?.detail || 'Failed to create problem card');
    }
  };

  const handleClose = async (id: string) => {
    await updateMutation.mutateAsync({ id, data: { status: 'closed' } });
  };

  return (
    <>
      <div className="space-y-4">
        {/* New Problem Card button / inline form */}
        {!showForm ? (
          <Button onClick={() => setShowForm(true)}>New Problem Card</Button>
        ) : (
          <Card className="border-primary-200 bg-primary-50/30">
            <input
              type="text"
              placeholder="Location (optional)"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
            <textarea
              placeholder="Description..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-2 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              rows={3}
            />
            {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
            <div className="mt-3 flex gap-2">
              <Button onClick={handleCreate} disabled={!description.trim() || createMutation.isPending}>
                {createMutation.isPending ? 'Creating...' : 'Submit'}
              </Button>
              <Button variant="secondary" onClick={() => { setShowForm(false); setLocation(''); setDescription(''); setError(''); }}>
                Cancel
              </Button>
            </div>
          </Card>
        )}

        {/* Cards list */}
        {cards.length === 0 ? (
          <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
            <p className="text-gray-400">No problem cards</p>
          </div>
        ) : (
          <div className="space-y-3">
            {cards.map((c) => (
              <div key={c.id} className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">{c.description}</span>
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${SC[c.status] || SC.closed}`}>
                      {c.status.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <p className="mt-0.5 text-sm text-gray-500">
                    {c.location ? `${c.location} · ` : ''}{new Date(c.created_at).toLocaleDateString()}
                  </p>
                </div>
                {(c.status === 'open' || c.status === 'in_progress') && (
                  <Button size="sm" variant="secondary" onClick={() => setConfirmCloseId(c.id)} disabled={updateMutation.isPending}>
                    Close
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      <ConfirmDialog
        open={!!confirmCloseId}
        onClose={() => setConfirmCloseId(null)}
        onConfirm={() => confirmCloseId && handleClose(confirmCloseId)}
        title="Close Problem Card"
        message="Close this problem card? It will be marked as resolved."
      />
    </>
  );
}
