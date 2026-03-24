import { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  factoryCalendarApi,
  type CalendarEntry,
  type CalendarCreatePayload,
} from '@/api/factoryCalendar';
import { useFactories } from '@/hooks/useFactories';
import { useCurrentUser } from '@/hooks/useCurrentUser';
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
  // Indonesian national holidays — dates for 2026 (Islamic dates shift yearly)
  // For other years these are approximate; admin should verify with government calendar
  // Source: SKB 3 Menteri No. 1497/2025, 2/2025, 5/2025
  // https://setneg.go.id/baca/index/inilah_skb_3_menteri_libur_nasional_dan_cuti_bersama_2026
  // 17 Hari Libur Nasional + 8 Cuti Bersama
  const holidays2026 = [
    // Hari Libur Nasional
    { date: '2026-01-01', name: 'Tahun Baru 2026 Masehi', source: 'government' },
    { date: '2026-01-16', name: 'Isra Mi\'raj Nabi Muhammad SAW', source: 'government' },
    { date: '2026-02-17', name: 'Tahun Baru Imlek 2577', source: 'government' },
    { date: '2026-03-19', name: 'Hari Suci Nyepi, Tahun Baru Saka 1948', source: 'balinese' },
    { date: '2026-03-21', name: 'Hari Raya Idul Fitri 1447H', source: 'government' },
    { date: '2026-03-22', name: 'Hari Raya Idul Fitri 1447H (Hari 2)', source: 'government' },
    { date: '2026-04-03', name: 'Wafat Yesus Kristus (Good Friday)', source: 'government' },
    { date: '2026-04-05', name: 'Paskah (Easter Sunday)', source: 'government' },
    { date: '2026-05-01', name: 'Hari Buruh Internasional', source: 'government' },
    { date: '2026-05-14', name: 'Kenaikan Yesus Kristus', source: 'government' },
    { date: '2026-05-27', name: 'Hari Raya Idul Adha 1447H', source: 'government' },
    { date: '2026-05-31', name: 'Hari Raya Waisak 2570 BE', source: 'government' },
    { date: '2026-06-01', name: 'Hari Lahir Pancasila', source: 'government' },
    { date: '2026-06-16', name: 'Tahun Baru Islam 1448H', source: 'government' },
    { date: '2026-08-17', name: 'Hari Kemerdekaan RI', source: 'government' },
    { date: '2026-08-25', name: 'Maulid Nabi Muhammad SAW', source: 'government' },
    { date: '2026-12-25', name: 'Hari Natal', source: 'government' },
    // Cuti Bersama
    { date: '2026-02-16', name: 'Cuti Bersama Imlek', source: 'government' },
    { date: '2026-03-18', name: 'Cuti Bersama Nyepi', source: 'government' },
    { date: '2026-03-20', name: 'Cuti Bersama Idul Fitri', source: 'government' },
    { date: '2026-03-23', name: 'Cuti Bersama Idul Fitri', source: 'government' },
    { date: '2026-03-24', name: 'Cuti Bersama Idul Fitri', source: 'government' },
    { date: '2026-05-15', name: 'Cuti Bersama Kenaikan Yesus', source: 'government' },
    { date: '2026-05-28', name: 'Cuti Bersama Idul Adha', source: 'government' },
    { date: '2026-12-24', name: 'Cuti Bersama Natal', source: 'government' },
  ];

  if (year === 2026) {
    return { label: 'Hari Libur Nasional Indonesia 2026', holidays: holidays2026 };
  }

  // Generic fallback for other years (fixed-date holidays only)
  return {
    label: `Hari Libur Nasional Indonesia ${year}`,
    holidays: [
      { date: `${year}-01-01`, name: "Tahun Baru Masehi", source: 'government' },
      { date: `${year}-05-01`, name: 'Hari Buruh', source: 'government' },
      { date: `${year}-06-01`, name: 'Hari Lahir Pancasila', source: 'government' },
      { date: `${year}-08-17`, name: 'Hari Kemerdekaan RI', source: 'government' },
      { date: `${year}-12-25`, name: 'Hari Natal', source: 'government' },
    ],
  };
}

