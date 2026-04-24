import { useState, useMemo, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';
import {
  employeesApi,
  type Employee,
  type EmployeeCreatePayload,
  type EmployeeUpdatePayload,
  type AttendanceRecord,
  type AdvanceRecord,
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

  // Termination dialog
  const [terminateDialogOpen, setTerminateDialogOpen] = useState(false);
  const [terminateEmployee, setTerminateEmployee] = useState<Employee | null>(null);
  const [terminateDate, setTerminateDate] = useState('');

  // Advance dialog
  const [advDialogOpen, setAdvDialogOpen] = useState(false);
  const [advEmployee, setAdvEmployee] = useState<Employee | null>(null);
  const [advExistingId, setAdvExistingId] = useState<string | null>(null);
  const [advDate, setAdvDate] = useState('');
  const [advAmount, setAdvAmount] = useState('');
  const [advNotes, setAdvNotes] = useState('');
  const [advFormError, setAdvFormError] = useState('');

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

  // Advances for all employees for this month
  const { data: advancesData } = useQuery({
    queryKey: ['advances-grid', factoryId, year, month],
    queryFn: async () => {
      if (!employees.length) return {};
      const results: Record<string, AdvanceRecord[]> = {};
      for (const emp of employees) {
        const res = await employeesApi.getAdvances(emp.id, { year, month });
        results[emp.id] = res.items;
      }
      return results;
    },
    enabled: !!factoryId && employees.length > 0 && activeTab === 'attendance',
  });

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

  const terminateMutation = useMutation({
    mutationFn: ({ id, termination_date }: { id: string; termination_date: string }) =>
      employeesApi.update(id, { termination_date, is_active: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      setTerminateDialogOpen(false);
      setTerminateEmployee(null);
      setTerminateDate('');
    },
  });

  const reinstateMutation = useMutation({
    mutationFn: (id: string) =>
      employeesApi.update(id, { termination_date: '', is_active: true } as any),
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

  const deleteAttendanceMutation = useMutation({
    mutationFn: (attendanceId: string) => employeesApi.deleteAttendance(attendanceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attendance-grid'] });
      queryClient.invalidateQueries({ queryKey: ['payroll-summary'] });
      setAttDialogOpen(false);
      setAttExistingId(null);
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? 'Failed to delete attendance');
    },
  });

  const advanceMutation = useMutation({
    mutationFn: ({ empId, existingId, data }: { empId: string; existingId: string | null; data: { date: string; amount: number; notes?: string } }) =>
      existingId
        ? employeesApi.updateAdvance(existingId, { amount: data.amount, notes: data.notes, date: data.date })
        : employeesApi.createAdvance(empId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['advances-grid'] });
      queryClient.invalidateQueries({ queryKey: ['payroll-summary'] });
      setAdvDialogOpen(false);
      setAdvExistingId(null);
      setAdvFormError('');
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAdvFormError(detail ?? 'Failed to save advance');
    },
  });

  const deleteAdvanceMutation = useMutation({
    mutationFn: (advId: string) => employeesApi.deleteAdvance(advId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['advances-grid'] });
      queryClient.invalidateQueries({ queryKey: ['payroll-summary'] });
      setAdvDialogOpen(false);
      setAdvExistingId(null);
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAdvFormError(detail ?? 'Failed to delete advance');
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
      termination_date: (emp as any).termination_date ?? '',
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

  const openAdvanceDialog = useCallback((emp: Employee, existing?: AdvanceRecord) => {
    setAdvEmployee(emp);
    setAdvFormError('');
    if (existing) {
      setAdvExistingId(existing.id);
      setAdvDate(existing.date);
      setAdvAmount(String(existing.amount));
      setAdvNotes(existing.notes ?? '');
    } else {
      setAdvExistingId(null);
      setAdvDate(toISO(year, month, new Date().getDate()));
      setAdvAmount('');
      setAdvNotes('');
    }
    setAdvDialogOpen(true);
  }, [year, month]);

  const handleAdvanceSubmit = useCallback(() => {
    if (!advEmployee || !advDate || !advAmount) return;
    const amt = parseFloat(advAmount);
    if (isNaN(amt) || amt <= 0) { setAdvFormError('Enter a valid amount'); return; }
    advanceMutation.mutate({
      empId: advEmployee.id,
      existingId: advExistingId,
      data: { date: advDate, amount: amt, notes: advNotes || undefined },
    });
  }, [advEmployee, advDate, advAmount, advNotes, advExistingId, advanceMutation]);

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
          onTerminate={(emp) => {
            setTerminateEmployee(emp);
            setTerminateDate(new Date().toISOString().split('T')[0]);
            setTerminateDialogOpen(true);
          }}
          onReinstate={(emp) => reinstateMutation.mutate(emp.id)}
        />
      )}

      {activeTab === 'attendance' && (
        <AttendanceTab
          employees={employees}
          attendanceData={attendanceData ?? {}}
          advancesData={advancesData ?? {}}
          loading={attendanceLoading || employeesLoading}
          year={year}
          month={month}
          daysInMonth={daysInMonth}
          onCellClick={openAttendanceDialog}
          onAdvanceClick={openAdvanceDialog}
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
            <Input
              label="Termination Date (last day)"
              type="date"
              value={(formData as any).termination_date ?? ''}
              onChange={(e) => setFormData({ ...formData, termination_date: e.target.value } as any)}
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
          <div className="flex justify-between pt-2">
            {attExistingId ? (
              <Button
                variant="secondary"
                onClick={() => {
                  if (attExistingId && confirm('Delete this attendance record? The cell will become empty.')) {
                    deleteAttendanceMutation.mutate(attExistingId);
                  }
                }}
                disabled={deleteAttendanceMutation.isPending}
                className="text-red-600 hover:bg-red-50 hover:text-red-700"
              >
                {deleteAttendanceMutation.isPending ? 'Deleting...' : 'Reset (delete)'}
              </Button>
            ) : <div />}
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setAttDialogOpen(false)}>Cancel</Button>
              <Button
                onClick={handleAttendanceSubmit}
                disabled={attendanceMutation.isPending}
              >
                {attendanceMutation.isPending ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </div>
        </div>
      </Dialog>

      {/* ── Advance Dialog ── */}
      <Dialog
        open={advDialogOpen}
        onClose={() => { setAdvDialogOpen(false); setAdvExistingId(null); setAdvFormError(''); }}
        title={advExistingId ? 'Edit Advance' : 'Record Advance'}
        className="w-full max-w-sm"
      >
        <div className="space-y-4">
          <div className="rounded-lg bg-gray-50 px-3 py-2 text-sm">
            <span className="font-medium text-gray-700">Employee:</span>{' '}
            <span className="text-gray-900">{advEmployee?.full_name}</span>
          </div>
          <Input
            label="Date"
            type="date"
            value={advDate}
            onChange={(e) => setAdvDate(e.target.value)}
          />
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Amount (IDR)</label>
            <div className="relative">
              <input
                type="text"
                inputMode="numeric"
                className="w-full rounded-md border border-gray-300 px-3 py-2 pr-14 text-sm focus:border-blue-500 focus:outline-none"
                value={advAmount ? Number(advAmount).toLocaleString('id-ID') : ''}
                placeholder="0"
                onChange={(e) => {
                  const raw = e.target.value.replace(/\D/g, '');
                  setAdvAmount(raw);
                }}
              />
              <span className="absolute inset-y-0 right-0 flex items-center pr-3 text-xs text-gray-400">IDR</span>
            </div>
          </div>
          <Input
            label="Notes"
            placeholder="Reason (optional)"
            value={advNotes}
            onChange={(e) => setAdvNotes(e.target.value)}
          />
          {advFormError && <p className="text-sm text-red-600">{advFormError}</p>}
          <div className="flex justify-between pt-2">
            {advExistingId ? (
              <Button
                variant="secondary"
                onClick={() => {
                  if (advExistingId && confirm('Delete this advance record?')) {
                    deleteAdvanceMutation.mutate(advExistingId);
                  }
                }}
                disabled={deleteAdvanceMutation.isPending}
                className="text-red-600 hover:bg-red-50 hover:text-red-700"
              >
                {deleteAdvanceMutation.isPending ? 'Deleting...' : 'Delete'}
              </Button>
            ) : <div />}
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setAdvDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleAdvanceSubmit} disabled={advanceMutation.isPending}>
                {advanceMutation.isPending ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </div>
        </div>
      </Dialog>

      {/* ── Terminate Dialog ── */}
      <Dialog
        open={terminateDialogOpen}
        onClose={() => { setTerminateDialogOpen(false); setTerminateEmployee(null); }}
        title={`Terminate ${terminateEmployee?.full_name ?? ''}`}
      >
        <div className="space-y-4 p-4">
          <p className="text-sm text-gray-600">
            This will mark the employee as terminated and calculate leave compensation in their final payroll.
          </p>
          <Input
            label="Last working day"
            type="date"
            value={terminateDate}
            onChange={(e) => setTerminateDate(e.target.value)}
          />
          {terminateEmployee?.hire_date && (
            <p className="text-xs text-gray-400">
              Hired: {terminateEmployee.hire_date}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => { setTerminateDialogOpen(false); setTerminateEmployee(null); }}>
              Cancel
            </Button>
            <Button
              variant="primary"
              className="bg-red-600 hover:bg-red-700"
              disabled={!terminateDate || terminateMutation.isPending}
              onClick={() => {
                if (terminateEmployee && terminateDate) {
                  terminateMutation.mutate({ id: terminateEmployee.id, termination_date: terminateDate });
                }
              }}
            >
              {terminateMutation.isPending ? 'Processing...' : 'Confirm Termination'}
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
  onTerminate,
  onReinstate,
}: {
  employees: Employee[];
  loading: boolean;
  showInactive: boolean;
  onToggleInactive: () => void;
  onEdit: (emp: Employee) => void;
  onTerminate: (emp: Employee) => void;
  onReinstate: (emp: Employee) => void;
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
                    <Badge status={emp.is_active ? 'active' : 'inactive'} label={emp.is_active ? 'Active' : 'Terminated'} />
                    {(emp as any).termination_date && (
                      <div className="text-[10px] text-gray-400 mt-0.5">{(emp as any).termination_date}</div>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="secondary" size="sm" onClick={() => onEdit(emp)}>Edit</Button>
                      {emp.is_active ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          className="text-red-600 hover:text-red-700"
                          onClick={() => onTerminate(emp)}
                        >
                          Terminate
                        </Button>
                      ) : (
                        <Button
                          variant="secondary"
                          size="sm"
                          className="text-green-600 hover:text-green-700"
                          onClick={() => onReinstate(emp)}
                        >
                          Reinstate
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
  advancesData,
  loading,
  year,
  month,
  daysInMonth,
  onCellClick,
  onAdvanceClick,
  calendarMap,
  workingDaysData,
}: {
  employees: Employee[];
  attendanceData: Record<string, AttendanceRecord[]>;
  advancesData: Record<string, AdvanceRecord[]>;
  loading: boolean;
  year: number;
  month: number;
  daysInMonth: number;
  onCellClick: (emp: Employee, dateStr: string, existingRecord?: { id?: string; status: string; overtime_hours?: number; hours_worked?: number | null; notes?: string }) => void;
  onAdvanceClick: (emp: Employee, existing?: AdvanceRecord) => void;
  calendarMap: Map<string, CalendarEntry>;
  workingDaysData: WorkingDaysResponse | null;
}) {
  const [selectedEmpIds, setSelectedEmpIds] = useState<Set<string>>(new Set());
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false);
  const [bulkStatus, setBulkStatus] = useState('present');
  const [bulkOvertime, setBulkOvertime] = useState('0');
  const [bulkDate, setBulkDate] = useState('');

  if (loading) {
    return <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>;
  }

  // Build attendance lookup: employeeId -> date -> record
  const lookup: Record<string, Record<string, AttendanceRecord>> = {};
  for (const [empId, records] of Object.entries(attendanceData)) {
    lookup[empId] = {};
    for (const rec of records) {
      lookup[empId][rec.date] = rec;
    }
  }

  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const activeEmps = employees.filter((e) => e.is_active);

  const toggleSelectAll = () => {
    if (selectedEmpIds.size === activeEmps.length) {
      setSelectedEmpIds(new Set());
    } else {
      setSelectedEmpIds(new Set(activeEmps.map((e) => e.id)));
    }
  };

  const toggleSelect = (empId: string) => {
    const next = new Set(selectedEmpIds);
    if (next.has(empId)) next.delete(empId); else next.add(empId);
    setSelectedEmpIds(next);
  };

  return (
    <Card>
      {/* Legend + bulk toolbar */}
      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs text-gray-500">
        <span>Click a cell to record attendance.</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-emerald-100" /> Present</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-red-100" /> Absent</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-yellow-100" /> Sick</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-blue-100" /> Leave</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-orange-100" /> Half</span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded bg-emerald-100 ring-1 ring-orange-400 ring-offset-0" />
          <span>+ OT</span>
        </span>
      </div>

      {/* Bulk fill toolbar */}
      {selectedEmpIds.size > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2">
          <span className="text-sm font-medium text-blue-700">{selectedEmpIds.size} selected</span>
          <Button size="sm" onClick={() => setBulkDialogOpen(true)}>
            Fill selected…
          </Button>
          <button
            onClick={() => setSelectedEmpIds(new Set())}
            className="ml-auto text-xs text-blue-500 hover:text-blue-700"
          >
            Clear selection
          </button>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              {/* Select-all checkbox */}
              <th className="sticky left-0 z-10 bg-gray-50 w-6 px-1 py-1.5">
                <input
                  type="checkbox"
                  checked={selectedEmpIds.size === activeEmps.length && activeEmps.length > 0}
                  onChange={toggleSelectAll}
                  className="h-3.5 w-3.5 rounded border-gray-300"
                  title="Select all"
                />
              </th>
              <th className="sticky left-6 z-10 bg-gray-50 px-2 py-1.5 text-left font-medium text-gray-600 min-w-[130px]">
                Employee
              </th>
              {days.map((d) => {
                const dateStr = toISO(year, month, d);
                const dateObj = new Date(year, month - 1, d);
                const isSunday = dateObj.getDay() === 0;
                const isSaturday = dateObj.getDay() === 6;
                const calEntry = calendarMap.get(dateStr);
                const isHoliday = calEntry ? !calEntry.is_working_day : false;
                const isCalendarWorkingDay = calEntry ? calEntry.is_working_day : !isSunday;

                let headerBg = '';
                let headerText = 'text-gray-500';
                if (isHoliday && !isSunday) {
                  headerBg = 'bg-red-50';
                  headerText = 'text-red-600 font-semibold';
                } else if (isSunday && !isCalendarWorkingDay) {
                  headerBg = 'bg-gray-100';
                  headerText = 'text-gray-400';
                } else if (isSunday && isCalendarWorkingDay) {
                  headerBg = 'bg-amber-50';
                  headerText = 'text-amber-600 font-semibold';
                } else if (isSaturday && isCalendarWorkingDay) {
                  headerBg = 'bg-blue-50';
                  headerText = 'text-blue-600 font-semibold';
                } else if (isCalendarWorkingDay) {
                  headerBg = 'bg-emerald-50';
                  headerText = 'text-emerald-700';
                }

                const tooltip = calEntry?.holiday_name ?? (isSunday ? 'Sunday' : isSaturday ? 'Saturday' : 'Working day');

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
              <th className="px-2 py-1.5 text-center font-medium text-gray-600 min-w-[70px]">Days</th>
              <th className="px-2 py-1.5 text-center font-medium text-orange-600 min-w-[50px]">OT h</th>
              <th className="px-2 py-1.5 text-center font-medium text-violet-600 min-w-[50px]">Adv.</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {activeEmps.map((emp) => {
              const empRecords = lookup[emp.id] ?? {};
              const empAdvances = advancesData[emp.id] ?? [];
              const totalAdvances = empAdvances.reduce((s, a) => s + a.amount, 0);
              let presentCount = 0;
              let totalOT = 0;

              // Pre-calculate counts for the whole row
              for (const d of days) {
                const dateStr = toISO(year, month, d);
                const record = empRecords[dateStr];
                if (record?.status === 'present') {
                  presentCount += record.hours_worked != null
                    ? Math.min(record.hours_worked / 7.5, 1)
                    : 1;
                }
                if (record?.status === 'half_day') presentCount += 0.5;
                if (record?.overtime_hours) totalOT += Number(record.overtime_hours);
              }

              const isSelected = selectedEmpIds.has(emp.id);

              return (
                <tr key={emp.id} className={isSelected ? 'bg-blue-50' : undefined}>
                  <td className="sticky left-0 z-10 bg-inherit w-6 px-1 py-1 text-center border-r border-gray-100">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelect(emp.id)}
                      className="h-3.5 w-3.5 rounded border-gray-300"
                    />
                  </td>
                  <td className="sticky left-6 z-10 bg-inherit px-2 py-1 font-medium text-gray-900 border-r">
                    {emp.full_name}
                  </td>
                  {days.map((d) => {
                    const dateStr = toISO(year, month, d);
                    const record = empRecords[dateStr];
                    const statusInfo = record
                      ? ATTENDANCE_STATUSES.find((s) => s.value === record.status)
                      : null;
                    const hasOT = record && Number(record.overtime_hours) > 0;

                    const dateObj = new Date(year, month - 1, d);
                    const isSunday = dateObj.getDay() === 0;
                    const isSaturday = dateObj.getDay() === 6;
                    const calEntry = calendarMap.get(dateStr);
                    const isFiveDaySatOff = isSaturday && emp.work_schedule === 'five_day';
                    const isNonWorking = calEntry
                      ? !calEntry.is_working_day
                      : (isSunday || isFiveDaySatOff);

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
                          className={`relative inline-flex h-6 w-6 items-center justify-center rounded text-[10px] font-bold transition-colors ${
                            statusInfo ? statusInfo.color : emptyCellClass
                          } ${hasOT ? 'ring-2 ring-orange-400 ring-offset-0' : ''}`}
                          title={cellTitle}
                        >
                          {statusInfo?.label ?? (isNonWorking ? '\u00B7' : '-')}
                        </button>
                      </td>
                    );
                  })}
                  {/* Days total */}
                  <td className="px-2 py-1 text-center font-semibold text-gray-700">
                    {Math.round(presentCount * 10) / 10}
                  </td>
                  {/* OT total */}
                  <td className="px-2 py-1 text-center font-semibold text-orange-600">
                    {totalOT > 0 ? totalOT : <span className="text-gray-300">–</span>}
                  </td>
                  {/* Advances */}
                  <td className="px-1 py-1 text-center">
                    <button
                      onClick={() => onAdvanceClick(emp)}
                      title={totalAdvances > 0 ? `Advances: ${formatIDR(totalAdvances)} — click to manage` : 'Add advance'}
                      className={`rounded px-1.5 py-0.5 text-[10px] font-medium transition-colors ${
                        totalAdvances > 0
                          ? 'bg-violet-100 text-violet-700 hover:bg-violet-200'
                          : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                      }`}
                    >
                      {totalAdvances > 0 ? `${(totalAdvances / 1000).toFixed(0)}k` : '+'}
                    </button>
                    {/* Individual advance records as small chips */}
                    {empAdvances.length > 0 && (
                      <div className="mt-0.5 flex flex-col gap-0.5">
                        {empAdvances.map((adv) => (
                          <button
                            key={adv.id}
                            onClick={() => onAdvanceClick(emp, adv)}
                            className="rounded bg-violet-50 px-1 py-0 text-[9px] text-violet-600 hover:bg-violet-100"
                            title={`${adv.date}: ${formatIDR(adv.amount)}${adv.notes ? ' — ' + adv.notes : ''}`}
                          >
                            {adv.date.slice(8)}/{(adv.amount / 1000).toFixed(0)}k
                          </button>
                        ))}
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
            {activeEmps.length === 0 && (
              <tr>
                <td colSpan={daysInMonth + 5} className="py-8 text-center text-gray-400">
                  No active employees.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Working Days Summary */}
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
              <span className="inline-block h-3 w-3 rounded bg-blue-200" />
              <span className="text-gray-600">Saturdays:</span>
              <span className="font-bold text-blue-600">{workingDaysData.saturdays ?? Math.floor(workingDaysData.total_days / 7) + (new Date(year, month - 1, workingDaysData.total_days).getDay() >= 6 ? 1 : 0)}</span>
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

      {/* Bulk Fill Dialog */}
      {bulkDialogOpen && (
        <BulkFillDialog
          open={bulkDialogOpen}
          onClose={() => setBulkDialogOpen(false)}
          selectedEmployees={activeEmps.filter((e) => selectedEmpIds.has(e.id))}
          year={year}
          month={month}
          daysInMonth={daysInMonth}
          lookup={lookup}
          calendarMap={calendarMap}
          onApplied={() => {
            setBulkDialogOpen(false);
            setSelectedEmpIds(new Set());
          }}
        />
      )}
    </Card>
  );
}

// ── Bulk Fill Dialog ─────────────────────────────────────────

function BulkFillDialog({
  open,
  onClose,
  selectedEmployees,
  year,
  month,
  daysInMonth,
  lookup,
  calendarMap,
  onApplied,
}: {
  open: boolean;
  onClose: () => void;
  selectedEmployees: Employee[];
  year: number;
  month: number;
  daysInMonth: number;
  lookup: Record<string, Record<string, AttendanceRecord>>;
  calendarMap: Map<string, CalendarEntry>;
  onApplied: () => void;
}) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('present');
  const [overtime, setOvertime] = useState('0');
  const [dateFrom, setDateFrom] = useState(toISO(year, month, 1));
  const [dateTo, setDateTo] = useState(toISO(year, month, daysInMonth));
  const [skipNonWorking, setSkipNonWorking] = useState(true);
  const [skipExisting, setSkipExisting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleApply = async () => {
    setSaving(true);
    setError('');
    try {
      const from = new Date(dateFrom);
      const to = new Date(dateTo);
      const days: string[] = [];
      const cur = new Date(from);
      while (cur <= to) {
        days.push(cur.toISOString().split('T')[0]);
        cur.setDate(cur.getDate() + 1);
      }

      for (const emp of selectedEmployees) {
        for (const dateStr of days) {
          const dateObj = new Date(dateStr);
          const isSunday = dateObj.getDay() === 0;
          const calEntry = calendarMap.get(dateStr);
          const isNonWorking = calEntry ? !calEntry.is_working_day : isSunday;
          if (skipNonWorking && isNonWorking) continue;

          const existing = lookup[emp.id]?.[dateStr];
          if (skipExisting && existing) continue;

          const payload = {
            date: dateStr,
            status,
            overtime_hours: parseFloat(overtime) || 0,
          };

          if (existing) {
            await employeesApi.updateAttendance(existing.id, payload);
          } else {
            await employeesApi.recordAttendance(emp.id, payload);
          }
        }
      }
      queryClient.invalidateQueries({ queryKey: ['attendance-grid'] });
      queryClient.invalidateQueries({ queryKey: ['payroll-summary'] });
      onApplied();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? 'Failed to apply bulk attendance');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Bulk Fill Attendance" className="w-full max-w-md">
      <div className="space-y-4">
        <div className="rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-700">
          Applying to <strong>{selectedEmployees.length}</strong> employee{selectedEmployees.length !== 1 ? 's' : ''}:{' '}
          {selectedEmployees.map((e) => e.full_name).join(', ')}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Status</label>
          <div className="flex flex-wrap gap-2">
            {ATTENDANCE_STATUSES.map((s) => (
              <button
                key={s.value}
                onClick={() => setStatus(s.value)}
                className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  status === s.value
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
          min="0"
          step="0.5"
          value={overtime}
          onChange={(e) => setOvertime(e.target.value)}
        />

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={skipNonWorking}
              onChange={(e) => setSkipNonWorking(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            Skip non-working days (holidays, Sundays)
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={skipExisting}
              onChange={(e) => setSkipExisting(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            Skip days that already have a record
          </label>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={handleApply} disabled={saving}>
            {saving ? 'Applying…' : `Apply to ${selectedEmployees.length} employee${selectedEmployees.length !== 1 ? 's' : ''}`}
          </Button>
        </div>
      </div>
    </Dialog>
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
              <tr key={row.employee_id} className={`${row.is_termination_month ? 'bg-red-50' : 'bg-white'}`}>
                <td className="px-3 py-2 font-medium text-gray-900">
                  {row.full_name}
                  {row.is_termination_month && (
                    <span className="ml-1.5 inline-flex items-center rounded-full bg-red-100 px-1.5 py-0.5 text-[10px] font-semibold text-red-700">
                      TERMINATION
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-gray-600">{row.position}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-700">{formatIDR(row.prorated_salary ?? row.base_salary)}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-700">{formatIDR(row.prorated_allowances ?? row.total_allowances)}</td>
                <td className="px-3 py-2 text-center text-emerald-700 font-semibold">
                  {getDays(row)}{row.working_days_in_month ? `/${row.working_days_in_month}` : ''}
                </td>
                <td className="px-3 py-2 text-center text-red-600">{row.absent_days || '-'}</td>
                <td className="px-3 py-2 text-center text-gray-600">{row.overtime_hours || '-'}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-700">{(row.overtime_pay ?? 0) > 0 ? formatIDR(row.overtime_pay) : '-'}</td>
                <td className="px-3 py-2 text-right font-mono font-medium text-gray-800">
                  {formatIDR(getGross(row))}
                  {(row.leave_compensation ?? 0) > 0 && (
                    <div className="text-[10px] text-orange-600 mt-0.5">
                      incl. leave comp. {formatIDR(row.leave_compensation)} ({row.leave_days_entitled}d)
                    </div>
                  )}
                </td>
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
