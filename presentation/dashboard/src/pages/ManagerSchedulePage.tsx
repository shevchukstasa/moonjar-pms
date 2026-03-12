import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { useUiStore } from '@/stores/uiStore';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { useGlazingSchedule, useFiringSchedule, useSortingSchedule, useQcSchedule, useKilnSchedule } from '@/hooks/useSchedule';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Tabs } from '@/components/ui/Tabs';
import { Spinner } from '@/components/ui/Spinner';
import { DataTable } from '@/components/ui/Table';
import { FactorySelector } from '@/components/layout/FactorySelector';
import apiClient from '@/api/client';

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

  const { data: glazingData, isLoading: glazingLoading, isError: glazingError } = useGlazingSchedule(activeFactoryId);
  const { data: firingData, isLoading: firingLoading, isError: firingError } = useFiringSchedule(activeFactoryId);
  const { data: sortingData, isLoading: sortingLoading, isError: sortingError } = useSortingSchedule(activeFactoryId);
  const { data: qcData, isLoading: qcLoading, isError: qcError } = useQcSchedule(activeFactoryId);
  const { data: kilnData, isLoading: kilnLoading, isError: kilnError } = useKilnSchedule(activeFactoryId);
  const hasError = glazingError || firingError || sortingError || qcError || kilnError;

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
      render: (item) => <Badge status={item.status} />,
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

      {/* Tabs */}
      <Tabs tabs={SECTION_TABS} activeTab={tab} onChange={setTab} />

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
                    {k.kiln.capacity_sqm && <span>Cap: {k.kiln.capacity_sqm} m&sup2;</span>}
                    {k.kiln.num_levels && <span className="ml-2">Levels: {k.kiln.num_levels}</span>}
                  </div>
                </div>
                {k.batches.length > 0 ? (
                  <div className="overflow-x-auto rounded-lg border border-gray-200">
                    <table className="w-full text-left text-sm">
                      <thead className="border-b bg-gray-50 text-xs font-medium uppercase text-gray-500">
                        <tr>
                          <th className="px-4 py-2">Date</th>
                          <th className="px-4 py-2">Status</th>
                          <th className="px-4 py-2">Positions</th>
                          <th className="px-4 py-2">Pieces</th>
                          <th className="px-4 py-2">Notes</th>
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
        /* Section tabs (glazing/firing/sorting/qc) */
        sectionItems[tab]?.length === 0 ? (
          <div className="py-8 text-center text-gray-400">No positions in this section</div>
        ) : (
          <DataTable columns={positionColumns} data={(sectionItems[tab] || []) as Record<string, unknown>[]} />
        )
      )}
    </div>
  );
}