function getBalineseHolidays(year: number): HolidayPreset {
  // Balinese holidays 2026 — Pawukon 210-day cycle
  // Source: https://www.detik.com/bali/berita/d-8293016/jadwal-lengkap-hari-raya-hindu-sepanjang-tahun-2026
  const holidays2026 = [
    { date: '2026-01-04', name: 'Hari Raya Saraswati', source: 'balinese' },
    { date: '2026-01-08', name: 'Pagerwesi', source: 'balinese' },
    { date: '2026-03-18', name: 'Pengerupukan (Nyepi Eve)', source: 'balinese' },
    { date: '2026-03-19', name: 'Nyepi (Tahun Baru Saka 1948)', source: 'balinese' },
    { date: '2026-03-20', name: 'Ngembak Geni', source: 'balinese' },
    { date: '2026-04-18', name: 'Tumpek Landep', source: 'balinese' },
    { date: '2026-05-23', name: 'Tumpek Uduh', source: 'balinese' },
    { date: '2026-06-16', name: 'Penampahan Galungan', source: 'balinese' },
    { date: '2026-06-17', name: 'Galungan', source: 'balinese' },
    { date: '2026-06-27', name: 'Kuningan', source: 'balinese' },
    { date: '2026-08-03', name: 'Hari Raya Saraswati', source: 'balinese' },
  ];

  if (year === 2026) {
    return { label: 'Hari Raya Bali 2026', holidays: holidays2026 };
  }

  return {
    label: `Hari Raya Bali ${year}`,
    holidays: [
      { date: `${year}-03-19`, name: 'Nyepi (approximate)', source: 'balinese' },
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
  const [sundayOverrideDate, setSundayOverrideDate] = useState<string>('');
  const [sundayOverrideOpen, setSundayOverrideOpen] = useState(false);

  // Factories — filter by user's assigned factories for PM
  const user = useCurrentUser();
  const { data: factoriesData, isLoading: factoriesLoading } = useFactories();
  const allFactories = factoriesData?.items ?? [];
  const GLOBAL_ROLES = new Set(['owner', 'administrator', 'ceo']);
  const isGlobal = user && GLOBAL_ROLES.has(user.role);
  const userFactoryIds = user?.factories?.map((f: { id?: string; factory_id?: string }) => f.id || f.factory_id) || [];
  const factories = isGlobal ? allFactories : allFactories.filter((f) => userFactoryIds.includes(f.id));

  // Auto-select first available factory (PM's own factory)
  useEffect(() => {
    if (!factoryId && factories.length > 0) {
      setFactoryId(factories[0].id);
    }
  }, [factories, factoryId]);

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
        // Entry exists (holiday or working-override) -- confirm deletion to revert to default
        setDeleteConfirmEntry(entry);
      } else {
        // No entry — check if it's a Sunday
        const dateObj = new Date(dateStr + 'T00:00:00');
        const dow = (dateObj.getDay() + 6) % 7; // 0=Mon, 6=Sun
        if (dow === 6) {
          // Sunday — offer to make it a working day (overtime)
          setSundayOverrideDate(dateStr);
          setSundayOverrideOpen(true);
          setFormError('');
        } else {
          // Regular working day — open create dialog to mark as non-working
          setSelectedDate(dateStr);
          setHolidayName('');
          setHolidaySource('manual');
          setNotes('');
          setFormError('');
          setDialogOpen(true);
        }
      }
    },
    [entryMap],
  );

  const handleSundayOvertime = useCallback(() => {
    if (!sundayOverrideDate) return;
    setFormError('');
    createMutation.mutate({
      factory_id: factoryId,
      date: sundayOverrideDate,
      is_working_day: true,
      holiday_name: 'Overtime / Lembur',
      holiday_source: 'manual',
      notes: 'Sunday overtime',
    }, {
      onSuccess: () => {
        setSundayOverrideOpen(false);
        setSundayOverrideDate('');
      },
    });
  }, [factoryId, sundayOverrideDate, createMutation]);

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
        title={deleteConfirmEntry?.is_working_day ? 'Revert to Default (Sunday Off)' : 'Make This a Working Day'}
        className="w-full max-w-md"
      >
        {deleteConfirmEntry && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              {deleteConfirmEntry.is_working_day ? (
                <>
                  Remove the working-day override for{' '}
                  <span className="font-semibold">{deleteConfirmEntry.date}</span>
                  {deleteConfirmEntry.holiday_name && (
                    <>
                      {' ('}
                      <span className="font-medium">{deleteConfirmEntry.holiday_name}</span>
                      {')'}
                    </>
                  )}
                  ? The day will revert to its default (Sunday off).
                </>
              ) : (
                <>
                  Remove the holiday/non-working entry for{' '}
                  <span className="font-semibold">{deleteConfirmEntry.date}</span>
                  {deleteConfirmEntry.holiday_name && (
                    <>
                      {' ('}
                      <span className="font-medium">{deleteConfirmEntry.holiday_name}</span>
                      {')'}
                    </>
                  )}
                  ? The day will become a regular working day.
                </>
              )}
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDeleteConfirmEntry(null)}>
                Cancel
              </Button>
              <Button
                className={deleteConfirmEntry.is_working_day
                  ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
                  : 'bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-500'}
                onClick={() => deleteMutation.mutate(deleteConfirmEntry.id)}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending
                  ? 'Removing...'
                  : deleteConfirmEntry.is_working_day
                    ? 'Revert to Sunday Off'
                    : 'Make Working Day'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* Sunday Overtime Dialog */}
      <Dialog
        open={sundayOverrideOpen}
        onClose={() => { setSundayOverrideOpen(false); setSundayOverrideDate(''); }}
        title="Add Sunday as Working Day"
        className="w-full max-w-md"
      >
        <div className="space-y-4">
          <div className="rounded-lg bg-gray-50 px-3 py-2 text-sm">
            <span className="font-medium text-gray-700">Date:</span>{' '}
            <span className="text-gray-900">{sundayOverrideDate}</span>
            {factoryName && (
              <>
                {' | '}
                <span className="font-medium text-gray-700">Factory:</span>{' '}
                <span className="text-gray-900">{factoryName}</span>
              </>
            )}
          </div>
          <p className="text-sm text-gray-600">
            This Sunday is currently a default day off. Add it as an overtime working day?
          </p>
          {formError && <p className="text-sm text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => { setSundayOverrideOpen(false); setSundayOverrideDate(''); }}>
              Cancel
            </Button>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-500"
              onClick={handleSundayOvertime}
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? 'Saving...' : 'Add as Overtime Working Day'}
            </Button>
          </div>
        </div>
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
