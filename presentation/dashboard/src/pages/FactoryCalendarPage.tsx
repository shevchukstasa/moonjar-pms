import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  factoryCalendarApi,
  type CalendarEntry,
  type CalendarCreatePayload,
} from '@/api/factoryCalendar';
import { useFactories } from '@/hooks/useFactories';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';
import { Tooltip } from '@/components/ui/Tooltip';

// ── Helpers ──────────────────────────────────────────────────

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const DAY_HEADERS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function pad(n: number) {
  return n < 10 ? `0${n}` : `${n}`;
}

function toISO(y: number, m: number, d: number) {
  return `${y}-${pad(m)}-${pad(d)}`;
}

/** Returns first day of month (0=Mon) and total days in month */
function monthGrid(year: number, month: number) {
  const firstDate = new Date(year, month - 1, 1);
  const firstDow = (firstDate.getDay() + 6) % 7; // 0=Mon
  const daysInMonth = new Date(year, month, 0).getDate();
  return { firstDow, daysInMonth };
}

// ── Bulk Holiday Presets ─────────────────────────────────────

interface HolidayPreset {
  label: string;
  holidays: { date: string; name: string; source: string }[];
}

function getIndonesianHolidays(year: number): HolidayPreset {
  // Major Indonesian national holidays with fixed dates
  return {
    label: `Indonesian National Holidays ${year}`,
    holidays: [
      { date: `${year}-01-01`, name: "New Year's Day", source: 'government' },
      { date: `${year}-02-01`, name: 'Isra Mi\'raj', source: 'government' },
      { date: `${year}-03-29`, name: 'Nyepi (Day of Silence)', source: 'balinese' },
      { date: `${year}-03-31`, name: 'Eid al-Fitr', source: 'government' },
      { date: `${year}-04-01`, name: 'Eid al-Fitr (Day 2)', source: 'government' },
      { date: `${year}-04-18`, name: 'Good Friday', source: 'government' },
      { date: `${year}-05-01`, name: 'Labour Day', source: 'government' },
      { date: `${year}-05-12`, name: 'Waisak', source: 'government' },
      { date: `${year}-05-29`, name: 'Ascension of Christ', source: 'government' },
      { date: `${year}-06-01`, name: 'Pancasila Day', source: 'government' },
      { date: `${year}-06-07`, name: 'Eid al-Adha', source: 'government' },
      { date: `${year}-06-27`, name: 'Islamic New Year', source: 'government' },
      { date: `${year}-08-17`, name: 'Independence Day', source: 'government' },
      { date: `${year}-09-05`, name: 'Mawlid (Prophet Birthday)', source: 'government' },
      { date: `${year}-12-25`, name: 'Christmas Day', source: 'government' },
    ],
  };
}

function getBalineseHolidays(year: number): HolidayPreset {
  return {
    label: `Balinese Holidays ${year}`,
    holidays: [
      { date: `${year}-03-29`, name: 'Nyepi (Day of Silence)', source: 'balinese' },
      { date: `${year}-04-13`, name: 'Galungan', source: 'balinese' },
      { date: `${year}-04-23`, name: 'Kuningan', source: 'balinese' },
      { date: `${year}-10-11`, name: 'Galungan', source: 'balinese' },
      { date: `${year}-10-21`, name: 'Kuningan', source: 'balinese' },
    ],
  };
}

// ── Component ────────────────────────────────────────────────

