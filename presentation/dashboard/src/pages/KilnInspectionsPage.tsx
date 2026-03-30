import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useUiStore } from '@/stores/uiStore';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { useKilns } from '@/hooks/useKilns';
import { kilnInspectionsApi, type Inspection, type InspectionItem, type RepairLog } from '@/api/kilnInspections';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Dialog } from '@/components/ui/Dialog';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { FactorySelector } from '@/components/layout/FactorySelector';
import { DatePicker } from '@/components/ui/DatePicker';

const PAGE_TABS = [
  { id: 'inspections', label: 'Inspections' },
  { id: 'repairs', label: 'Repair Log' },
  { id: 'new', label: '+ New Inspection' },
];

const RESULT_OPTIONS = [
  { value: 'ok', label: 'OK', color: 'bg-green-100 text-green-700' },
  { value: 'not_applicable', label: 'N/A', color: 'bg-gray-100 text-gray-500' },
  { value: 'damaged', label: 'Damaged', color: 'bg-red-100 text-red-700' },
  { value: 'needs_repair', label: 'Needs Repair', color: 'bg-orange-100 text-orange-700' },
];

const REPAIR_STATUSES = ['open', 'in_progress', 'done'];

/* ──────────────────────────────────────────────────── */
/*  Main Page                                           */
/* ──────────────────────────────────────────────────── */

