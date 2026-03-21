import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useUiStore } from '@/stores/uiStore';
import { useKilns } from '@/hooks/useKilns';
import {
  kilnMaintenanceApi,
  type MaintenanceSchedule,
  type MaintenanceType,
  type MaintenanceTypeInput,
  type MaintenanceScheduleInput,
} from '@/api/kilnMaintenance';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Dialog } from '@/components/ui/Dialog';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { FactorySelector } from '@/components/layout/FactorySelector';

const PAGE_TABS = [
  { id: 'upcoming', label: 'Upcoming' },
  { id: 'history', label: 'History' },
  { id: 'types', label: 'Maintenance Types' },
];

/* ──────────────────────────────────────────────────── */
/*  Main Page                                           */
/* ──────────────────────────────────────────────────── */

export default function KilnMaintenancePage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState('upcoming');
  const factoryId = useUiStore((s) => s.activeFactoryId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kiln Maintenance</h1>
          <p className="mt-1 text-sm text-gray-500">
            Schedule, track, and manage kiln maintenance
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

      {tab === 'upcoming' && <UpcomingTab factoryId={factoryId} />}
      {tab === 'history' && <HistoryTab factoryId={factoryId} />}
      {tab === 'types' && <TypesTab />}
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Helpers                                             */
/* ──────────────────────────────────────────────────── */

function getDateStatus(scheduledDate: string): 'overdue' | 'today' | 'upcoming' {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const d = new Date(scheduledDate + 'T00:00:00');
  if (d < today) return 'overdue';
  if (d.getTime() === today.getTime()) return 'today';
  return 'upcoming';
}

function DateBadge({ date }: { date: string }) {
  const status = getDateStatus(date);
  const colors: Record<string, string> = {
    overdue: 'bg-red-100 text-red-700',
    today: 'bg-yellow-100 text-yellow-700',
    upcoming: 'bg-green-100 text-green-700',
  };
  const labels: Record<string, string> = {
    overdue: 'Overdue',
    today: 'Today',
    upcoming: 'Upcoming',
  };
  return <Badge className={colors[status]}>{labels[status]}</Badge>;
}

function RequirementBadges({ item }: { item: MaintenanceSchedule }) {
  return (
    <div className="flex flex-wrap gap-1">
      {item.requires_empty_kiln && (
        <span className="inline-flex items-center rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-medium text-orange-700">
          Empty kiln
        </span>
      )}
      {item.requires_cooled_kiln && (
        <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700">
          Cooled
        </span>
      )}
      {item.requires_power_off && (
        <span className="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-700">
          Power off
        </span>
      )}
      {item.is_recurring && (
        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
          Recurring ({item.recurrence_interval_days}d)
        </span>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Upcoming Tab                                        */
/* ──────────────────────────────────────────────────── */

function UpcomingTab({ factoryId }: { factoryId: string | null }) {
  const qc = useQueryClient();
  const [showSchedule, setShowSchedule] = useState(false);
  const [completeTarget, setCompleteTarget] = useState<MaintenanceSchedule | null>(null);
  const [completeNotes, setCompleteNotes] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<MaintenanceSchedule | null>(null);

  const params: { factory_id?: string; days?: number } = { days: 90 };
  if (factoryId) params.factory_id = factoryId;

  const { data, isLoading } = useQuery({
    queryKey: ['kiln-maintenance-upcoming', params],
    queryFn: () => kilnMaintenanceApi.listUpcoming(params),
  });

  // Also fetch overdue items (all planned items, then filter client-side)
  const { data: allData } = useQuery({
    queryKey: ['kiln-maintenance-all-planned', factoryId],
    queryFn: () => {
      const p: Record<string, string> = { status: 'planned', per_page: '200' };
      if (factoryId) p.factory_id = factoryId;
      return kilnMaintenanceApi.listAll(p);
    },
  });

  const completeMutation = useMutation({
    mutationFn: ({ kilnId, scheduleId, notes }: { kilnId: string; scheduleId: string; notes?: string }) =>
      kilnMaintenanceApi.complete(kilnId, scheduleId, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kiln-maintenance-upcoming'] });
      qc.invalidateQueries({ queryKey: ['kiln-maintenance-all-planned'] });
      qc.invalidateQueries({ queryKey: ['kiln-maintenance-history'] });
      setCompleteTarget(null);
      setCompleteNotes('');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: ({ kilnId, scheduleId }: { kilnId: string; scheduleId: string }) =>
      kilnMaintenanceApi.cancel(kilnId, scheduleId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kiln-maintenance-upcoming'] });
      qc.invalidateQueries({ queryKey: ['kiln-maintenance-all-planned'] });
    },
  });

  if (isLoading) {
    return <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>;
  }

  // Merge upcoming + overdue (from allData) deduped by id
  const upcomingItems = data?.items || [];
  const overdueItems = (allData?.items || []).filter((item) => {
    const status = getDateStatus(item.scheduled_date);
    return status === 'overdue' && !upcomingItems.find((u) => u.id === item.id);
  });
  const items = [...overdueItems, ...upcomingItems].sort((a, b) =>
    a.scheduled_date.localeCompare(b.scheduled_date),
  );

  // Summary counts
  const overdueCount = items.filter((i) => getDateStatus(i.scheduled_date) === 'overdue').length;
  const todayCount = items.filter((i) => getDateStatus(i.scheduled_date) === 'today').length;

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <div className="text-xs text-gray-500">Total Scheduled</div>
          <div className="mt-1 text-2xl font-bold">{items.length}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Overdue</div>
          <div className="mt-1 text-2xl font-bold text-red-600">{overdueCount}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Today</div>
          <div className="mt-1 text-2xl font-bold text-yellow-600">{todayCount}</div>
        </Card>
        <Card className="flex items-center justify-center">
          <Button onClick={() => setShowSchedule(true)}>+ Schedule Maintenance</Button>
        </Card>
      </div>

      {/* Schedule dialog */}
      {showSchedule && (
        <ScheduleMaintenanceForm
          factoryId={factoryId}
          onDone={() => {
            setShowSchedule(false);
            qc.invalidateQueries({ queryKey: ['kiln-maintenance-upcoming'] });
            qc.invalidateQueries({ queryKey: ['kiln-maintenance-all-planned'] });
          }}
          onCancel={() => setShowSchedule(false)}
        />
      )}

      {/* Complete dialog */}
      {completeTarget && (
        <Card className="border-green-200 bg-green-50/30 p-5">
          <h3 className="text-sm font-bold text-gray-700 mb-2">
            Complete: {completeTarget.maintenance_type} - {completeTarget.kiln_name}
          </h3>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Completion Notes (optional)</label>
            <input
              type="text"
              value={completeNotes}
              onChange={(e) => setCompleteNotes(e.target.value)}
              placeholder="Any notes about this maintenance..."
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="mt-3 flex gap-2">
            <Button
              onClick={() =>
                completeMutation.mutate({
                  kilnId: completeTarget.resource_id,
                  scheduleId: completeTarget.id,
                  notes: completeNotes || undefined,
                })
              }
              disabled={completeMutation.isPending}
            >
              {completeMutation.isPending ? <Spinner className="h-4 w-4 mr-2" /> : null}
              Mark Complete
            </Button>
            <Button variant="ghost" onClick={() => { setCompleteTarget(null); setCompleteNotes(''); }}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      {/* Items list */}
      {items.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-lg font-medium text-gray-400">No upcoming maintenance</p>
          <p className="mt-1 text-sm text-gray-400">Schedule your first maintenance using the button above</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Kiln</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Scheduled Date</th>
                <th className="px-4 py-3">Duration</th>
                <th className="px-4 py-3">Requirements</th>
                <th className="px-4 py-3">Notes</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((item) => {
                const dateStatus = getDateStatus(item.scheduled_date);
                return (
                  <tr
                    key={item.id}
                    className={
                      dateStatus === 'overdue'
                        ? 'bg-red-50/50'
                        : dateStatus === 'today'
                          ? 'bg-yellow-50/50'
                          : ''
                    }
                  >
                    <td className="px-4 py-3">
                      <DateBadge date={item.scheduled_date} />
                    </td>
                    <td className="px-4 py-3 font-medium">{item.kiln_name || '---'}</td>
                    <td className="px-4 py-3">{item.maintenance_type}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {item.scheduled_date}
                      {item.scheduled_time ? ` ${item.scheduled_time}` : ''}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {item.estimated_duration_hours ? `${item.estimated_duration_hours}h` : '---'}
                    </td>
                    <td className="px-4 py-3">
                      <RequirementBadges item={item} />
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 max-w-[150px] truncate">
                      {item.notes || '---'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          className="text-xs text-green-700 hover:bg-green-50"
                          onClick={() => setCompleteTarget(item)}
                        >
                          Complete
                        </Button>
                        <Button
                          variant="ghost"
                          className="text-xs text-red-600 hover:bg-red-50"
                          onClick={() => setDeleteTarget(item)}
                          disabled={cancelMutation.isPending}
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete Scheduled Maintenance">
        <p className="text-sm text-gray-600">
          Are you sure you want to delete this scheduled maintenance
          {deleteTarget ? ` (${deleteTarget.maintenance_type} - ${deleteTarget.kiln_name})` : ''}? This action will be logged.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button
            variant="danger"
            onClick={() => {
              if (deleteTarget) {
                cancelMutation.mutate({
                  kilnId: deleteTarget.resource_id,
                  scheduleId: deleteTarget.id,
                });
                setDeleteTarget(null);
              }
            }}
            disabled={cancelMutation.isPending}
          >
            {cancelMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Schedule Maintenance Form                           */
/* ──────────────────────────────────────────────────── */

function ScheduleMaintenanceForm({
  factoryId,
  onDone,
  onCancel,
}: {
  factoryId: string | null;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [kilnId, setKilnId] = useState('');
  const [typeId, setTypeId] = useState('');
  const [scheduledDate, setScheduledDate] = useState(new Date().toISOString().slice(0, 10));
  const [scheduledTime, setScheduledTime] = useState('');
  const [notes, setNotes] = useState('');
  const [isRecurring, setIsRecurring] = useState(false);
  const [intervalDays, setIntervalDays] = useState('');

  const { data: kilnsData } = useKilns(factoryId ? { factory_id: factoryId } : undefined);
  const kilns = kilnsData?.items || [];

  const { data: typesData } = useQuery({
    queryKey: ['kiln-maintenance-types'],
    queryFn: () => kilnMaintenanceApi.listTypes(),
  });
  const types = typesData?.items || [];

  const scheduleMutation = useMutation({
    mutationFn: ({ kilnId, data }: { kilnId: string; data: MaintenanceScheduleInput }) =>
      kilnMaintenanceApi.scheduleForKiln(kilnId, data),
    onSuccess: () => onDone(),
  });

  const selectedType = types.find((t) => t.id === typeId);

  const handleSubmit = () => {
    if (!kilnId || !scheduledDate) return;
    const data: MaintenanceScheduleInput = {
      scheduled_date: scheduledDate,
      maintenance_type_id: typeId || undefined,
      maintenance_type: selectedType?.name || undefined,
      scheduled_time: scheduledTime || undefined,
      notes: notes || undefined,
      factory_id: factoryId || undefined,
      is_recurring: isRecurring,
      recurrence_interval_days: isRecurring && intervalDays ? parseInt(intervalDays, 10) : undefined,
    };
    scheduleMutation.mutate({ kilnId, data });
  };

  if (!factoryId) {
    return (
      <Card className="border-blue-200 bg-blue-50/30 p-5">
        <p className="text-gray-400">Select a factory first</p>
      </Card>
    );
  }

  return (
    <Card className="border-blue-200 bg-blue-50/30 p-5">
      <h3 className="text-sm font-bold text-gray-700 mb-3">Schedule Maintenance</h3>
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
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Maintenance Type</label>
          <select
            value={typeId}
            onChange={(e) => {
              setTypeId(e.target.value);
              const t = types.find((x) => x.id === e.target.value);
              if (t?.default_interval_days) {
                setIsRecurring(true);
                setIntervalDays(String(t.default_interval_days));
              }
            }}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">General Maintenance</option>
            {types.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Scheduled Date *</label>
          <input
            type="date"
            value={scheduledDate}
            onChange={(e) => setScheduledDate(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Time (optional)</label>
          <input
            type="time"
            value={scheduledTime}
            onChange={(e) => setScheduledTime(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      {/* Selected type info */}
      {selectedType && (
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-500">
          <span>Duration: {selectedType.duration_hours}h</span>
          {selectedType.requires_empty_kiln && <Badge className="bg-orange-100 text-orange-700">Requires empty kiln</Badge>}
          {selectedType.requires_cooled_kiln && <Badge className="bg-blue-100 text-blue-700">Requires cooling</Badge>}
          {selectedType.requires_power_off && <Badge className="bg-purple-100 text-purple-700">Requires power off</Badge>}
        </div>
      )}

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Notes (optional)</label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Additional details..."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="flex items-end gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isRecurring}
              onChange={(e) => setIsRecurring(e.target.checked)}
              className="rounded border-gray-300"
            />
            Recurring
          </label>
          {isRecurring && (
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-500 mb-1">Interval (days)</label>
              <input
                type="number"
                value={intervalDays}
                onChange={(e) => setIntervalDays(e.target.value)}
                min={1}
                placeholder="e.g. 30"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 flex gap-2">
        <Button
          onClick={handleSubmit}
          disabled={!kilnId || !scheduledDate || scheduleMutation.isPending}
        >
          {scheduleMutation.isPending ? <Spinner className="h-4 w-4 mr-2" /> : null}
          Schedule
        </Button>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>

      {scheduleMutation.isError && (
        <div className="mt-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {(scheduleMutation.error as any)?.response?.data?.detail || 'Failed to schedule maintenance'}
        </div>
      )}
    </Card>
  );
}

/* ──────────────────────────────────────────────────── */
/*  History Tab                                         */
/* ──────────────────────────────────────────────────── */

function HistoryTab({ factoryId }: { factoryId: string | null }) {
  const [filterKiln, setFilterKiln] = useState('');
  const [filterFrom, setFilterFrom] = useState('');
  const [filterTo, setFilterTo] = useState('');

  const { data: kilnsData } = useKilns(factoryId ? { factory_id: factoryId } : undefined);
  const kilns = kilnsData?.items || [];

  const params: Record<string, string> = { status: 'done', per_page: '100' };
  if (factoryId) params.factory_id = factoryId;

  const { data, isLoading } = useQuery({
    queryKey: ['kiln-maintenance-history', factoryId],
    queryFn: () => kilnMaintenanceApi.listAll(params),
  });

  let items = data?.items || [];

  // Client-side filters
  if (filterKiln) {
    items = items.filter((i) => i.resource_id === filterKiln);
  }
  if (filterFrom) {
    items = items.filter((i) => i.scheduled_date >= filterFrom);
  }
  if (filterTo) {
    items = items.filter((i) => i.scheduled_date <= filterTo);
  }

  if (isLoading) {
    return <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>;
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card className="p-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Filter by Kiln</label>
            <select
              value={filterKiln}
              onChange={(e) => setFilterKiln(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All kilns</option>
              {kilns.map((k) => (
                <option key={k.id} value={k.id}>{k.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">From Date</label>
            <input
              type="date"
              value={filterFrom}
              onChange={(e) => setFilterFrom(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">To Date</label>
            <input
              type="date"
              value={filterTo}
              onChange={(e) => setFilterTo(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>
      </Card>

      {items.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-lg font-medium text-gray-400">No completed maintenance records</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Kiln</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Scheduled Date</th>
                <th className="px-4 py-3">Completed Date</th>
                <th className="px-4 py-3">Duration</th>
                <th className="px-4 py-3">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((item) => (
                <tr key={item.id}>
                  <td className="px-4 py-3 font-medium">{item.kiln_name || '---'}</td>
                  <td className="px-4 py-3">{item.maintenance_type}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{item.scheduled_date}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {item.completed_at ? new Date(item.completed_at).toLocaleDateString() : '---'}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {item.estimated_duration_hours ? `${item.estimated_duration_hours}h` : '---'}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-[250px] truncate">
                    {item.notes || '---'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Maintenance Types Tab                               */
/* ──────────────────────────────────────────────────── */

function TypesTab() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [editTarget, setEditTarget] = useState<MaintenanceType | null>(null);
  const [deleteTypeId, setDeleteTypeId] = useState<string | null>(null);

  const deleteTypeMut = useMutation({
    mutationFn: (id: string) => kilnMaintenanceApi.deleteType(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kiln-maintenance-types'] });
      setDeleteTypeId(null);
    },
  });

  const { data, isLoading } = useQuery({
    queryKey: ['kiln-maintenance-types'],
    queryFn: () => kilnMaintenanceApi.listTypes(),
  });

  const types = data?.items || [];

  if (isLoading) {
    return <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => { setShowAdd(true); setEditTarget(null); }}>
          + Add Type
        </Button>
      </div>

      {(showAdd || editTarget) && (
        <TypeForm
          initial={editTarget}
          onDone={() => {
            setShowAdd(false);
            setEditTarget(null);
            qc.invalidateQueries({ queryKey: ['kiln-maintenance-types'] });
          }}
          onCancel={() => { setShowAdd(false); setEditTarget(null); }}
        />
      )}

      {types.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-lg font-medium text-gray-400">No maintenance types defined</p>
          <p className="mt-1 text-sm text-gray-400">Add types to standardize your maintenance scheduling</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3 text-center">Duration (h)</th>
                <th className="px-4 py-3 text-center">Empty Kiln</th>
                <th className="px-4 py-3 text-center">Cooled</th>
                <th className="px-4 py-3 text-center">Power Off</th>
                <th className="px-4 py-3 text-center">Interval (days)</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {types.map((t) => (
                <tr key={t.id}>
                  <td className="px-4 py-3 font-medium">{t.name}</td>
                  <td className="px-4 py-3 text-gray-500 max-w-[200px] truncate">{t.description || '---'}</td>
                  <td className="px-4 py-3 text-center">{t.duration_hours ?? '---'}</td>
                  <td className="px-4 py-3 text-center">
                    {t.requires_empty_kiln ? (
                      <span className="text-orange-600 font-bold">Yes</span>
                    ) : (
                      <span className="text-gray-300">No</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {t.requires_cooled_kiln ? (
                      <span className="text-blue-600 font-bold">Yes</span>
                    ) : (
                      <span className="text-gray-300">No</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {t.requires_power_off ? (
                      <span className="text-purple-600 font-bold">Yes</span>
                    ) : (
                      <span className="text-gray-300">No</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {t.default_interval_days ?? '---'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        className="text-xs"
                        onClick={() => { setEditTarget(t); setShowAdd(false); }}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        className="text-xs text-red-600"
                        onClick={() => setDeleteTypeId(t.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Type Confirmation Dialog */}
      <Dialog open={!!deleteTypeId} onClose={() => setDeleteTypeId(null)} title="Delete Maintenance Type">
        <p className="text-sm text-gray-600">Are you sure you want to delete this maintenance type? This action will be logged.</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteTypeId(null)}>Cancel</Button>
          <Button variant="danger" onClick={() => deleteTypeId && deleteTypeMut.mutate(deleteTypeId)} disabled={deleteTypeMut.isPending}>
            {deleteTypeMut.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Type Create/Edit Form                               */
/* ──────────────────────────────────────────────────── */

function TypeForm({
  initial,
  onDone,
  onCancel,
}: {
  initial: MaintenanceType | null;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name || '');
  const [description, setDescription] = useState(initial?.description || '');
  const [durationHours, setDurationHours] = useState(String(initial?.duration_hours ?? 2));
  const [requiresEmpty, setRequiresEmpty] = useState(initial?.requires_empty_kiln ?? false);
  const [requiresCooled, setRequiresCooled] = useState(initial?.requires_cooled_kiln ?? false);
  const [requiresPower, setRequiresPower] = useState(initial?.requires_power_off ?? false);
  const [intervalDays, setIntervalDays] = useState(String(initial?.default_interval_days ?? ''));

  const createMutation = useMutation({
    mutationFn: (data: MaintenanceTypeInput) => kilnMaintenanceApi.createType(data),
    onSuccess: () => onDone(),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<MaintenanceTypeInput>) => kilnMaintenanceApi.updateType(initial!.id, data),
    onSuccess: () => onDone(),
  });

  const handleSubmit = () => {
    if (!name.trim()) return;
    const payload: MaintenanceTypeInput = {
      name: name.trim(),
      description: description.trim() || undefined,
      duration_hours: parseFloat(durationHours) || 2,
      requires_empty_kiln: requiresEmpty,
      requires_cooled_kiln: requiresCooled,
      requires_power_off: requiresPower,
      default_interval_days: intervalDays ? parseInt(intervalDays, 10) : null,
    };
    if (initial) {
      updateMutation.mutate(payload);
    } else {
      createMutation.mutate(payload);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;
  const isError = createMutation.isError || updateMutation.isError;
  const error = createMutation.error || updateMutation.error;

  return (
    <Card className="border-blue-200 bg-blue-50/30 p-5">
      <h3 className="text-sm font-bold text-gray-700 mb-3">
        {initial ? 'Edit Maintenance Type' : 'Add Maintenance Type'}
      </h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Name *</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Element Replacement"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description..."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Duration (hours)</label>
          <input
            type="number"
            value={durationHours}
            onChange={(e) => setDurationHours(e.target.value)}
            min={0.5}
            step={0.5}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Default Interval (days)</label>
          <input
            type="number"
            value={intervalDays}
            onChange={(e) => setIntervalDays(e.target.value)}
            min={1}
            placeholder="Leave empty for non-recurring"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={requiresEmpty}
            onChange={(e) => setRequiresEmpty(e.target.checked)}
            className="rounded border-gray-300"
          />
          Requires empty kiln
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={requiresCooled}
            onChange={(e) => setRequiresCooled(e.target.checked)}
            className="rounded border-gray-300"
          />
          Requires cooled kiln
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={requiresPower}
            onChange={(e) => setRequiresPower(e.target.checked)}
            className="rounded border-gray-300"
          />
          Requires power off
        </label>
      </div>
      <div className="mt-3 flex gap-2">
        <Button onClick={handleSubmit} disabled={!name.trim() || isPending}>
          {isPending ? <Spinner className="h-4 w-4 mr-2" /> : null}
          {initial ? 'Update' : 'Create'}
        </Button>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
      {isError && (
        <div className="mt-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {(error as any)?.response?.data?.detail || 'Operation failed'}
        </div>
      )}
    </Card>
  );
}
