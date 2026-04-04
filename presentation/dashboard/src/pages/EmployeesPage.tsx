import { useState, useMemo, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';
import {
  employeesApi,
  type Employee,
  type EmployeeCreatePayload,
  type EmployeeUpdatePayload,
  type AttendanceRecord,
  type PayrollSummaryItem,
} from '@/api/employees';
import { useFactories } from '@/hooks/useFactories';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import {
  factoryCalendarApi,
  type CalendarEntry,
  type WorkingDaysResponse,
} from '@/api/factoryCalendar';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { Badge } from '@/components/ui/Badge';

// ── Constants ────────────────────────────────────────────────

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const EMPLOYMENT_TYPES = [
  { value: 'full_time', label: 'Full Time' },
  { value: 'part_time', label: 'Part Time' },
  { value: 'contract', label: 'Contract' },
];

const EMPLOYMENT_CATEGORIES = [
  { value: 'formal', label: 'Formal (PPh 21)' },
  { value: 'contractor', label: 'Contractor (PPh 23)' },
];

const DEPARTMENTS = [
  { value: 'production', label: 'Production' },
  { value: 'sales', label: 'Sales' },
  { value: 'administration', label: 'Administration' },
];

const WORK_SCHEDULES = [
  { value: 'five_day', label: '5-Day (Mon–Fri)' },
  { value: 'six_day', label: '6-Day (Mon–Sat)' },
];

const BPJS_MODES = [
  { value: 'company_pays', label: 'Company Pays' },
  { value: 'reimburse', label: 'Reimburse Employee' },
];

const PAY_PERIODS = [
  { value: 'calendar_month', label: 'Calendar Month (paid last day)' },
  { value: '25_to_24', label: '25th–24th (paid on 25th)' },
];

const ATTENDANCE_STATUSES = [
  { value: 'present', label: 'P', color: 'bg-emerald-100 text-emerald-800' },
  { value: 'absent', label: 'A', color: 'bg-red-100 text-red-800' },
  { value: 'sick', label: 'S', color: 'bg-yellow-100 text-yellow-800' },
  { value: 'leave', label: 'L', color: 'bg-blue-100 text-blue-800' },
  { value: 'half_day', label: 'H', color: 'bg-orange-100 text-orange-800' },
];

function pad(n: number) { return n < 10 ? `0${n}` : `${n}`; }
function toISO(y: number, m: number, d: number) { return `${y}-${pad(m)}-${pad(d)}`; }
function formatIDR(n: number) { return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(n); }

// ── Main Component ───────────────────────────────────────────

export default function EmployeesPage() {
  const queryClient = useQueryClient();
  const today = new Date();
  const user = useCurrentUser();
  const location = useLocation();

  // Detect if accessed from PM /manager/staff route — pre-filter to production dept + PM's factory
  const isStaffView = location.pathname.startsWith('/manager/staff');

  // State
  const [activeTab, setActiveTab] = useState('employees');
  const [factoryId, setFactoryId] = useState('');
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [showInactive, setShowInactive] = useState(false);

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [formError, setFormError] = useState('');

  // Attendance dialog
  const [attDialogOpen, setAttDialogOpen] = useState(false);
  const [attEmployee, setAttEmployee] = useState<Employee | null>(null);
  const [attDate, setAttDate] = useState('');
  const [attStatus, setAttStatus] = useState('present');
  const [attOvertime, setAttOvertime] = useState('0');
  const [attNotes, setAttNotes] = useState('');
  const [attExistingId, setAttExistingId] = useState<string | null>(null);
  const [attHoursWorked, setAttHoursWorked] = useState('');

  // Form state
  const [formData, setFormData] = useState<EmployeeCreatePayload>({
    factory_id: '',
    full_name: '',
    short_name: '',
    position: '',
    phone: '',
    email: '',
    birth_date: '',
    has_own_bpjs: false,
    hire_date: '',
    employment_type: 'full_time',
    department: isStaffView ? 'production' : 'production',
    work_schedule: 'six_day',
    bpjs_mode: 'company_pays',
    employment_category: 'formal',
    pay_period: 'calendar_month',
    commission_rate: null,
    base_salary: 0,
    allowance_bike: 0,
    allowance_housing: 0,
    allowance_food: 0,
    allowance_bpjs: 0,
    allowance_other: 0,
    allowance_other_note: '',
  });

  // Factories
  const { data: factoriesData, isLoading: factoriesLoading } = useFactories();
  const allFactories = factoriesData?.items ?? [];
  const GLOBAL_ROLES = new Set(['owner', 'administrator', 'ceo']);
  const isGlobal = user && GLOBAL_ROLES.has(user.role);
  const userFactoryIds = user?.factories?.map((f: { id?: string; factory_id?: string }) => f.id || f.factory_id) || [];
  const factories = isGlobal ? allFactories : allFactories.filter((f) => userFactoryIds.includes(f.id));

  useEffect(() => {
    if (!factoryId && factories.length > 0) setFactoryId(factories[0].id);
  }, [factories, factoryId]);

  // ── Queries ─────────────────────────────────────────────────

  const { data: employeesData, isLoading: employeesLoading } = useQuery({
    queryKey: ['employees', factoryId, showInactive, isStaffView ? 'production' : 'all'],
    queryFn: () => employeesApi.list({
      factory_id: factoryId,
      is_active: showInactive ? undefined : true,
      department: isStaffView ? 'production' : undefined,
    }),
    enabled: !!factoryId,
  });

  const employees = employeesData?.items ?? [];

  // Attendance for all employees for this month
  const { data: attendanceData, isLoading: attendanceLoading } = useQuery({
    queryKey: ['attendance-grid', factoryId, year, month],
    queryFn: async () => {
      if (!employees.length) return {};
      const results: Record<string, AttendanceRecord[]> = {};
      for (const emp of employees) {
        const res = await employeesApi.getAttendance(emp.id, { year, month });
        results[emp.id] = res.items;
      }
      return results;
    },
    enabled: !!factoryId && employees.length > 0 && activeTab === 'attendance',
  });

  // Factory calendar for attendance tab (color-coded headers + working days count)
  const { data: calendarData } = useQuery({
    queryKey: ['factory-calendar', factoryId, year, month],
    queryFn: () => factoryCalendarApi.list(factoryId, year, month),
    enabled: !!factoryId && activeTab === 'attendance',
    staleTime: 30_000,
  });

  const calendarStartDate = toISO(year, month, 1);
  const calendarDaysInMonth = new Date(year, month, 0).getDate();
  const calendarEndDate = toISO(year, month, calendarDaysInMonth);
  const { data: workingDaysData } = useQuery({
    queryKey: ['factory-calendar-working-days', factoryId, calendarStartDate, calendarEndDate],
    queryFn: () => factoryCalendarApi.workingDays(factoryId, calendarStartDate, calendarEndDate),
    enabled: !!factoryId && activeTab === 'attendance',
    staleTime: 30_000,
  });

  // Build calendar lookup: date -> CalendarEntry
  const calendarMap = useMemo(() => {
    const map = new Map<string, CalendarEntry>();
    if (calendarData?.items) {
      for (const entry of calendarData.items) {
        map.set(entry.date, entry);
      }
    }
    return map;
  }, [calendarData]);

  // Payroll
  const { data: payrollData, isLoading: payrollLoading } = useQuery({
    queryKey: ['payroll-summary', factoryId, year, month],
    queryFn: () => employeesApi.payrollSummary({ factory_id: factoryId, year, month }),
    enabled: !!factoryId && activeTab === 'payroll',
  });

  // ── Mutations ───────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (data: EmployeeCreatePayload) => employeesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      closeDialog();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to create employee');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: EmployeeUpdatePayload }) => employeesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      closeDialog();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to update employee');
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => employeesApi.deactivate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees'] }),
  });

  const attendanceMutation = useMutation({
    mutationFn: ({ empId, existingId, data }: { empId: string; existingId: string | null; data: { date: string; status: string; overtime_hours: number; hours_worked?: number; notes?: string } }) =>
      existingId
        ? employeesApi.updateAttendance(existingId, { status: data.status, overtime_hours: data.overtime_hours, hours_worked: data.hours_worked, notes: data.notes })
        : employeesApi.recordAttendance(empId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attendance-grid'] });
      queryClient.invalidateQueries({ queryKey: ['payroll-summary'] });
      setAttDialogOpen(false);
      setAttExistingId(null);
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to record attendance');
    },
  });

  // ── Handlers ────────────────────────────────────────────────

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setEditingEmployee(null);
    setFormError('');
    setFormData({
      factory_id: factoryId,
      full_name: '',
      position: '',
      phone: '',
      hire_date: '',
      employment_type: 'full_time',
      department: isStaffView ? 'production' : 'production',
      work_schedule: 'six_day',
      bpjs_mode: 'company_pays',
      employment_category: 'formal',
      commission_rate: null,
      base_salary: 0,
      allowance_bike: 0,
      allowance_housing: 0,
      allowance_food: 0,
      allowance_bpjs: 0,
      allowance_other: 0,
      allowance_other_note: '',
    });
  }, [factoryId, isStaffView]);

  const openCreate = useCallback(() => {
    setEditingEmployee(null);
    setFormData({
      factory_id: factoryId,
      full_name: '',
      position: '',
      phone: '',
      hire_date: '',
      employment_type: 'full_time',
      department: isStaffView ? 'production' : 'production',
      work_schedule: 'six_day',
      bpjs_mode: 'company_pays',
      employment_category: 'formal',
      commission_rate: null,
      base_salary: 0,
      allowance_bike: 0,
      allowance_housing: 0,
      allowance_food: 0,
      allowance_bpjs: 0,
      allowance_other: 0,
      allowance_other_note: '',
    });
    setFormError('');
    setDialogOpen(true);
  }, [factoryId, isStaffView]);

  const openEdit = useCallback((emp: Employee) => {
    setEditingEmployee(emp);
    setFormData({
      factory_id: emp.factory_id,
      full_name: emp.full_name,
      short_name: emp.short_name ?? '',
      position: emp.position,
      phone: emp.phone ?? '',
      email: emp.email ?? '',
      birth_date: emp.birth_date ?? '',
      has_own_bpjs: emp.has_own_bpjs ?? false,
      hire_date: emp.hire_date ?? '',
      employment_type: emp.employment_type,
      department: emp.department || 'production',
      work_schedule: emp.work_schedule || 'six_day',
      bpjs_mode: emp.bpjs_mode || 'company_pays',
      employment_category: emp.employment_category || 'formal',
      commission_rate: emp.commission_rate,
      pay_period: emp.pay_period || 'calendar_month',
      base_salary: emp.base_salary,
      allowance_bike: emp.allowance_bike,
      allowance_housing: emp.allowance_housing,
      allowance_food: emp.allowance_food,
      allowance_bpjs: emp.allowance_bpjs,
      allowance_other: emp.allowance_other,
      allowance_other_note: emp.allowance_other_note ?? '',
    });
    setFormError('');
    setDialogOpen(true);
  }, []);

  const handleSubmit = useCallback(() => {
    if (!formData.full_name || !formData.position) {
      setFormError('Name and position are required');
      return;
    }
    if (editingEmployee) {
      const { factory_id, ...rest } = formData;
      // Convert empty strings to null for optional fields
      const cleaned = Object.fromEntries(
        Object.entries(rest).map(([k, v]) => [k, v === '' ? null : v])
      );
      updateMutation.mutate({ id: editingEmployee.id, data: cleaned });
    } else {
      createMutation.mutate({ ...formData, factory_id: factoryId });
    }
  }, [formData, editingEmployee, factoryId, createMutation, updateMutation]);

  const openAttendanceDialog = useCallback((emp: Employee, dateStr: string, existingRecord?: { id?: string; status: string; overtime_hours?: number; hours_worked?: number | null; notes?: string }) => {
    setAttEmployee(emp);
    setAttDate(dateStr);
    setFormError('');
    setAttExistingId(existingRecord?.id ?? null);

    if (existingRecord) {
      // Pre-fill from existing record (editing mode)
      setAttStatus(existingRecord.status);
      setAttOvertime(String(existingRecord.overtime_hours ?? 0));
      setAttHoursWorked(existingRecord.hours_worked != null ? String(existingRecord.hours_worked) : '');
      setAttNotes(existingRecord.notes ?? '');
    } else {
      // New record
      setAttStatus('present');
      setAttHoursWorked('');

      // Check if this date is a non-working day (holiday or Sunday)
      const dateObj = new Date(dateStr);
      const isSunday = dateObj.getDay() === 0;
      const calEntry = calendarMap.get(dateStr);
      const isNonWorking = calEntry ? !calEntry.is_working_day : isSunday;

      if (isNonWorking) {
        setAttOvertime('8');
        const reason = calEntry?.holiday_name ?? (isSunday ? 'Sunday' : 'Holiday');
        setAttNotes(`Overtime: ${reason}`);
      } else {
        setAttOvertime('0');
        setAttNotes('');
      }
    }

    setAttDialogOpen(true);
  }, [calendarMap]);

  const handleAttendanceSubmit = useCallback(() => {
    if (!attEmployee || !attDate) return;
    const hwVal = attHoursWorked ? parseFloat(attHoursWorked) : undefined;
    attendanceMutation.mutate({
      empId: attEmployee.id,
      existingId: attExistingId,
      data: {
        date: attDate,
        status: attStatus,
        overtime_hours: parseFloat(attOvertime) || 0,
        hours_worked: hwVal != null && !isNaN(hwVal) ? hwVal : undefined,
        notes: attNotes || undefined,
      },
    });
  }, [attEmployee, attDate, attStatus, attOvertime, attHoursWorked, attNotes, attExistingId, attendanceMutation]);

  // Month nav
  const prevMonth = () => {
    if (month === 1) { setMonth(12); setYear(year - 1); }
    else setMonth(month - 1);
  };
  const nextMonth = () => {
    if (month === 12) { setMonth(1); setYear(year + 1); }
    else setMonth(month + 1);
  };

  const daysInMonth = new Date(year, month, 0).getDate();

  // ── Render ──────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{isStaffView ? 'Production Staff' : 'Employees'}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {isStaffView ? 'Manage production staff, attendance, and payroll' : 'Manage employees, attendance, and payroll'}
          </p>
        </div>
        <div className="flex gap-2">
          {activeTab === 'employees' && (
            <Button onClick={openCreate}>+ Add Employee</Button>
          )}
        </div>
      </div>

      {/* Factory selector */}
      <Card>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
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
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            )}
          </div>
          {(activeTab === 'attendance' || activeTab === 'payroll') && (
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={prevMonth}>&larr;</Button>
              <span className="min-w-[160px] text-center text-lg font-semibold text-gray-900">
                {MONTH_NAMES[month - 1]} {year}
              </span>
              <Button variant="secondary" size="sm" onClick={nextMonth}>&rarr;</Button>
            </div>
          )}
        </div>
      </Card>

      {/* Tabs */}
      <Tabs
        tabs={[
          { id: 'employees', label: 'Employee List' },
          { id: 'attendance', label: 'Attendance' },
          { id: 'payroll', label: 'Payroll Summary' },
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
      />

      {/* Tab Content */}
      {activeTab === 'employees' && (
        <EmployeeListTab
          employees={employees}
          loading={employeesLoading}
          showInactive={showInactive}
          onToggleInactive={() => setShowInactive(!showInactive)}
          onEdit={openEdit}
          onDeactivate={(emp) => deactivateMutation.mutate(emp.id)}
        />
      )}

      {activeTab === 'attendance' && (
        <AttendanceTab
          employees={employees}
          attendanceData={attendanceData ?? {}}
          loading={attendanceLoading || employeesLoading}
          year={year}
          month={month}
          daysInMonth={daysInMonth}
          onCellClick={openAttendanceDialog}
          calendarMap={calendarMap}
          workingDaysData={workingDaysData ?? null}
        />
      )}

      {activeTab === 'payroll' && (
        <PayrollTab
          data={payrollData?.items ?? []}
          loading={payrollLoading}
          year={year}
          month={month}
          factoryId={factoryId}
        />
      )}

      {/* Employee Create/Edit Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        title={editingEmployee ? 'Edit Employee' : 'Add Employee'}
        className="w-full max-w-lg"
      >
        <div className="space-y-4 max-h-[70vh] overflow-y-auto">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Full Name *"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
            />
            <Input
              label="Short Name"
              placeholder="Nickname"
              value={(formData as any).short_name ?? ''}
              onChange={(e) => setFormData({ ...formData, short_name: e.target.value } as any)}
            />
            <Input
              label="Position *"
              placeholder="e.g. Glazer, Kiln Operator"
              value={formData.position}
              onChange={(e) => setFormData({ ...formData, position: e.target.value })}
            />
            <Input
              label="Phone"
              value={formData.phone ?? ''}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            />
            <Input
              label="Email"
              type="email"
              value={(formData as any).email ?? ''}
              onChange={(e) => setFormData({ ...formData, email: e.target.value } as any)}
            />
            <Input
              label="Birth Date"
              type="date"
              value={(formData as any).birth_date ?? ''}
              onChange={(e) => setFormData({ ...formData, birth_date: e.target.value } as any)}
            />
            <Input
              label="Hire Date"
              type="date"
              value={formData.hire_date ?? ''}
              onChange={(e) => setFormData({ ...formData, hire_date: e.target.value })}
            />
            <div className="flex items-center gap-2 pt-5">
              <input
                type="checkbox"
                id="has_own_bpjs"
                checked={(formData as any).has_own_bpjs ?? false}
                onChange={(e) => setFormData({ ...formData, has_own_bpjs: e.target.checked } as any)}
                className="h-4 w-4 rounded border-gray-300"
              />
              <label htmlFor="has_own_bpjs" className="text-sm text-gray-700">Has own BPJS</label>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Employment Type</label>
              <select
                value={formData.employment_type}
                onChange={(e) => setFormData({ ...formData, employment_type: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {EMPLOYMENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Employment Category</label>
              <select
                value={(formData as any).employment_category || 'formal'}
                onChange={(e) => setFormData({ ...formData, employment_category: e.target.value } as any)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {EMPLOYMENT_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Department</label>
              <select
                value={(formData as any).department || 'production'}
                onChange={(e) => setFormData({ ...formData, department: e.target.value } as any)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {DEPARTMENTS.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Work Schedule</label>
              <select
                value={(formData as any).work_schedule || 'six_day'}
                onChange={(e) => setFormData({ ...formData, work_schedule: e.target.value } as any)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {WORK_SCHEDULES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">BPJS Mode</label>
              <select
                value={(formData as any).bpjs_mode || 'company_pays'}
                onChange={(e) => setFormData({ ...formData, bpjs_mode: e.target.value } as any)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {BPJS_MODES.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Pay Period</label>
              <select
                value={(formData as any).pay_period || 'calendar_month'}
                onChange={(e) => setFormData({ ...formData, pay_period: e.target.value } as any)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {PAY_PERIODS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
          </div>

          <hr className="my-2" />
          <p className="text-sm font-medium text-gray-700">Salary & Allowances (IDR/month)</p>
          <div className="grid grid-cols-2 gap-4">
            {(["base_salary", "allowance_bike", "allowance_housing", "allowance_food", "allowance_bpjs", "allowance_other"] as const).map((field) => {
              const labels: Record<string, string> = {
                base_salary: "Base Salary", allowance_bike: "Bike Allowance",
                allowance_housing: "Housing Allowance", allowance_food: "Food Allowance",
                allowance_bpjs: "BPJS", allowance_other: "Other Allowance",
              };
              const val = (formData as any)[field] ?? 0;
              const display = Number(val).toLocaleString('id-ID');
              return (
                <div key={field}>
                  <label className="mb-1 block text-sm font-medium text-gray-700">{labels[field]}</label>
                  <div className="relative">
                    <input
                      type="text"
                      inputMode="numeric"
                      className="w-full rounded-md border border-gray-300 px-3 py-2 pr-14 text-sm focus:border-blue-500 focus:outline-none"
                      value={display}
                      onChange={(e) => {
                        const raw = e.target.value.replace(/\D/g, '');
                        setFormData({ ...formData, [field]: parseInt(raw) || 0 } as any);
                      }}
                    />
                    <span className="absolute inset-y-0 right-0 flex items-center pr-3 text-xs text-gray-400">IDR</span>
                  </div>
                </div>
              );
            })}
            <div className="col-span-2">
              <Input
                label="Other Allowance Note"
                placeholder="Description for other allowance"
                value={formData.allowance_other_note ?? ''}
                onChange={(e) => setFormData({ ...formData, allowance_other_note: e.target.value })}
              />
            </div>
          </div>

          {formError && <p className="text-sm text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeDialog}>Cancel</Button>
            <Button
              onClick={handleSubmit}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {(createMutation.isPending || updateMutation.isPending) ? 'Saving...' : editingEmployee ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Attendance Record Dialog */}
      <Dialog
        open={attDialogOpen}
        onClose={() => { setAttDialogOpen(false); setAttExistingId(null); }}
        title={attExistingId ? 'Edit Attendance' : 'Record Attendance'}
        className="w-full max-w-md"
      >
        <div className="space-y-4">
          <div className="rounded-lg bg-gray-50 px-3 py-2 text-sm">
            <span className="font-medium text-gray-700">Employee:</span>{' '}
            <span className="text-gray-900">{attEmployee?.full_name}</span>
            {' | '}
            <span className="font-medium text-gray-700">Date:</span>{' '}
            <span className="text-gray-900">{attDate}</span>
          </div>
          {/* Overtime warning for non-working days */}
          {(() => {
            if (!attDate) return null;
            const d = new Date(attDate);
            const isSun = d.getDay() === 0;
            const cal = calendarMap.get(attDate);
            const nonWorking = cal ? !cal.is_working_day : isSun;
            if (!nonWorking) return null;
            return (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                <strong>Overtime day</strong> — {cal?.holiday_name ?? (isSun ? 'Sunday' : 'Non-working day')}.
                This attendance will be counted as overtime.
              </div>
            );
          })()}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Status</label>
            <div className="flex gap-2">
              {ATTENDANCE_STATUSES.map((s) => (
                <button
                  key={s.value}
                  onClick={() => setAttStatus(s.value)}
                  className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    attStatus === s.value
                      ? s.color + ' ring-2 ring-offset-1 ring-gray-400'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {s.value.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
          <Input
            label="Overtime Hours"
            type="number"
            value={attOvertime}
            onChange={(e) => setAttOvertime(e.target.value)}
          />
          <div>
            <Input
              label="Hours Worked"
              type="number"
              step="0.5"
              min="0"
              max="8"
              placeholder="Leave empty for full day"
              value={attHoursWorked}
              onChange={(e) => setAttHoursWorked(e.target.value)}
            />
            <p className="mt-1 text-xs text-gray-500">
              Leave empty = full working day. Enter hours if employee came late or left early (e.g. 5 = worked 5h out of 7/8h standard).
            </p>
          </div>
          <Input
            label="Notes"
            value={attNotes}
            onChange={(e) => setAttNotes(e.target.value)}
          />
          {formError && <p className="text-sm text-red-600">{formError}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setAttDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleAttendanceSubmit}
              disabled={attendanceMutation.isPending}
            >
              {attendanceMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

// ── Employee List Tab ────────────────────────────────────────

function EmployeeListTab({
  employees,
  loading,
  showInactive,
  onToggleInactive,
  onEdit,
  onDeactivate,
}: {
  employees: Employee[];
  loading: boolean;
  showInactive: boolean;
  onToggleInactive: () => void;
  onEdit: (emp: Employee) => void;
  onDeactivate: (emp: Employee) => void;
}) {
  if (loading) {
    return <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>;
  }

  return (
    <Card>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-gray-500">{employees.length} employee{employees.length !== 1 ? 's' : ''}</p>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={onToggleInactive}
            className="rounded border-gray-300"
          />
          Show inactive
        </label>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-xs font-medium uppercase text-gray-500">
            <tr>
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Position</th>
              <th className="px-3 py-2 text-left">Phone</th>
              <th className="px-3 py-2 text-left">Type</th>
              <th className="px-3 py-2 text-left">Hire Date</th>
              <th className="px-3 py-2 text-right">Base Salary</th>
              <th className="px-3 py-2 text-right">Total Allow.</th>
              <th className="px-3 py-2 text-center">Status</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {employees.map((emp) => {
              const totalAllow = emp.allowance_bike + emp.allowance_housing + emp.allowance_food + emp.allowance_bpjs + emp.allowance_other;
              return (
                <tr key={emp.id} className={emp.is_active ? 'bg-white' : 'bg-gray-50 opacity-60'}>
                  <td className="px-3 py-2 font-medium text-gray-900">
                    {emp.full_name}
                    {emp.short_name && <span className="ml-1 text-xs text-gray-400">({emp.short_name})</span>}
                  </td>
                  <td className="px-3 py-2 text-gray-600">{emp.position}</td>
                  <td className="px-3 py-2 text-gray-600">{emp.phone || '-'}</td>
                  <td className="px-3 py-2 text-gray-600 capitalize">{emp.employment_type.replace('_', ' ')}</td>
                  <td className="px-3 py-2 text-gray-600">{emp.hire_date || '-'}</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-700">{formatIDR(emp.base_salary)}</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-700">{formatIDR(totalAllow)}</td>
                  <td className="px-3 py-2 text-center">
                    <Badge status={emp.is_active ? 'active' : 'inactive'} label={emp.is_active ? 'Active' : 'Inactive'} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="secondary" size="sm" onClick={() => onEdit(emp)}>Edit</Button>
                      {emp.is_active && (
                        <Button
                          variant="secondary"
                          size="sm"
                          className="text-red-600 hover:text-red-700"
                          onClick={() => onDeactivate(emp)}
                        >
                          Deactivate
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {employees.length === 0 && (
              <tr>
                <td colSpan={9} className="py-8 text-center text-gray-400">
                  No employees found. Add one to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ── Attendance Tab ───────────────────────────────────────────

function AttendanceTab({
  employees,
  attendanceData,
  loading,
  year,
  month,
  daysInMonth,
  onCellClick,
  calendarMap,
  workingDaysData,
}: {
  employees: Employee[];
  attendanceData: Record<string, AttendanceRecord[]>;
  loading: boolean;
  year: number;
  month: number;
  daysInMonth: number;
  onCellClick: (emp: Employee, dateStr: string, existingRecord?: { id?: string; status: string; overtime_hours?: number; hours_worked?: number | null; notes?: string }) => void;
  calendarMap: Map<string, CalendarEntry>;
  workingDaysData: WorkingDaysResponse | null;
}) {
  if (loading) {
    return <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>;
  }

  // Build attendance lookup: employeeId -> date -> record
  const lookup = useMemo(() => {
    const map: Record<string, Record<string, AttendanceRecord>> = {};
    for (const [empId, records] of Object.entries(attendanceData)) {
      map[empId] = {};
      for (const rec of records) {
        map[empId][rec.date] = rec;
      }
    }
    return map;
  }, [attendanceData]);

  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);

  return (
    <Card>
      <div className="mb-3 flex items-center gap-4 text-xs text-gray-500">
        <span>Click a cell to record attendance.</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-emerald-100" /> Present</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-red-100" /> Absent</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-yellow-100" /> Sick</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-blue-100" /> Leave</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-orange-100" /> Half</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              <th className="sticky left-0 z-10 bg-gray-50 px-2 py-1.5 text-left font-medium text-gray-600 min-w-[140px]">
                Employee
              </th>
              {days.map((d) => {
                const dateStr = toISO(year, month, d);
                const dateObj = new Date(year, month - 1, d);
                const isSunday = dateObj.getDay() === 0;
                const calEntry = calendarMap.get(dateStr);
                // Determine day type: holiday (from calendar), Sunday, or working day
                const isHoliday = calEntry ? !calEntry.is_working_day : false;
                const isCalendarWorkingDay = calEntry ? calEntry.is_working_day : !isSunday;

                let headerBg = '';
                let headerText = 'text-gray-500';
                if (isHoliday && !isSunday) {
                  // Explicit holiday from calendar
                  headerBg = 'bg-red-50';
                  headerText = 'text-red-600 font-semibold';
                } else if (isSunday && !isCalendarWorkingDay) {
                  // Regular Sunday (non-working)
                  headerBg = 'bg-gray-100';
                  headerText = 'text-gray-400';
                } else if (isSunday && isCalendarWorkingDay) {
                  // Sunday overridden to working day (overtime)
                  headerBg = 'bg-amber-50';
                  headerText = 'text-amber-600 font-semibold';
                } else if (isCalendarWorkingDay) {
                  // Normal working day
                  headerBg = 'bg-emerald-50';
                  headerText = 'text-emerald-700';
                }

                const tooltip = calEntry?.holiday_name
                  ? calEntry.holiday_name
                  : isSunday
                    ? 'Sunday'
                    : 'Working day';

                return (
                  <th
                    key={d}
                    className={`px-0.5 py-1.5 text-center font-medium min-w-[28px] ${headerBg} ${headerText}`}
                    title={tooltip}
                  >
                    {d}
                  </th>
                );
              })}
              <th className="px-2 py-1.5 text-center font-medium text-gray-600">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {employees.filter((e) => e.is_active).map((emp) => {
              const empRecords = lookup[emp.id] ?? {};
              let presentCount = 0;
              return (
                <tr key={emp.id}>
                  <td className="sticky left-0 z-10 bg-white px-2 py-1 font-medium text-gray-900 border-r">
                    {emp.full_name}
                  </td>
                  {days.map((d) => {
                    const dateStr = toISO(year, month, d);
                    const record = empRecords[dateStr];
                    if (record?.status === 'present') {
                      if (record.hours_worked != null) {
                        // Partial day: count fraction (assume 7h for 6-day, 8h for 5-day — use 7.5 avg)
                        presentCount += Math.min(record.hours_worked / 7.5, 1);
                      } else {
                        presentCount++;
                      }
                    }
                    if (record?.status === 'half_day') presentCount += 0.5;
                    const statusInfo = record
                      ? ATTENDANCE_STATUSES.find((s) => s.value === record.status)
                      : null;

                    // Calendar-aware styling for empty cells
                    const dateObj = new Date(year, month - 1, d);
                    const isSunday = dateObj.getDay() === 0;
                    const calEntry = calendarMap.get(dateStr);
                    const isNonWorking = calEntry
                      ? !calEntry.is_working_day
                      : isSunday;

                    // Empty cell style: working days show light bg, non-working show striped/dim
                    const emptyCellClass = isNonWorking
                      ? 'bg-gray-100 text-gray-200 hover:bg-gray-200'
                      : 'bg-gray-50 text-gray-300 hover:bg-gray-100';

                    const cellTitle = record
                      ? `${record.status}${record.hours_worked != null ? ` (${record.hours_worked}h)` : ''}${record.overtime_hours ? ` +${record.overtime_hours}h OT` : ''}`
                      : isNonWorking
                        ? (calEntry?.holiday_name ?? 'Non-working day') + ' (overtime if recorded)'
                        : 'Click to record';

                    return (
                      <td key={d} className="px-0.5 py-1 text-center">
                        <button
                          onClick={() => onCellClick(emp, dateStr, record ?? undefined)}
                          className={`inline-flex h-6 w-6 items-center justify-center rounded text-[10px] font-bold transition-colors ${
                            statusInfo
                              ? statusInfo.color
                              : emptyCellClass
                          }`}
                          title={cellTitle}
                        >
                          {statusInfo?.label ?? (isNonWorking ? '\u00B7' : '-')}
                        </button>
                      </td>
                    );
                  })}
                  <td className="px-2 py-1 text-center font-semibold text-gray-700">
                    {presentCount}
                  </td>
                </tr>
              );
            })}
            {employees.filter((e) => e.is_active).length === 0 && (
              <tr>
                <td colSpan={daysInMonth + 2} className="py-8 text-center text-gray-400">
                  No active employees.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {/* Working Days Summary from Factory Calendar */}
      <div className="mt-4 flex flex-wrap items-center gap-6 border-t pt-3">
        {workingDaysData ? (
          <>
            <div className="flex items-center gap-2 text-sm">
              <span className="inline-block h-3 w-3 rounded bg-emerald-200" />
              <span className="text-gray-600">5-day:</span>
              <span className="font-bold text-emerald-700">{workingDaysData.working_days_5day ?? workingDaysData.working_days}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="inline-block h-3 w-3 rounded bg-blue-200" />
              <span className="text-gray-600">6-day:</span>
              <span className="font-bold text-blue-600">{workingDaysData.working_days_6day ?? workingDaysData.working_days}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="inline-block h-3 w-3 rounded bg-red-200" />
              <span className="text-gray-600">Holidays:</span>
              <span className="font-bold text-red-600">{workingDaysData.holidays}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="inline-block h-3 w-3 rounded bg-gray-200" />
              <span className="text-gray-600">Sundays:</span>
              <span className="font-bold text-gray-500">{workingDaysData.sundays}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-600">Total days:</span>
              <span className="font-semibold text-gray-700">{workingDaysData.total_days}</span>
            </div>
          </>
        ) : (
          <span className="text-xs text-gray-400">Loading calendar data...</span>
        )}
      </div>
    </Card>
  );
}

// ── Payroll Tab ──────────────────────────────────────────────

function PayrollTab({
  data,
  loading,
  year,
  month,
  factoryId,
}: {
  data: PayrollSummaryItem[];
  loading: boolean;
  year: number;
  month: number;
  factoryId?: string;
}) {
  const [pdfLoading, setPdfLoading] = useState(false);
  const [slipLoading, setSlipLoading] = useState<string | null>(null);

  const downloadPayslip = async (employeeId: string, employeeName: string) => {
    setSlipLoading(employeeId);
    try {
      const blob = await employeesApi.payrollPdfEmployee({ employee_id: employeeId, year, month });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `payslip_${employeeName.replace(/\s+/g, '_')}_${year}_${String(month).padStart(2, '0')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Payslip download failed', e);
    } finally {
      setSlipLoading(null);
    }
  };

  const downloadPdf = async () => {
    setPdfLoading(true);
    try {
      const blob = await employeesApi.payrollPdf({ factory_id: factoryId, year, month });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `payroll_${year}_${String(month).padStart(2, '0')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('PDF download failed', e);
    } finally {
      setPdfLoading(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>;
  }

  // Support both old (gross_total) and new (gross_salary) API response format
  const getGross = (r: any) => r.gross_salary ?? r.gross_total ?? 0;
  const getNet = (r: any) => r.net_salary ?? 0;
  const getDays = (r: any) => r.present_days ?? r.working_days ?? 0;
  const grandGross = data.reduce((sum, r) => sum + getGross(r), 0);
  const grandNet = data.reduce((sum, r) => sum + getNet(r), 0);

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between flex-wrap gap-2">
        <p className="text-sm text-gray-500">
          Payroll for {MONTH_NAMES[month - 1]} {year} -- {data.length} employees
        </p>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-gray-700">Gross: <strong>{formatIDR(grandGross)}</strong></span>
          {grandNet > 0 && <span className="text-green-700">Net: <strong>{formatIDR(grandNet)}</strong></span>}
          <Button variant="secondary" onClick={downloadPdf} disabled={pdfLoading || data.length === 0}>
            {pdfLoading ? 'Generating...' : '↓ PDF'}
          </Button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-xs font-medium uppercase text-gray-500">
            <tr>
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Position</th>
              <th className="px-3 py-2 text-right">Base</th>
              <th className="px-3 py-2 text-right">Allowances</th>
              <th className="px-3 py-2 text-center">Days</th>
              <th className="px-3 py-2 text-center">Absent</th>
              <th className="px-3 py-2 text-center">OT</th>
              <th className="px-3 py-2 text-right">OT Pay</th>
              <th className="px-3 py-2 text-right">Gross</th>
              <th className="px-3 py-2 text-right">Deductions</th>
              <th className="px-3 py-2 text-right font-bold">Net</th>
              <th className="px-3 py-2 text-center">Slip</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.map((row: any) => (
              <tr key={row.employee_id} className="bg-white">
                <td className="px-3 py-2 font-medium text-gray-900">{row.full_name}</td>
                <td className="px-3 py-2 text-gray-600">{row.position}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-700">{formatIDR(row.prorated_salary ?? row.base_salary)}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-700">{formatIDR(row.prorated_allowances ?? row.total_allowances)}</td>
                <td className="px-3 py-2 text-center text-emerald-700 font-semibold">
                  {getDays(row)}{row.working_days_in_month ? `/${row.working_days_in_month}` : ''}
                </td>
                <td className="px-3 py-2 text-center text-red-600">{row.absent_days || '-'}</td>
                <td className="px-3 py-2 text-center text-gray-600">{row.overtime_hours || '-'}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-700">{(row.overtime_pay ?? 0) > 0 ? formatIDR(row.overtime_pay) : '-'}</td>
                <td className="px-3 py-2 text-right font-mono font-medium text-gray-800">{formatIDR(getGross(row))}</td>
                <td className="px-3 py-2 text-right font-mono text-red-600">{(row.total_deductions ?? 0) > 0 ? formatIDR(row.total_deductions) : '-'}</td>
                <td className="px-3 py-2 text-right font-mono font-bold text-green-700">{formatIDR(getNet(row))}</td>
                <td className="px-3 py-2 text-center">
                  <button
                    onClick={() => downloadPayslip(row.employee_id, row.full_name)}
                    disabled={slipLoading === row.employee_id}
                    className="rounded px-2 py-0.5 text-xs font-medium text-blue-600 hover:bg-blue-50 disabled:opacity-40"
                    title="Download payslip"
                  >
                    {slipLoading === row.employee_id ? '...' : '↓'}
                  </button>
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={12} className="py-8 text-center text-gray-400">
                  No payroll data for this period.
                </td>
              </tr>
            )}
          </tbody>
          {data.length > 0 && (
            <tfoot className="border-t-2 border-gray-300">
              <tr className="bg-gray-50 font-semibold">
                <td className="px-3 py-2 text-gray-700" colSpan={2}>TOTAL</td>
                <td className="px-3 py-2" colSpan={4}></td>
                <td className="px-3 py-2" colSpan={1}></td>
                <td className="px-3 py-2 text-right font-mono text-gray-700">
                  {formatIDR(data.reduce((s, r: any) => s + (r.overtime_pay ?? 0), 0))}
                </td>
                <td className="px-3 py-2 text-right font-mono font-bold text-gray-900">
                  {formatIDR(grandGross)}
                </td>
                <td className="px-3 py-2 text-right font-mono text-red-600">
                  {formatIDR(data.reduce((s, r: any) => s + (r.total_deductions ?? 0), 0))}
                </td>
                <td className="px-3 py-2 text-right font-mono font-bold text-green-700">
                  {formatIDR(grandNet)}
                </td>
                <td className="px-3 py-2"></td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </Card>
  );
}
