import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Trash2, Thermometer, ClipboardCheck, Calendar, AlertTriangle, RefreshCw } from 'lucide-react';
import { useUiStore } from '@/stores/uiStore';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { useGlazingSchedule, useFiringSchedule, useSortingSchedule, useQcSchedule, useKilnSchedule, useAutoFormBatches } from '@/hooks/useSchedule';
import { Badge } from '@/components/ui/Badge';
import { StatusDropdown } from '@/components/tablo/StatusDropdown';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Tabs } from '@/components/ui/Tabs';
import { Spinner } from '@/components/ui/Spinner';
import { DataTable } from '@/components/ui/Table';
import { FactorySelector } from '@/components/layout/FactorySelector';
import apiClient from '@/api/client';
import { formatEdgeProfile, formatShape } from '@/components/tablo/PositionRow';
import { QualityCheckDialog } from '@/components/quality/QualityCheckDialog';

const SECTION_TABS = [
  { id: 'glazing', label: 'Glazing' },
  { id: 'firing', label: 'Firing' },
  { id: 'sorting', label: 'Sorting' },
  { id: 'qc', label: 'QC' },
  { id: 'kilns', label: 'Kilns' },
];

export default function ManagerSchedulePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);
  const currentUser = useCurrentUser();
  const [tab, setTab] = useState('glazing');
  const [canDeletePositions, setCanDeletePositions] = useState(false);
  // Map factory_id → whether cleanup is allowed (used when "All Factories" selected)
  const [deleteFactoryMap, setDeleteFactoryMap] = useState<Record<string, boolean>>({});
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // QC Check dialog state
  const [qcOpen, setQcOpen] = useState(false);
  const [qcPositionId, setQcPositionId] = useState('');
  const [qcFactoryId, setQcFactoryId] = useState('');
  const [qcCheckType, setQcCheckType] = useState<'pre_kiln' | 'final'>('pre_kiln');
  const [qcPositionLabel, setQcPositionLabel] = useState('');

  const { data: glazingData, isLoading: glazingLoading, isError: glazingError } = useGlazingSchedule(activeFactoryId);
  const { data: firingData, isLoading: firingLoading, isError: firingError } = useFiringSchedule(activeFactoryId);
  const { data: sortingData, isLoading: sortingLoading, isError: sortingError } = useSortingSchedule(activeFactoryId);
  const { data: qcData, isLoading: qcLoading, isError: qcError } = useQcSchedule(activeFactoryId);
  const { data: kilnData, isLoading: kilnLoading, isError: kilnError } = useKilnSchedule(activeFactoryId);
  const hasError = glazingError || firingError || sortingError || qcError || kilnError;

  const autoFormMutation = useAutoFormBatches();
  const [autoFormResult, setAutoFormResult] = useState<string | null>(null);
  const [rescheduling, setRescheduling] = useState(false);
  const [rescheduleResult, setRescheduleResult] = useState<string | null>(null);

  // Firing log state
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [firingLogBatch, setFiringLogBatch] = useState<any | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [firingLogData, setFiringLogData] = useState<any | null>(null);
  const [firingLogLoading, setFiringLogLoading] = useState(false);
  const [tempInput, setTempInput] = useState('');
  const [tempNotes, setTempNotes] = useState('');
  const [firingLogSaving, setFiringLogSaving] = useState(false);

  const openFiringLog = useCallback(async (batch: { id: string; kiln_id?: string }) => {
    setFiringLogBatch(batch);
    setFiringLogLoading(true);
    try {
      const res = await apiClient.get(`/batches/${batch.id}/firing-log`);
      const logs = res.data?.items || [];
      // Use the latest active log, or null
      setFiringLogData(logs.length > 0 ? logs[0] : null);
    } catch {
      setFiringLogData(null);
    } finally {
      setFiringLogLoading(false);
    }
  }, []);

  const startFiringLog = useCallback(async () => {
    if (!firingLogBatch) return;
    setFiringLogSaving(true);
    try {
      const res = await apiClient.post(`/batches/${firingLogBatch.id}/firing-log`, {});
      setFiringLogData(res.data);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to start firing log';
      alert(msg);
    } finally {
      setFiringLogSaving(false);
    }
  }, [firingLogBatch]);

  const addReading = useCallback(async () => {
    if (!firingLogBatch || !firingLogData || !tempInput) return;
    const temp = parseFloat(tempInput);
    if (isNaN(temp)) return;
    setFiringLogSaving(true);
    try {
      const res = await apiClient.post(
        `/batches/${firingLogBatch.id}/firing-log/${firingLogData.id}/reading`,
        { temp, notes: tempNotes || undefined },
      );
      setFiringLogData(res.data);
      setTempInput('');
      setTempNotes('');
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to add reading';
      alert(msg);
    } finally {
      setFiringLogSaving(false);
    }
  }, [firingLogBatch, firingLogData, tempInput, tempNotes]);

  const endFiring = useCallback(async (result: string) => {
    if (!firingLogBatch || !firingLogData) return;
    if (!window.confirm(`End firing with result: ${result}?`)) return;
    setFiringLogSaving(true);
    try {
      const res = await apiClient.patch(
        `/batches/${firingLogBatch.id}/firing-log/${firingLogData.id}`,
        { ended_at: new Date().toISOString(), result },
      );
      setFiringLogData(res.data);
      queryClient.invalidateQueries({ queryKey: ['schedule'] });
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to end firing';
      alert(msg);
    } finally {
      setFiringLogSaving(false);
    }
  }, [firingLogBatch, firingLogData, queryClient]);

  const handleAutoFormBatches = useCallback(async () => {
    if (!activeFactoryId) {
      alert('Please select a specific factory first.');
      return;
    }
    if (!window.confirm('Auto-form kiln batches from ready positions?')) return;
    setAutoFormResult(null);
    try {
      const result = await autoFormMutation.mutateAsync({ factory_id: activeFactoryId });
      if (result.batches_created === 0) {
        setAutoFormResult('No batches formed — no kiln-ready positions found.');
      } else {
        setAutoFormResult(
          `Formed ${result.batches_created} batch${result.batches_created > 1 ? 'es' : ''} with ${result.positions_assigned} position${result.positions_assigned > 1 ? 's' : ''}.`
        );
      }
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Auto-form failed';
      setAutoFormResult(`Error: ${msg}`);
    }
  }, [activeFactoryId, autoFormMutation]);

  // Fetch PM cleanup permissions — works for a single factory or "All Factories"
  useEffect(() => {
    if (activeFactoryId) {
      // Single factory selected
      apiClient.get('/cleanup/permissions', { params: { factory_id: activeFactoryId } })
        .then((r) => {
          const allowed = r.data.pm_can_delete_positions;
          setCanDeletePositions(allowed);
          setDeleteFactoryMap({ [activeFactoryId]: allowed });
        })
        .catch(() => {
          setCanDeletePositions(false);
          setDeleteFactoryMap({});
        });
    } else {
      // "All Factories" — fetch permissions for every factory the user belongs to
      const userFactories = currentUser?.factories ?? [];
      if (userFactories.length === 0) {
        setCanDeletePositions(false);
        setDeleteFactoryMap({});
        return;
      }
      Promise.all(
        userFactories.map((f) =>
          apiClient.get('/cleanup/permissions', { params: { factory_id: f.id } })
            .then((r) => ({ id: f.id, allowed: r.data.pm_can_delete_positions as boolean }))
            .catch(() => ({ id: f.id, allowed: false }))
        )
      ).then((results) => {
        const map: Record<string, boolean> = {};
        let anyAllowed = false;
        for (const r of results) {
          map[r.id] = r.allowed;
          if (r.allowed) anyAllowed = true;
        }
        setCanDeletePositions(anyAllowed);
        setDeleteFactoryMap(map);
      });
    }
  }, [activeFactoryId, currentUser]);

  const handleDeletePosition = useCallback(async (positionId: string, positionFactoryId?: string) => {
    // Determine which factory_id to use for the delete call
    const factoryId = activeFactoryId || positionFactoryId;
    if (!factoryId) {
      alert('Cannot determine factory for this position. Select a specific factory.');
      return;
    }
    if (!window.confirm('Delete this position and all its linked tasks? This cannot be undone.')) return;
    setDeletingId(positionId);
    try {
      await apiClient.delete(`/cleanup/positions/${positionId}`, {
        params: { factory_id: factoryId },
      });
      // Refresh all schedule tabs
      queryClient.invalidateQueries({ queryKey: ['schedule'] });
      queryClient.invalidateQueries({ queryKey: ['glazing-schedule'] });
      queryClient.invalidateQueries({ queryKey: ['firing-schedule'] });
      queryClient.invalidateQueries({ queryKey: ['sorting-schedule'] });
      queryClient.invalidateQueries({ queryKey: ['qc-schedule'] });
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Delete failed';
      alert(msg);
    } finally {
      setDeletingId(null);
    }
  }, [activeFactoryId, queryClient]);

  const isLoading =
    (tab === 'glazing' && glazingLoading) ||
    (tab === 'firing' && firingLoading) ||
    (tab === 'sorting' && sortingLoading) ||
    (tab === 'qc' && qcLoading) ||
    (tab === 'kilns' && kilnLoading);

  const sectionItems: Record<string, unknown[]> = {
    glazing: glazingData?.items || [],
    firing: firingData?.items || [],
    sorting: sortingData?.items || [],
    qc: qcData?.items || [],
  };

  const kilns = kilnData?.items || [];

  // Date field mapping per section tab
  const DATE_FIELD_MAP: Record<string, string> = {
    glazing: 'planned_glazing_date',
    firing: 'planned_kiln_date',
    sorting: 'planned_sorting_date',
    qc: 'planned_completion_date',
  };

  // Group positions by their planned date for the active section
  const groupedByDate = useMemo(() => {
    const items = (sectionItems[tab] || []) as Record<string, unknown>[];
    const dateField = DATE_FIELD_MAP[tab];
    if (!dateField || items.length === 0) return [];

    const groups = new Map<string, Record<string, unknown>[]>();
    for (const item of items) {
      const dateVal = (item[dateField] as string) || 'Unscheduled';
      if (!groups.has(dateVal)) groups.set(dateVal, []);
      groups.get(dateVal)!.push(item);
    }
    // Sort groups: real dates first (ascending), "Unscheduled" last
    return Array.from(groups.entries()).sort(([a], [b]) => {
      if (a === 'Unscheduled') return 1;
      if (b === 'Unscheduled') return -1;
      return a.localeCompare(b);
    });
  }, [tab, sectionItems]);

  // Count overdue positions across all sections
  const overdueCount = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    let count = 0;
    for (const [dateKey, positions] of groupedByDate) {
      if (dateKey !== 'Unscheduled' && dateKey < today) {
        count += positions.length;
      }
    }
    return count;
  }, [groupedByDate]);

  const handleRescheduleOverdue = useCallback(async () => {
    if (!activeFactoryId) {
      alert('Please select a specific factory first.');
      return;
    }
    if (!window.confirm(`Reschedule ${overdueCount} overdue position(s) forward from today?`)) return;
    setRescheduling(true);
    setRescheduleResult(null);
    try {
      const res = await apiClient.post(`/schedule/factory/${activeFactoryId}/reschedule`);
      const count = res.data?.positions_rescheduled ?? 0;
      setRescheduleResult(`${count} position(s) rescheduled successfully.`);
      queryClient.invalidateQueries({ queryKey: ['schedule'] });
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Reschedule failed';
      setRescheduleResult(`Error: ${msg}`);
    } finally {
      setRescheduling(false);
    }
  }, [activeFactoryId, overdueCount, queryClient]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const positionColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    { key: 'order_number', header: 'Order' },
    {
      key: 'position_label',
      header: '#',
      render: (item) => (
        <span className="font-mono text-xs font-semibold text-gray-700">
          {item.position_label ?? (item.position_number != null ? `#${item.position_number}` : '—')}
        </span>
      ),
    },
    { key: 'color', header: 'Color' },
    { key: 'size', header: 'Size' },
    {
      key: 'thickness_mm',
      header: 'Thickness',
      render: (item) => item.thickness_mm ? `${item.thickness_mm} mm` : '10 mm',
    },
    {
      key: 'shape',
      header: 'Shape',
      render: (item) => formatShape(item.shape, item.width_cm, item.length_cm),
    },
    {
      key: 'place_of_application',
      header: 'Glaze Place',
      render: (item) => {
        const labels: Record<string, string> = {
          face_only: 'Face',
          edges_1: 'Face + 1 edge',
          edges_2: 'Face + 2 edges',
          all_edges: 'Face + all edges',
          with_back: 'All surfaces',
        };
        return item.place_of_application ? (labels[item.place_of_application] ?? item.place_of_application) : labels['face_only'];
      },
    },
    {
      key: 'edge_profile',
      header: 'Edge',
      render: (item) => {
        const edge = formatEdgeProfile(item.edge_profile, item.edge_profile_sides);
        const isNonDefault = item.edge_profile && item.edge_profile !== 'straight';
        return isNonDefault ? (
          <span className="inline-flex items-center rounded bg-orange-50 px-1.5 py-0.5 text-[10px] font-medium text-orange-700">
            {edge}
          </span>
        ) : edge;
      },
    },
    {
      key: 'application',
      header: 'Application',
      render: (item) => item.application ?? '—',
    },
    {
      key: 'collection',
      header: 'Collection',
      render: (item) => item.collection ?? '—',
    },
    { key: 'quantity', header: 'Qty' },
    {
      key: 'status',
      header: 'Status',
      render: (item) => (
        <StatusDropdown positionId={item.id} currentStatus={item.status} section={tab} />
      ),
    },
    { key: 'product_type', header: 'Type' },
    {
      key: 'priority_order',
      header: 'Priority',
      render: (item) => item.priority_order != null ? item.priority_order : '\u2014',
    },
    // Delete column — only shown when PM cleanup is enabled
    ...(canDeletePositions ? [{
      key: '_delete',
      header: '',
      render: (item: { id: string; factory_id?: string }) => {
        // When "All Factories" mode, check per-factory permission
        const itemFactoryId = item.factory_id;
        if (!activeFactoryId && itemFactoryId && !deleteFactoryMap[itemFactoryId]) {
          return null; // This factory doesn't allow cleanup
        }
        return (
          <button
            onClick={(e) => { e.stopPropagation(); handleDeletePosition(item.id, itemFactoryId); }}
            disabled={deletingId === item.id}
            className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
            title="Delete position"
          >
            {deletingId === item.id
              ? <span className="text-xs">...</span>
              : <Trash2 className="h-4 w-4" />}
          </button>
        );
      },
    }] : []),
    // QC Check column — only shown on the QC tab
    ...(tab === 'qc' ? [{
      key: '_qc_check',
      header: 'QC Check',
      render: (item: { id: string; factory_id?: string; status?: string; order_number?: string; color?: string; size?: string }) => {
        // Determine check type based on position status
        const PRE_KILN_STATUSES = ['glazing', 'drying', 'ready_to_fire', 'pending_pre_kiln_qc'];
        const checkType: 'pre_kiln' | 'final' = PRE_KILN_STATUSES.includes(item.status ?? '') ? 'pre_kiln' : 'final';
        const label = checkType === 'pre_kiln' ? 'Pre-Kiln' : 'Final';
        return (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setQcPositionId(item.id);
              setQcFactoryId(item.factory_id ?? activeFactoryId ?? '');
              setQcCheckType(checkType);
              setQcPositionLabel(`${item.order_number ?? ''} · ${item.color ?? ''} · ${item.size ?? ''}`);
              setQcOpen(true);
            }}
            className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100"
            title={`Run ${label} QC Check`}
          >
            <ClipboardCheck className="h-3.5 w-3.5" />
            {label}
          </button>
        );
      },
    }] : []),
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate('/manager')}>&larr; Back</Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Production Schedule</h1>
            <p className="mt-1 text-sm text-gray-500">Section schedules and kiln batches</p>
          </div>
        </div>
        <FactorySelector />
      </div>

      {/* KPI */}
      <div className="grid grid-cols-5 gap-4">
        <Card>
          <div className="text-sm text-gray-500">Glazing</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{glazingData?.total ?? '\u2014'}</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Firing</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{firingData?.total ?? '\u2014'}</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Sorting</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{sortingData?.total ?? '\u2014'}</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">QC</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{qcData?.total ?? '\u2014'}</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Kilns</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{kilns.length}</div>
        </Card>
      </div>

      {/* Overdue banner */}
      {overdueCount > 0 && (
        <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <span className="text-sm font-medium text-red-800">
              {overdueCount} position{overdueCount !== 1 ? 's' : ''} with past scheduled dates
            </span>
            <span className="text-xs text-red-600">
              (auto-reschedule runs nightly at 08:05 Bali time)
            </span>
          </div>
          <div className="flex items-center gap-3">
            {rescheduleResult && (
              <span className={`text-xs ${rescheduleResult.startsWith('Error') ? 'text-red-700' : 'text-green-700'}`}>
                {rescheduleResult}
              </span>
            )}
            <Button
              size="sm"
              onClick={handleRescheduleOverdue}
              disabled={rescheduling || !activeFactoryId}
              className="bg-red-600 text-white hover:bg-red-700"
            >
              <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${rescheduling ? 'animate-spin' : ''}`} />
              {rescheduling ? 'Rescheduling...' : 'Reschedule Now'}
            </Button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <Tabs tabs={SECTION_TABS} activeTab={tab} onChange={setTab} />

      {/* Auto-Form Batches — visible on Firing and Kilns tabs */}
      {(tab === 'firing' || tab === 'kilns') && (
        <div className="flex items-center gap-4">
          <Button
            onClick={handleAutoFormBatches}
            disabled={autoFormMutation.isPending || !activeFactoryId}
          >
            {autoFormMutation.isPending ? 'Forming...' : 'Auto-Form Batches'}
          </Button>
          {!activeFactoryId && (
            <span className="text-sm text-gray-400">Select a factory first</span>
          )}
          {autoFormResult && (
            <div className={`rounded-lg border px-3 py-1.5 text-sm ${autoFormResult.startsWith('Error') ? 'border-red-200 bg-red-50 text-red-700' : 'border-green-200 bg-green-50 text-green-700'}`}>
              {autoFormResult}
            </div>
          )}
        </div>
      )}

      {/* API Error */}
      {hasError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">⚠ Error loading schedule data. Try refreshing.</p>
        </div>
      )}

      {/* Cleanup mode banner */}
      {canDeletePositions && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          🗑 Cleanup mode: delete buttons are visible on each position row.
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : tab === 'kilns' ? (
        /* Kilns tab */
        kilns.length === 0 ? (
          <div className="py-8 text-center text-gray-400">No kilns found</div>
        ) : (
          <div className="space-y-4">
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {kilns.map((k: any) => (
              <Card key={k.kiln.id} className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-gray-900">{k.kiln.name}</h3>
                    <Badge status={k.kiln.status} />
                    {k.kiln.kiln_type && (
                      <span className="text-xs text-gray-500">{k.kiln.kiln_type}</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500">
                    {k.kiln?.capacity_sqm && <span>Cap: {k.kiln.capacity_sqm} m&sup2;</span>}
                    {k.kiln?.num_levels && <span className="ml-2">Levels: {k.kiln.num_levels}</span>}
                  </div>
                </div>
                {(k.batches ?? []).length > 0 ? (
                  <div className="overflow-x-auto rounded-lg border border-gray-200">
                    <table className="w-full text-left text-sm">
                      <thead className="border-b bg-gray-50 text-xs font-medium uppercase text-gray-500">
                        <tr>
                          <th className="px-4 py-2">Date</th>
                          <th className="px-4 py-2">Status</th>
                          <th className="px-4 py-2">Positions</th>
                          <th className="px-4 py-2">Pieces</th>
                          <th className="px-4 py-2">Notes</th>
                          <th className="px-4 py-2"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {k.batches.map((b: any) => (
                          <tr key={b.id} className="bg-white">
                            <td className="px-4 py-2">{b.batch_date || '\u2014'}</td>
                            <td className="px-4 py-2"><Badge status={b.status} /></td>
                            <td className="px-4 py-2">{b.positions_count}</td>
                            <td className="px-4 py-2">{b.total_pcs}</td>
                            <td className="px-4 py-2 text-xs text-gray-500">{b.notes || '\u2014'}</td>
                            <td className="px-4 py-2">
                              {b.status === 'in_progress' && (
                                <button
                                  onClick={() => openFiringLog({ id: b.id, kiln_id: k.kiln.id })}
                                  className="inline-flex items-center gap-1 rounded bg-orange-50 px-2 py-1 text-xs font-medium text-orange-700 hover:bg-orange-100"
                                  title="Log temperature readings"
                                >
                                  <Thermometer className="h-3.5 w-3.5" />
                                  Log Temp
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="py-4 text-center text-sm text-gray-400">No batches scheduled</div>
                )}
              </Card>
            ))}
          </div>
        )
      ) : (
        /* Section tabs (glazing/firing/sorting/qc) — grouped by date */
        sectionItems[tab]?.length === 0 ? (
          <div className="py-8 text-center text-gray-400">No positions in this section</div>
        ) : (
          <div className="space-y-4">
            {groupedByDate.map(([dateKey, positions]) => {
              const isUnscheduled = dateKey === 'Unscheduled';
              const dateLabel = isUnscheduled
                ? 'Unscheduled'
                : new Date(dateKey + 'T00:00:00').toLocaleDateString('en-GB', {
                    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
                  });
              const isToday = !isUnscheduled && dateKey === new Date().toISOString().slice(0, 10);
              const isPast = !isUnscheduled && dateKey < new Date().toISOString().slice(0, 10);

              return (
                <div key={dateKey}>
                  <div className={`flex items-center gap-2 rounded-t-lg border-b px-4 py-2 ${
                    isToday ? 'bg-orange-50 border-orange-200' :
                    isPast ? 'bg-red-50 border-red-200' :
                    isUnscheduled ? 'bg-gray-50 border-gray-200' :
                    'bg-blue-50 border-blue-200'
                  }`}>
                    <Calendar className={`h-4 w-4 ${
                      isToday ? 'text-orange-500' : isPast ? 'text-red-400' : isUnscheduled ? 'text-gray-400' : 'text-blue-500'
                    }`} />
                    <span className={`text-sm font-semibold ${
                      isToday ? 'text-orange-700' : isPast ? 'text-red-600' : isUnscheduled ? 'text-gray-500' : 'text-blue-700'
                    }`}>
                      {dateLabel}
                      {isToday && ' (Today)'}
                      {isPast && (() => {
                        const diff = Math.floor((Date.now() - new Date(dateKey + 'T00:00:00').getTime()) / 86400000);
                        return ` — ${diff} day${diff !== 1 ? 's' : ''} overdue`;
                      })()}
                    </span>
                    <span className="ml-auto text-xs text-gray-500">
                      {positions.length} position{positions.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <DataTable columns={positionColumns} data={positions} />
                </div>
              );
            })}
          </div>
        )
      )}

      {/* Firing Log Dialog */}
      {firingLogBatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setFiringLogBatch(null)}>
          <div className="mx-4 w-full max-w-lg rounded-xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Firing Temperature Log</h3>
              <button onClick={() => setFiringLogBatch(null)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>

            {firingLogLoading ? (
              <div className="flex justify-center py-8"><Spinner className="h-6 w-6" /></div>
            ) : !firingLogData ? (
              <div className="space-y-4">
                <p className="text-sm text-gray-500">No firing log started yet for this batch.</p>
                <Button onClick={startFiringLog} disabled={firingLogSaving}>
                  {firingLogSaving ? 'Starting...' : 'Start Firing Log'}
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Status bar */}
                <div className="flex items-center gap-3 text-sm">
                  <span className="text-gray-500">Started:</span>
                  <span className="font-medium">{firingLogData.started_at ? new Date(firingLogData.started_at).toLocaleString() : '—'}</span>
                  {firingLogData.ended_at && (
                    <>
                      <span className="text-gray-500">Ended:</span>
                      <span className="font-medium">{new Date(firingLogData.ended_at).toLocaleString()}</span>
                    </>
                  )}
                  {firingLogData.peak_temperature && (
                    <span className="rounded bg-red-50 px-2 py-0.5 text-xs font-bold text-red-700">
                      Peak: {firingLogData.peak_temperature}&deg;C
                    </span>
                  )}
                  {firingLogData.result && (
                    <Badge status={firingLogData.result} />
                  )}
                </div>

                {/* Temperature readings timeline */}
                {(firingLogData.temperature_readings?.length > 0) && (
                  <div className="max-h-48 overflow-y-auto rounded-lg border border-gray-200">
                    <table className="w-full text-left text-sm">
                      <thead className="border-b bg-gray-50 text-xs font-medium uppercase text-gray-500 sticky top-0">
                        <tr>
                          <th className="px-3 py-1.5">Time</th>
                          <th className="px-3 py-1.5">Temp (&deg;C)</th>
                          <th className="px-3 py-1.5">Notes</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {firingLogData.temperature_readings.map((r: any, i: number) => (
                          <tr key={i} className="bg-white">
                            <td className="px-3 py-1.5 font-mono text-xs">{r.time}</td>
                            <td className="px-3 py-1.5 font-bold">{r.temp}</td>
                            <td className="px-3 py-1.5 text-xs text-gray-500">{r.notes || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Add reading form — only if firing not ended */}
                {!firingLogData.ended_at && (
                  <div className="space-y-2 rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        placeholder="Temperature (\u00b0C)"
                        value={tempInput}
                        onChange={(e) => setTempInput(e.target.value)}
                        className="w-32 rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500"
                      />
                      <input
                        type="text"
                        placeholder="Notes (optional)"
                        value={tempNotes}
                        onChange={(e) => setTempNotes(e.target.value)}
                        className="flex-1 rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500"
                      />
                      <Button size="sm" onClick={addReading} disabled={firingLogSaving || !tempInput}>
                        {firingLogSaving ? '...' : 'Add'}
                      </Button>
                    </div>
                  </div>
                )}

                {/* End firing buttons — only if not ended */}
                {!firingLogData.ended_at && (
                  <div className="flex items-center gap-2 pt-2 border-t">
                    <span className="text-sm text-gray-500">End firing:</span>
                    <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white" onClick={() => endFiring('success')} disabled={firingLogSaving}>
                      Success
                    </Button>
                    <Button size="sm" className="bg-amber-500 hover:bg-amber-600 text-white" onClick={() => endFiring('partial_failure')} disabled={firingLogSaving}>
                      Partial Failure
                    </Button>
                    <Button size="sm" className="bg-red-600 hover:bg-red-700 text-white" onClick={() => endFiring('abort')} disabled={firingLogSaving}>
                      Abort
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* QC Check Dialog */}
      <QualityCheckDialog
        open={qcOpen}
        onClose={() => {
          setQcOpen(false);
          queryClient.invalidateQueries({ queryKey: ['schedule', 'qc'] });
        }}
        checkType={qcCheckType}
        positionId={qcPositionId}
        factoryId={qcFactoryId}
        positionLabel={qcPositionLabel}
      />
    </div>
  );
}