export default function FactoryCalendarPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const today = new Date();

  // State
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [factoryId, setFactoryId] = useState<string>('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [holidayName, setHolidayName] = useState('');
  const [holidaySource, setHolidaySource] = useState<string>('manual');
  const [notes, setNotes] = useState('');
  const [formError, setFormError] = useState('');
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false);
  const [bulkPreset, setBulkPreset] = useState<HolidayPreset | null>(null);
  const [deleteConfirmEntry, setDeleteConfirmEntry] = useState<CalendarEntry | null>(null);

  // Factories
  const { data: factoriesData, isLoading: factoriesLoading } = useFactories();
  const factories = factoriesData?.items ?? [];

  // Auto-select first factory
  if (!factoryId && factories.length > 0) {
    setFactoryId(factories[0].id);
  }

  const factoryName = factories.find((f) => f.id === factoryId)?.name ?? '';

  // Calendar entries query
  const calendarQueryKey = ['factory-calendar', factoryId, year, month];
  const {
    data: calendarData,
    isLoading: calendarLoading,
    isError: calendarError,
  } = useQuery({
    queryKey: calendarQueryKey,
    queryFn: () => factoryCalendarApi.list(factoryId, year, month),
    enabled: !!factoryId,
    staleTime: 30_000,
  });

  // Working days count
  const startDate = toISO(year, month, 1);
  const endDate = toISO(year, month, monthGrid(year, month).daysInMonth);
  const {
    data: workingDaysData,
  } = useQuery({
    queryKey: ['factory-calendar-working-days', factoryId, startDate, endDate],
    queryFn: () => factoryCalendarApi.workingDays(factoryId, startDate, endDate),
    enabled: !!factoryId,
    staleTime: 30_000,
  });

  // Build entry map: date string -> CalendarEntry
  const entryMap = useMemo(() => {
    const map = new Map<string, CalendarEntry>();
    if (calendarData?.items) {
      for (const entry of calendarData.items) {
        map.set(entry.date, entry);
      }
    }
    return map;
  }, [calendarData]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: (payload: CalendarCreatePayload) => factoryCalendarApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['factory-calendar'] });
      queryClient.invalidateQueries({ queryKey: ['factory-calendar-working-days'] });
      closeDialog();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to create entry');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (entryId: string) => factoryCalendarApi.remove(entryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['factory-calendar'] });
      queryClient.invalidateQueries({ queryKey: ['factory-calendar-working-days'] });
      setDeleteConfirmEntry(null);
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to delete entry');
    },
  });

  const bulkMutation = useMutation({
    mutationFn: (payload: { factory_id: string; entries: CalendarCreatePayload[] }) =>
      factoryCalendarApi.bulkCreate(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['factory-calendar'] });
      queryClient.invalidateQueries({ queryKey: ['factory-calendar-working-days'] });
      setBulkDialogOpen(false);
      setBulkPreset(null);
      if (data.total_skipped > 0) {
        setFormError(`Created ${data.total_created}, skipped ${data.total_skipped} (duplicates).`);
      }
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Bulk creation failed');
    },
  });

  // Handlers
  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setSelectedDate('');
    setHolidayName('');
    setHolidaySource('manual');
    setNotes('');
    setFormError('');
  }, []);

  const handleDayClick = useCallback(
    (dateStr: string) => {
      const entry = entryMap.get(dateStr);
      if (entry) {
        // Entry exists -- confirm deletion
        setDeleteConfirmEntry(entry);
      } else {
        // No entry -- open create dialog
        setSelectedDate(dateStr);
        setHolidayName('');
        setHolidaySource('manual');
        setNotes('');
        setFormError('');
        setDialogOpen(true);
      }
    },
    [entryMap],
  );

  const handleCreateSubmit = useCallback(() => {
    if (!selectedDate) return;
    setFormError('');
    createMutation.mutate({
      factory_id: factoryId,
      date: selectedDate,
      is_working_day: false,
      holiday_name: holidayName || null,
      holiday_source: holidaySource || 'manual',
      notes: notes || null,
    });
  }, [factoryId, selectedDate, holidayName, holidaySource, notes, createMutation]);

  const handleBulkSubmit = useCallback(() => {
    if (!bulkPreset || !factoryId) return;
    const entries: CalendarCreatePayload[] = bulkPreset.holidays.map((h) => ({
      factory_id: factoryId,
      date: h.date,
      is_working_day: false,
      holiday_name: h.name,
      holiday_source: h.source,
    }));
    bulkMutation.mutate({ factory_id: factoryId, entries });
  }, [bulkPreset, factoryId, bulkMutation]);

  const prevMonth = () => {
    if (month === 1) { setMonth(12); setYear(year - 1); }
    else setMonth(month - 1);
  };

  const nextMonth = () => {
    if (month === 12) { setMonth(1); setYear(year + 1); }
    else setMonth(month + 1);
  };

  const goToday = () => {
    setYear(today.getFullYear());
    setMonth(today.getMonth() + 1);
  };

  // Calendar grid
  const { firstDow, daysInMonth } = monthGrid(year, month);
  const todayISO = toISO(today.getFullYear(), today.getMonth() + 1, today.getDate());

  // ── Render ─────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Factory Calendar</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage working and non-working days per factory
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin')}>
            Back to Admin
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setBulkPreset(getIndonesianHolidays(year));
              setBulkDialogOpen(true);
              setFormError('');
            }}
          >
            + National Holidays
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setBulkPreset(getBalineseHolidays(year));
              setBulkDialogOpen(true);
              setFormError('');
            }}
          >
            + Balinese Holidays
          </Button>
        </div>
      </div>

      {/* Factory selector + Month nav */}
      <Card>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          {/* Factory */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">Factory:</label>
            {factoriesLoading ? (
              <Spinner className="h-5 w-5" />
            ) : (
              <select
                value={factoryId}
                onChange={(e) => setFactoryId(e.target.value)}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {factories.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Month Navigation */}
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={prevMonth}>
              &larr;
            </Button>
            <span className="min-w-[160px] text-center text-lg font-semibold text-gray-900">
              {MONTH_NAMES[month - 1]} {year}
            </span>
            <Button variant="secondary" size="sm" onClick={nextMonth}>
              &rarr;
            </Button>
            <Button variant="secondary" size="sm" onClick={goToday}>
              Today
            </Button>
          </div>
        </div>
      </Card>

      {/* Calendar Grid */}
      {!factoryId ? (
        <Card>
          <p className="py-8 text-center text-gray-400">Select a factory to view calendar</p>
        </Card>
      ) : calendarError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm font-medium text-red-800">Error loading calendar data</p>
        </div>
      ) : calendarLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : (
        <Card>
          {/* Day headers */}
          <div className="grid grid-cols-7 gap-1">
            {DAY_HEADERS.map((d) => (
              <div
                key={d}
                className="py-2 text-center text-xs font-semibold uppercase tracking-wider text-gray-500"
              >
                {d}
              </div>
            ))}

            {/* Empty cells before first day */}
            {Array.from({ length: firstDow }, (_, i) => (
              <div key={`empty-${i}`} className="h-20" />
            ))}

            {/* Day cells */}
            {Array.from({ length: daysInMonth }, (_, i) => {
              const day = i + 1;
              const dateStr = toISO(year, month, day);
              const dateObj = new Date(year, month - 1, day);
              const dow = (dateObj.getDay() + 6) % 7; // 0=Mon, 6=Sun
              const isSunday = dow === 6;
              const entry = entryMap.get(dateStr);
              const isToday = dateStr === todayISO;

              // Determine day status
              let bgClass: string;
              let textClass: string;
              let statusLabel: string;

              if (entry) {
                if (entry.is_working_day) {
                  // Override: working on a normally off day
                  bgClass = 'bg-emerald-100 hover:bg-emerald-200 border-emerald-300';
                  textClass = 'text-emerald-900';
                  statusLabel = 'Working (override)';
                } else {
                  // Non-working day / holiday
                  bgClass = 'bg-red-100 hover:bg-red-200 border-red-300';
                  textClass = 'text-red-900';
                  statusLabel = entry.holiday_name || 'Non-working day';
                }
              } else if (isSunday) {
                bgClass = 'bg-gray-100 hover:bg-gray-200 border-gray-300';
                textClass = 'text-gray-500';
                statusLabel = 'Sunday (default off)';
              } else {
                bgClass = 'bg-emerald-50 hover:bg-emerald-100 border-emerald-200';
                textClass = 'text-emerald-800';
                statusLabel = 'Working day';
              }

              const cell = (
                <button
                  key={dateStr}
                  onClick={() => handleDayClick(dateStr)}
                  className={`relative flex h-20 flex-col items-start rounded-lg border p-1.5 text-left transition-colors ${bgClass} ${
                    isToday ? 'ring-2 ring-primary-500 ring-offset-1' : ''
                  }`}
                >
                  <span className={`text-sm font-semibold ${textClass}`}>{day}</span>
                  {entry && !entry.is_working_day && entry.holiday_name && (
                    <span className="mt-0.5 line-clamp-2 text-[10px] leading-tight text-red-700">
                      {entry.holiday_name}
                    </span>
                  )}
                  {isSunday && !entry && (
                    <span className="mt-0.5 text-[10px] text-gray-400">Sun</span>
                  )}
                </button>
              );

              // Wrap with tooltip for entries that have names/notes
              if (entry && (entry.holiday_name || entry.notes)) {
                const tipParts: string[] = [];
                if (entry.holiday_name) tipParts.push(entry.holiday_name);
                if (entry.holiday_source) tipParts.push(`[${entry.holiday_source}]`);
                if (entry.notes) tipParts.push(entry.notes);
                return (
                  <Tooltip key={dateStr} text={tipParts.join(' - ')}>
                    {cell}
                  </Tooltip>
                );
              }

              // Tooltip for default statuses
              return (
                <Tooltip key={dateStr} text={statusLabel}>
                  {cell}
                </Tooltip>
              );
            })}
          </div>
        </Card>
      )}

      {/* Working Days Summary */}
      {workingDaysData && (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="text-2xl font-bold text-emerald-700">{workingDaysData.working_days}</p>
                <p className="text-xs text-gray-500">Working Days</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-red-600">{workingDaysData.holidays}</p>
                <p className="text-xs text-gray-500">Holidays</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-500">{workingDaysData.sundays}</p>
                <p className="text-xs text-gray-500">Sundays</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900">{workingDaysData.total_days}</p>
                <p className="text-xs text-gray-500">Total Days</p>
              </div>
            </div>
            <div className="flex gap-3 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-emerald-100 border border-emerald-300" /> Working
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-red-100 border border-red-300" /> Holiday
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-gray-100 border border-gray-300" /> Sunday
              </span>
            </div>
          </div>
        </Card>
      )}

      {/* Inline info/error */}
      {formError && !dialogOpen && !bulkDialogOpen && !deleteConfirmEntry && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          {formError}
          <button className="ml-3 underline" onClick={() => setFormError('')}>
            dismiss
          </button>
        </div>
      )}

      {/* Create Entry Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        title="Add Non-Working Day"
        className="w-full max-w-md"
      >
        <div className="space-y-4">
          <div className="rounded-lg bg-gray-50 px-3 py-2 text-sm">
            <span className="font-medium text-gray-700">Date:</span>{' '}
            <span className="text-gray-900">{selectedDate}</span>
            {factoryName && (
              <>
                {' | '}
                <span className="font-medium text-gray-700">Factory:</span>{' '}
                <span className="text-gray-900">{factoryName}</span>
              </>
            )}
          </div>
          <Input
            label="Holiday Name"
            placeholder="e.g. Nyepi, Company Event"
            value={holidayName}
            onChange={(e) => setHolidayName(e.target.value)}
          />
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Source</label>
            <select
              value={holidaySource}
              onChange={(e) => setHolidaySource(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            >
              <option value="manual">Manual</option>
              <option value="government">Government Holiday</option>
              <option value="balinese">Balinese Holiday</option>
            </select>
          </div>
          <Input
            label="Notes"
            placeholder="Optional notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          {formError && <p className="text-sm text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateSubmit}
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? 'Saving...' : 'Mark as Non-Working'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog
        open={!!deleteConfirmEntry}
        onClose={() => setDeleteConfirmEntry(null)}
        title="Remove Calendar Entry"
        className="w-full max-w-md"
      >
        {deleteConfirmEntry && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Remove the calendar override for{' '}
              <span className="font-semibold">{deleteConfirmEntry.date}</span>
              {deleteConfirmEntry.holiday_name && (
                <>
                  {' ('}
                  <span className="font-medium">{deleteConfirmEntry.holiday_name}</span>
                  {')'}
                </>
              )}
              ? The day will revert to its default schedule (Mon-Sat working, Sunday off).
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDeleteConfirmEntry(null)}>
                Cancel
              </Button>
              <Button
                className="bg-red-600 hover:bg-red-700 focus:ring-red-500"
                onClick={() => deleteMutation.mutate(deleteConfirmEntry.id)}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? 'Removing...' : 'Remove'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* Bulk Holidays Dialog */}
      <Dialog
        open={bulkDialogOpen}
        onClose={() => {
          setBulkDialogOpen(false);
          setBulkPreset(null);
        }}
        title="Bulk Add Holidays"
        className="w-full max-w-lg"
      >
        {bulkPreset && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Add <span className="font-semibold">{bulkPreset.holidays.length}</span> holidays from{' '}
              <span className="font-semibold">{bulkPreset.label}</span> for factory{' '}
              <span className="font-semibold">{factoryName}</span>.
            </p>
            <p className="text-xs text-gray-400">
              Dates that already have entries will be skipped automatically.
            </p>
            <div className="max-h-60 overflow-y-auto rounded-lg border border-gray-200">
              <table className="w-full text-sm">
                <thead className="sticky top-0 border-b bg-gray-50 text-xs font-medium uppercase text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Date</th>
                    <th className="px-3 py-2 text-left">Name</th>
                    <th className="px-3 py-2 text-left">Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {bulkPreset.holidays.map((h) => (
                    <tr key={h.date} className="bg-white">
                      <td className="px-3 py-1.5 font-mono text-gray-700">{h.date}</td>
                      <td className="px-3 py-1.5 text-gray-900">{h.name}</td>
                      <td className="px-3 py-1.5 text-gray-500">{h.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {formError && <p className="text-sm text-amber-600">{formError}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="secondary"
                onClick={() => {
                  setBulkDialogOpen(false);
                  setBulkPreset(null);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleBulkSubmit}
                disabled={bulkMutation.isPending}
              >
                {bulkMutation.isPending
                  ? 'Adding...'
                  : `Add ${bulkPreset.holidays.length} Holidays`}
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