export default function KilnInspectionsPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState('inspections');
  const factoryId = useUiStore((s) => s.activeFactoryId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kiln Inspections</h1>
          <p className="mt-1 text-sm text-gray-500">
            Weekly checklists & repair tracking
          </p>
        </div>
        <div className="flex items-center gap-3">
          <FactorySelector />
          <Button variant="secondary" onClick={() => navigate('/manager/kilns')}>
            {'\u2190'} Kilns
          </Button>
        </div>
      </div>

      <Tabs tabs={PAGE_TABS} activeTab={tab} onChange={setTab} />

      {tab === 'inspections' && <InspectionsTab factoryId={factoryId} />}
      {tab === 'repairs' && <RepairsTab factoryId={factoryId} />}
      {tab === 'new' && <NewInspectionForm factoryId={factoryId} onDone={() => setTab('inspections')} />}
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Inspections Tab                                     */
/* ──────────────────────────────────────────────────── */

function InspectionsTab({ factoryId }: { factoryId: string | null }) {
  const qc = useQueryClient();
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const params: Record<string, string> = {};
  if (factoryId) params.factory_id = factoryId;

  const { data, isLoading } = useQuery({
    queryKey: ['kiln-inspections', params],
    queryFn: () => kilnInspectionsApi.listInspections(params),
  });

  const inspections: Inspection[] = data?.items || [];

  const deleteMut = useMutation({
    mutationFn: (id: string) => kilnInspectionsApi.deleteInspection(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kiln-inspections'] });
      setDeleteId(null);
    },
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>;

  if (inspections.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
        <p className="text-lg font-medium text-gray-400">No inspections yet</p>
        <p className="mt-1 text-sm text-gray-400">Create your first kiln inspection using the tab above</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <div className="text-xs text-gray-500">Total Inspections</div>
          <div className="mt-1 text-2xl font-bold">{inspections.length}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Issues Found</div>
          <div className="mt-1 text-2xl font-bold text-red-600">
            {inspections.reduce((s, i) => s + i.summary.issues, 0)}
          </div>
        </Card>
      </div>

      {/* Inspection list */}
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-gray-50 text-xs font-semibold uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Kiln</th>
              <th className="px-4 py-3">Inspector</th>
              <th className="px-4 py-3 text-center">OK</th>
              <th className="px-4 py-3 text-center">Issues</th>
              <th className="px-4 py-3 text-center">N/A</th>
              <th className="px-4 py-3">Notes</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {inspections.map((insp) => (
              <InspectionRow key={insp.id} inspection={insp} onDelete={() => setDeleteId(insp.id)} />
            ))}
          </tbody>
        </table>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Inspection">
        <p className="text-sm text-gray-600">Are you sure you want to delete this inspection? This action will be logged.</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteId(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => deleteId && deleteMut.mutate(deleteId)} disabled={deleteMut.isPending}>
            {deleteMut.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

function InspectionRow({ inspection: i, onDelete }: { inspection: Inspection; onDelete: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const hasIssues = i.summary.issues > 0;

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className={`cursor-pointer hover:bg-gray-50 ${hasIssues ? 'bg-red-50/50' : ''}`}
      >
        <td className="px-4 py-3 font-medium">{i.inspection_date}</td>
        <td className="px-4 py-3">{i.resource_name || '—'}</td>
        <td className="px-4 py-3 text-gray-500">{i.inspected_by_name || '—'}</td>
        <td className="px-4 py-3 text-center">
          <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
            {i.summary.ok}
          </span>
        </td>
        <td className="px-4 py-3 text-center">
          {i.summary.issues > 0 ? (
            <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">
              {i.summary.issues}
            </span>
          ) : (
            <span className="text-gray-300">0</span>
          )}
        </td>
        <td className="px-4 py-3 text-center text-gray-400">{i.summary.not_applicable}</td>
        <td className="px-4 py-3 text-xs text-gray-500 max-w-[200px] truncate">{i.notes || '—'}</td>
        <td className="px-4 py-3 text-right">
          <Button
            variant="ghost"
            size="sm"
            className="text-red-600"
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
          >
            Delete
          </Button>
        </td>
      </tr>

      {/* Expanded detail */}
      {expanded && (
        <tr>
          <td colSpan={8} className="bg-gray-50 px-6 py-4">
            <div className="space-y-3">
              {/* Group results by category */}
              {Object.entries(
                i.results.reduce<Record<string, typeof i.results>>((acc, r) => {
                  const cat = r.category || 'Other';
                  (acc[cat] = acc[cat] || []).push(r);
                  return acc;
                }, {}),
              ).map(([category, results]) => (
                <div key={category}>
                  <h4 className="text-xs font-bold uppercase text-gray-400 mb-1">{category}</h4>
                  <div className="grid gap-1">
                    {results.map((r) => (
                      <div
                        key={r.id}
                        className={`flex items-center gap-3 rounded px-3 py-1.5 text-xs ${
                          r.result === 'ok' ? 'bg-white' :
                          r.result === 'not_applicable' ? 'bg-gray-50' :
                          'bg-red-50'
                        }`}
                      >
                        <ResultBadge result={r.result} />
                        <span className="flex-1 text-gray-700">{r.item_text}</span>
                        {r.notes && <span className="text-gray-400 italic">{r.notes}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function ResultBadge({ result }: { result: string }) {
  const opt = RESULT_OPTIONS.find((o) => o.value === result);
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${opt?.color || 'bg-gray-100 text-gray-600'}`}>
      {opt?.label || result}
    </span>
  );
}

/* ──────────────────────────────────────────────────── */
/*  New Inspection Form                                 */
/* ──────────────────────────────────────────────────── */

function NewInspectionForm({ factoryId, onDone }: { factoryId: string | null; onDone: () => void }) {
  const qc = useQueryClient();
  const user = useCurrentUser();
  const [kilnId, setKilnId] = useState('');
  const [inspDate, setInspDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState('');
  const [results, setResults] = useState<Record<string, { result: string; notes: string }>>({});

  // Load kilns
  const { data: kilnsData } = useKilns(factoryId ? { factory_id: factoryId } : undefined);
  const kilns = kilnsData?.items || [];

  // Load checklist items
  const { data: itemsData, isLoading: itemsLoading } = useQuery({
    queryKey: ['kiln-inspection-items'],
    queryFn: () => kilnInspectionsApi.getItems(),
  });
  const categories: Record<string, InspectionItem[]> = itemsData?.categories || {};

  const createMutation = useMutation({
    mutationFn: (data: Parameters<typeof kilnInspectionsApi.createInspection>[0]) =>
      kilnInspectionsApi.createInspection(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kiln-inspections'] });
      onDone();
    },
  });

  const setResult = (itemId: string, result: string) => {
    setResults((prev) => ({
      ...prev,
      [itemId]: { ...prev[itemId], result, notes: prev[itemId]?.notes || '' },
    }));
  };

  const setItemNotes = (itemId: string, notes: string) => {
    setResults((prev) => ({
      ...prev,
      [itemId]: { ...prev[itemId], result: prev[itemId]?.result || 'ok', notes },
    }));
  };

  const handleSubmit = () => {
    if (!kilnId || !factoryId) return;
    const resultList = Object.entries(results)
      .filter(([, v]) => v.result)
      .map(([itemId, v]) => ({
        item_id: itemId,
        result: v.result,
        notes: v.notes || undefined,
      }));

    createMutation.mutate({
      resource_id: kilnId,
      factory_id: factoryId,
      inspection_date: inspDate,
      results: resultList,
      notes: notes || undefined,
    });
  };

  const allItemIds = Object.values(categories).flat().map((i) => i.id);
  const filledCount = allItemIds.filter((id) => results[id]?.result).length;

  if (!factoryId) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
        <p className="text-gray-400">Select a factory first</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Form header */}
      <Card className="p-5">
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Kiln</label>
            <select
              value={kilnId}
              onChange={(e) => setKilnId(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select kiln...</option>
              {kilns.map((k) => (
                <option key={k.id} value={k.id}>{k.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Inspection Date</label>
            <DatePicker
              value={inspDate}
              onChange={(v) => setInspDate(v)}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Inspector</label>
            <input
              type="text"
              value={user?.name || user?.email || ''}
              readOnly
              className="w-full rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500"
            />
          </div>
        </div>
        <div className="mt-3">
          <label className="block text-xs font-medium text-gray-500 mb-1">Notes (optional)</label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="General notes about this inspection..."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
      </Card>

      {/* Progress */}
      <div className="flex items-center gap-3">
        <div className="h-2 flex-1 rounded-full bg-gray-200 overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-[width] duration-200"
            style={{ width: `${allItemIds.length > 0 ? (filledCount / allItemIds.length) * 100 : 0}%` }}
          />
        </div>
        <span className="text-xs font-medium text-gray-500">
          {filledCount} / {allItemIds.length} items
        </span>
      </div>

      {/* Checklist items by category */}
      {itemsLoading ? (
        <div className="flex justify-center py-8"><Spinner className="h-6 w-6" /></div>
      ) : (
        <div className="space-y-4">
          {Object.entries(categories).map(([category, items]) => (
            <Card key={category} className="overflow-hidden">
              <div className="bg-gray-50 px-4 py-2.5 border-b">
                <h3 className="text-sm font-bold text-gray-700">{category}</h3>
              </div>
              <div className="divide-y">
                {items.map((item) => {
                  const current = results[item.id]?.result || '';
                  return (
                    <div key={item.id} className={`flex items-center gap-3 px-4 py-2.5 ${
                      current === 'damaged' || current === 'needs_repair' ? 'bg-red-50/50' : ''
                    }`}>
                      <span className="flex-1 text-sm text-gray-700">{item.item_text}</span>
                      <div className="flex gap-1">
                        {RESULT_OPTIONS.map((opt) => (
                          <button
                            key={opt.value}
                            onClick={() => setResult(item.id, opt.value)}
                            className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-all ${
                              current === opt.value
                                ? `${opt.color} ring-2 ring-offset-1 ring-current`
                                : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                            }`}
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                      {(current === 'damaged' || current === 'needs_repair') && (
                        <input
                          type="text"
                          placeholder="Details..."
                          value={results[item.id]?.notes || ''}
                          onChange={(e) => setItemNotes(item.id, e.target.value)}
                          className="ml-2 w-40 rounded border border-red-200 px-2 py-1 text-xs"
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Submit */}
      <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-3">
        <span className="text-sm text-gray-500">
          {filledCount === allItemIds.length ? (
            <span className="font-medium text-green-600">{'\u2705'} All items checked</span>
          ) : (
            `${allItemIds.length - filledCount} items remaining`
          )}
        </span>
        <Button
          onClick={handleSubmit}
          disabled={!kilnId || filledCount === 0 || createMutation.isPending}
        >
          {createMutation.isPending ? <Spinner className="h-4 w-4 mr-2" /> : null}
          Save Inspection
        </Button>
      </div>

      {createMutation.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {(createMutation.error as any)?.response?.data?.detail || 'Failed to save inspection'}
        </div>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Repairs Tab                                         */
/* ──────────────────────────────────────────────────── */

function RepairsTab({ factoryId }: { factoryId: string | null }) {
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [deleteRepairId, setDeleteRepairId] = useState<string | null>(null);

  const params: Record<string, string> = {};
  if (factoryId) params.factory_id = factoryId;

  const { data, isLoading } = useQuery({
    queryKey: ['kiln-repairs', params],
    queryFn: () => kilnInspectionsApi.listRepairs(params),
  });

  const repairs: RepairLog[] = data?.items || [];

  const updateMutation = useMutation({
    mutationFn: ({ id, data: d }: { id: string; data: Record<string, unknown> }) =>
      kilnInspectionsApi.updateRepair(id, d),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kiln-repairs'] }),
  });

  const deleteRepairMut = useMutation({
    mutationFn: (id: string) => kilnInspectionsApi.deleteRepair(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kiln-repairs'] });
      setDeleteRepairId(null);
    },
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setShowNew(!showNew)}>
          {showNew ? 'Cancel' : '+ New Repair Entry'}
        </Button>
      </div>

      {showNew && (
        <NewRepairForm factoryId={factoryId} onDone={() => setShowNew(false)} />
      )}

      {/* Repair log table */}
      {repairs.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-lg font-medium text-gray-400">No repair logs yet</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Kiln</th>
                <th className="px-4 py-3">Issue</th>
                <th className="px-4 py-3">Reported By</th>
                <th className="px-4 py-3">Diagnosis</th>
                <th className="px-4 py-3">Repair Actions</th>
                <th className="px-4 py-3">Spare Parts</th>
                <th className="px-4 py-3">Technician</th>
                <th className="px-4 py-3">Completed</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {repairs.map((r) => (
                <tr key={r.id} className={r.status === 'open' ? 'bg-yellow-50/50' : r.status === 'in_progress' ? 'bg-blue-50/30' : ''}>
                  <td className="px-4 py-3 whitespace-nowrap">{r.date_reported}</td>
                  <td className="px-4 py-3 font-medium">{r.resource_name}</td>
                  <td className="px-4 py-3 max-w-[200px]">{r.issue_description}</td>
                  <td className="px-4 py-3 text-gray-500">{r.reported_by_name}</td>
                  <td className="px-4 py-3 text-gray-500 max-w-[150px]">{r.diagnosis || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 max-w-[150px]">{r.repair_actions || '—'}</td>
                  <td className="px-4 py-3 text-gray-500">{r.spare_parts_used || '—'}</td>
                  <td className="px-4 py-3">{r.technician || '—'}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{r.date_completed || '—'}</td>
                  <td className="px-4 py-3">
                    <select
                      value={r.status}
                      onChange={(e) => updateMutation.mutate({ id: r.id, data: { status: e.target.value } })}
                      className={`rounded-md border px-2 py-1 text-xs font-medium ${
                        r.status === 'done' ? 'border-green-200 bg-green-50 text-green-700' :
                        r.status === 'in_progress' ? 'border-blue-200 bg-blue-50 text-blue-700' :
                        'border-orange-200 bg-orange-50 text-orange-700'
                      }`}
                    >
                      {REPAIR_STATUSES.map((s) => (
                        <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600"
                      onClick={() => setDeleteRepairId(r.id)}
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Repair Confirmation Dialog */}
      <Dialog open={!!deleteRepairId} onClose={() => setDeleteRepairId(null)} title="Delete Repair Log">
        <p className="text-sm text-gray-600">Are you sure you want to delete this repair log entry? This action will be logged.</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteRepairId(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => deleteRepairId && deleteRepairMut.mutate(deleteRepairId)} disabled={deleteRepairMut.isPending}>
            {deleteRepairMut.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

function NewRepairForm({ factoryId, onDone }: { factoryId: string | null; onDone: () => void }) {
  const qc = useQueryClient();
  const [kilnId, setKilnId] = useState('');
  const [issue, setIssue] = useState('');
  const [technician, setTechnician] = useState('');
  const [notes, setNotes] = useState('');

  const { data: kilnsData } = useKilns(factoryId ? { factory_id: factoryId } : undefined);
  const kilns = kilnsData?.items || [];

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => kilnInspectionsApi.createRepair(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kiln-repairs'] });
      onDone();
    },
  });

  return (
    <Card className="p-5 border-blue-200 bg-blue-50/30">
      <h3 className="text-sm font-bold text-gray-700 mb-3">New Repair Entry</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Kiln *</label>
          <select
            value={kilnId}
            onChange={(e) => setKilnId(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">Select kiln...</option>
            {kilns.map((k) => (
              <option key={k.id} value={k.id}>{k.name}</option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="block text-xs font-medium text-gray-500 mb-1">Issue Description *</label>
          <input
            type="text"
            value={issue}
            onChange={(e) => setIssue(e.target.value)}
            placeholder="e.g. Broken hinge on door"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Technician</label>
          <input
            type="text"
            value={technician}
            onChange={(e) => setTechnician(e.target.value)}
            placeholder="Name"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
      </div>
      <div className="mt-3">
        <label className="block text-xs font-medium text-gray-500 mb-1">Notes</label>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
      </div>
      <div className="mt-3 flex gap-2">
        <Button
          onClick={() => {
            if (!kilnId || !issue || !factoryId) return;
            createMutation.mutate({
              resource_id: kilnId,
              factory_id: factoryId,
              issue_description: issue,
              technician: technician || undefined,
              notes: notes || undefined,
            });
          }}
          disabled={!kilnId || !issue || createMutation.isPending}
        >
          {createMutation.isPending ? <Spinner className="h-4 w-4 mr-2" /> : null}
          Create
        </Button>
        <Button variant="ghost" onClick={onDone}>Cancel</Button>
      </div>
    </Card>
  );
}
