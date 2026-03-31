import { useState, useMemo, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  employeesApi,
  type Employee,
  type EmployeeCreatePayload,
  type EmployeeUpdatePayload,
  type PayrollItem,
  type PayrollTotals,
} from '@/api/employees';
import { useFactories } from '@/hooks/useFactories';
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

const DEPARTMENTS = [
  { value: 'production', label: 'Production' },
  { value: 'sales', label: 'Sales' },
  { value: 'administration', label: 'Administration' },
];

const WORK_SCHEDULES = [
  { value: 'five_day', label: '5-day (Mon-Fri)' },
  { value: 'six_day', label: '6-day (Mon-Sat)' },
];

const BPJS_MODES = [
  { value: 'company_pays', label: 'Company Pays' },
  { value: 'reimburse', label: 'Reimburse' },
];

const EMPLOYMENT_CATEGORIES = [
  { value: 'formal', label: 'Formal' },
  { value: 'contractor', label: 'Contractor' },
];

const PAY_PERIODS = [
  { value: 'calendar_month', label: 'Calendar Month (paid last day)' },
  { value: '25_to_24', label: '25th–24th (paid on 25th)' },
];

const DEPARTMENT_FILTERS = ['all', 'production', 'sales', 'administration'];

function formatIDR(n: number) {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0,
  }).format(n);
}

function formatNum(n: number, decimals = 0) {
  return new Intl.NumberFormat('id-ID', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

// ── Main Component ───────────────────────────────────────────

export default function CeoEmployeesPage() {
  const queryClient = useQueryClient();
  const today = new Date();

  // State
  const [activeTab, setActiveTab] = useState('employees');
  const [factoryFilter, setFactoryFilter] = useState('all');
  const [departmentFilter, setDepartmentFilter] = useState('all');
  const [showInactive, setShowInactive] = useState(false);
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [formError, setFormError] = useState('');

  // Form state
  const [formData, setFormData] = useState<EmployeeCreatePayload>({
    factory_id: '',
    full_name: '',
    position: '',
    phone: '',
    hire_date: '',
    employment_type: 'full_time',
    department: 'production',
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

  // Factories
  const { data: factoriesData, isLoading: factoriesLoading } = useFactories();
  const factories = factoriesData?.items ?? [];

  // ── Queries ─────────────────────────────────────────────────

  // Employees — fetch all (no factory filter at API level for CEO, filter locally)
  const { data: employeesData, isLoading: employeesLoading } = useQuery({
    queryKey: ['employees', 'all', showInactive],
    queryFn: () => employeesApi.list({
      is_active: showInactive ? undefined : true,
      per_page: 500,
    }),
  });

  const allEmployees = employeesData?.items ?? [];

  // Apply filters locally
  const filteredEmployees = useMemo(() => {
    let result = allEmployees;
    if (factoryFilter !== 'all') {
      result = result.filter((e) => e.factory_id === factoryFilter);
    }
    if (departmentFilter !== 'all') {
      result = result.filter((e) => e.department === departmentFilter);
    }
    return result;
  }, [allEmployees, factoryFilter, departmentFilter]);

  // Payroll
  const { data: payrollData, isLoading: payrollLoading } = useQuery({
    queryKey: ['payroll-summary', factoryFilter === 'all' ? undefined : factoryFilter, year, month],
    queryFn: () => employeesApi.payrollSummary({
      factory_id: factoryFilter === 'all' ? undefined : factoryFilter,
      year,
      month,
    }),
    enabled: activeTab === 'payroll',
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

  // ── Handlers ────────────────────────────────────────────────

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    setEditingEmployee(null);
    setFormError('');
  }, []);

  const openCreate = useCallback(() => {
    setEditingEmployee(null);
    setFormData({
      factory_id: factories.length > 0 ? factories[0].id : '',
      full_name: '',
      position: '',
      phone: '',
      hire_date: '',
      employment_type: 'full_time',
      department: 'production',
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
    setFormError('');
    setDialogOpen(true);
  }, [factories]);

  const openEdit = useCallback((emp: Employee) => {
    setEditingEmployee(emp);
    setFormData({
      factory_id: emp.factory_id,
      full_name: emp.full_name,
      position: emp.position,
      phone: emp.phone ?? '',
      hire_date: emp.hire_date ?? '',
      employment_type: emp.employment_type,
      department: emp.department || 'production',
      work_schedule: emp.work_schedule || 'six_day',
      bpjs_mode: emp.bpjs_mode || 'company_pays',
      employment_category: emp.employment_category || 'formal',
      pay_period: emp.pay_period || 'calendar_month',
      commission_rate: emp.commission_rate,
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
    if (!formData.factory_id) {
      setFormError('Factory is required');
      return;
    }
    if (editingEmployee) {
      const { factory_id, ...rest } = formData;
      updateMutation.mutate({ id: editingEmployee.id, data: rest });
    } else {
      createMutation.mutate(formData);
    }
  }, [formData, editingEmployee, createMutation, updateMutation]);

  // Month nav
  const prevMonth = () => {
    if (month === 1) { setMonth(12); setYear(year - 1); }
    else setMonth(month - 1);
  };
  const nextMonth = () => {
    if (month === 12) { setMonth(1); setYear(year + 1); }
    else setMonth(month + 1);
  };

  const isContractor = formData.employment_category === 'contractor';
  const isSales = formData.department === 'sales';

  // ── Render ──────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Employees & Payroll</h1>
          <p className="mt-1 text-sm text-gray-500">Manage all employees across factories and view payroll</p>
        </div>
        <div className="flex gap-2">
          {activeTab === 'employees' && (
            <Button onClick={openCreate}>+ Add Employee</Button>
          )}
        </div>
      </div>

      {/* Filters Bar */}
      <Card>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Factory filter */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Factory:</label>
              {factoriesLoading ? (
                <Spinner className="h-5 w-5" />
              ) : (
                <select
                  value={factoryFilter}
                  onChange={(e) => setFactoryFilter(e.target.value)}
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                >
                  <option value="all">All Factories</option>
                  {factories.map((f) => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </select>
              )}
            </div>

            {/* Department filter tabs */}
            {activeTab === 'employees' && (
              <div className="flex items-center gap-1">
                {DEPARTMENT_FILTERS.map((dept) => (
                  <button
                    key={dept}
                    onClick={() => setDepartmentFilter(dept)}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      departmentFilter === dept
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {dept === 'all' ? 'All' : dept.charAt(0).toUpperCase() + dept.slice(1)}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Month selector for payroll */}
          {activeTab === 'payroll' && (
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
          { id: 'employees', label: 'Employee Management' },
          { id: 'payroll', label: 'Payroll' },
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
      />

      {/* Tab Content */}
      {activeTab === 'employees' && (
        <EmployeeManagementTab
          employees={filteredEmployees}
          loading={employeesLoading}
          showInactive={showInactive}
          onToggleInactive={() => setShowInactive(!showInactive)}
          onEdit={openEdit}
          onDeactivate={(emp) => {
            if (confirm(`Deactivate ${emp.full_name}?`)) {
              deactivateMutation.mutate(emp.id);
            }
          }}
        />
      )}

      {activeTab === 'payroll' && (
        <PayrollTab
          items={payrollData?.items ?? []}
          totals={payrollData?.totals ?? null}
          loading={payrollLoading}
          year={year}
          month={month}
          departmentFilter={departmentFilter}
          factoryId={factoryFilter === 'all' ? undefined : factoryFilter}
        />
      )}

      {/* Employee Create/Edit Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        title={editingEmployee ? 'Edit Employee' : 'Add Employee'}
        className="w-full max-w-2xl"
      >
        <div className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
          {/* Basic info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Input
                label="Full Name *"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              />
            </div>
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
              label="Hire Date"
              type="date"
              value={formData.hire_date ?? ''}
              onChange={(e) => setFormData({ ...formData, hire_date: e.target.value })}
            />
            {!editingEmployee && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Factory *</label>
                <select
                  value={formData.factory_id}
                  onChange={(e) => setFormData({ ...formData, factory_id: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                >
                  <option value="">Select factory</option>
                  {factories.map((f) => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Employment details */}
          <hr className="my-2" />
          <p className="text-sm font-semibold text-gray-800">Employment Details</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Category</label>
              <select
                value={formData.employment_category}
                onChange={(e) => setFormData({ ...formData, employment_category: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {EMPLOYMENT_CATEGORIES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Department</label>
              <select
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {DEPARTMENTS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
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
              <label className="mb-1 block text-sm font-medium text-gray-700">Work Schedule</label>
              <select
                value={formData.work_schedule}
                onChange={(e) => setFormData({ ...formData, work_schedule: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                {WORK_SCHEDULES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            {!isContractor && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">BPJS Mode</label>
                <select
                  value={formData.bpjs_mode}
                  onChange={(e) => setFormData({ ...formData, bpjs_mode: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                >
                  {BPJS_MODES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
            )}
            {isSales && (
              <Input
                label="Commission Rate (%)"
                type="number"
                placeholder="e.g. 5.00"
                value={String(formData.commission_rate ?? '')}
                onChange={(e) => setFormData({
                  ...formData,
                  commission_rate: e.target.value ? parseFloat(e.target.value) : null,
                })}
              />
            )}
            <div className="col-span-2">
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

          {/* Contractor notice */}
          {isContractor && (
            <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
              Contractor: No BPJS, no THR, no annual leave. Tax = 2.5% PPh 23 on total payment.
            </div>
          )}

          {/* Salary & Allowances */}
          <hr className="my-2" />
          <p className="text-sm font-semibold text-gray-800">Salary & Allowances (IDR/month)</p>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Base Salary"
              type="number"
              value={String(formData.base_salary ?? 0)}
              onChange={(e) => setFormData({ ...formData, base_salary: parseFloat(e.target.value) || 0 })}
            />
            <Input
              label="Bike Allowance"
              type="number"
              value={String(formData.allowance_bike ?? 0)}
              onChange={(e) => setFormData({ ...formData, allowance_bike: parseFloat(e.target.value) || 0 })}
            />
            <Input
              label="Housing Allowance"
              type="number"
              value={String(formData.allowance_housing ?? 0)}
              onChange={(e) => setFormData({ ...formData, allowance_housing: parseFloat(e.target.value) || 0 })}
            />
            <Input
              label="Food Allowance"
              type="number"
              value={String(formData.allowance_food ?? 0)}
              onChange={(e) => setFormData({ ...formData, allowance_food: parseFloat(e.target.value) || 0 })}
            />
            <Input
              label="BPJS Allowance"
              type="number"
              value={String(formData.allowance_bpjs ?? 0)}
              onChange={(e) => setFormData({ ...formData, allowance_bpjs: parseFloat(e.target.value) || 0 })}
            />
            <Input
              label="Other Allowance"
              type="number"
              value={String(formData.allowance_other ?? 0)}
              onChange={(e) => setFormData({ ...formData, allowance_other: parseFloat(e.target.value) || 0 })}
            />
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
    </div>
  );
}

// ── Employee Management Tab ──────────────────────────────────

function EmployeeManagementTab({
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

  // Group counts
  const formalCount = employees.filter((e) => e.employment_category === 'formal').length;
  const contractorCount = employees.filter((e) => e.employment_category === 'contractor').length;

  return (
    <div className="space-y-4">
      {/* Summary badges */}
      <div className="flex items-center gap-4 flex-wrap">
        <span className="text-sm text-gray-500">{employees.length} employee{employees.length !== 1 ? 's' : ''}</span>
        <Badge variant="blue">{formalCount} Formal</Badge>
        <Badge variant="yellow">{contractorCount} Contractor</Badge>
        <label className="ml-auto flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={onToggleInactive}
            className="rounded border-gray-300"
          />
          Show inactive
        </label>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50 text-xs font-medium uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2 text-left">Name</th>
                <th className="px-3 py-2 text-left">Dept</th>
                <th className="px-3 py-2 text-left">Position</th>
                <th className="px-3 py-2 text-left">Factory</th>
                <th className="px-3 py-2 text-center">Type</th>
                <th className="px-3 py-2 text-center">Schedule</th>
                <th className="px-3 py-2 text-right">Base Salary</th>
                <th className="px-3 py-2 text-center">BPJS</th>
                <th className="px-3 py-2 text-center">Status</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {employees.map((emp) => (
                <tr key={emp.id} className={emp.is_active ? 'bg-white' : 'bg-gray-50 opacity-60'}>
                  <td className="px-3 py-2 font-medium text-gray-900">{emp.full_name}</td>
                  <td className="px-3 py-2 text-gray-600 capitalize">{emp.department || 'production'}</td>
                  <td className="px-3 py-2 text-gray-600">{emp.position}</td>
                  <td className="px-3 py-2 text-gray-600">{emp.factory_name || '-'}</td>
                  <td className="px-3 py-2 text-center">
                    <Badge variant={emp.employment_category === 'formal' ? 'blue' : 'yellow'}>
                      {emp.employment_category === 'formal' ? 'Formal' : 'Contractor'}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-center text-gray-600">
                    {emp.work_schedule === 'five_day' ? '5-day' : '6-day'}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-gray-700">{formatIDR(emp.base_salary)}</td>
                  <td className="px-3 py-2 text-center text-gray-600">
                    {emp.employment_category === 'formal'
                      ? (emp.bpjs_mode === 'company_pays' ? 'Co. Pays' : 'Reimburse')
                      : '-'
                    }
                  </td>
                  <td className="px-3 py-2 text-center">
                    <Badge variant={emp.is_active ? 'green' : 'gray'}>
                      {emp.is_active ? 'Active' : 'Inactive'}
                    </Badge>
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
              ))}
              {employees.length === 0 && (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-gray-400">
                    No employees found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// ── Payroll Tab ──────────────────────────────────────────────

function PayrollTab({
  items,
  totals,
  loading,
  year,
  month,
  departmentFilter,
  factoryId,
}: {
  items: PayrollItem[];
  totals: PayrollTotals | null;
  loading: boolean;
  year: number;
  month: number;
  departmentFilter: string;
  factoryId?: string;
}) {
  const [pdfLoading, setPdfLoading] = useState(false);

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

  // Apply department filter to payroll items too
  const filtered = departmentFilter === 'all'
    ? items
    : items.filter((i) => i.department === departmentFilter);

  // Compute local totals if filtered
  const localTotals = useMemo(() => {
    if (departmentFilter === 'all' && totals) return totals;
    const t: PayrollTotals = {
      total_employees: 0,
      formal_count: 0,
      contractor_count: 0,
      total_gross: 0,
      total_bpjs_employer: 0,
      total_bpjs_employee: 0,
      total_pph21: 0,
      total_contractor_tax: 0,
      total_net: 0,
      total_cost: 0,
      total_overtime_pay: 0,
      total_commission: 0,
    };
    for (const i of filtered) {
      t.total_employees++;
      if (i.employment_category === 'formal') t.formal_count++;
      else t.contractor_count++;
      t.total_gross += i.gross_salary;
      t.total_bpjs_employer += i.bpjs_employer;
      t.total_bpjs_employee += i.bpjs_employee;
      t.total_pph21 += i.pph21;
      t.total_contractor_tax += i.contractor_tax;
      t.total_net += i.net_salary;
      t.total_cost += i.total_cost_to_company;
      t.total_overtime_pay += i.overtime_pay;
      t.total_commission += i.commission;
    }
    return t;
  }, [filtered, totals, departmentFilter]);

  // Separate by category
  const formalItems = filtered.filter((i) => i.employment_category === 'formal');
  const contractorItems = filtered.filter((i) => i.employment_category === 'contractor');

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6 flex-1">
          <SummaryCard label="Employees" value={String(localTotals.total_employees)} sub={`${localTotals.formal_count}F / ${localTotals.contractor_count}C`} />
          <SummaryCard label="Total Gross" value={formatIDR(localTotals.total_gross)} />
          <SummaryCard label="BPJS (Employer)" value={formatIDR(localTotals.total_bpjs_employer)} color="text-orange-600" />
          <SummaryCard label="Tax (PPh 21+23)" value={formatIDR(localTotals.total_pph21 + localTotals.total_contractor_tax)} color="text-red-600" />
          <SummaryCard label="Total Net" value={formatIDR(localTotals.total_net)} color="text-green-600" />
          <SummaryCard label="Total Cost" value={formatIDR(localTotals.total_cost)} color="text-blue-600" />
        </div>
        <Button variant="secondary" onClick={downloadPdf} disabled={pdfLoading || items.length === 0}>
          {pdfLoading ? 'Generating...' : '↓ PDF'}
        </Button>
      </div>

      {/* Formal employees table */}
      {formalItems.length > 0 && (
        <PayrollTable
          title={`Formal Employees (${formalItems.length})`}
          items={formalItems}
          showBpjs
        />
      )}

      {/* Contractor table */}
      {contractorItems.length > 0 && (
        <PayrollTable
          title={`Contractors (${contractorItems.length})`}
          items={contractorItems}
          showBpjs={false}
        />
      )}

      {filtered.length === 0 && (
        <Card>
          <p className="py-8 text-center text-gray-400">No payroll data for {MONTH_NAMES[month - 1]} {year}.</p>
        </Card>
      )}
    </div>
  );
}

// ── Payroll Table ────────────────────────────────────────────

function PayrollTable({
  title,
  items,
  showBpjs,
}: {
  title: string;
  items: PayrollItem[];
  showBpjs: boolean;
}) {
  // Subtotals
  const sub = useMemo(() => {
    const s = { gross: 0, bpjsEmp: 0, bpjsEr: 0, tax: 0, net: 0, cost: 0, ot: 0, comm: 0 };
    for (const i of items) {
      s.gross += i.gross_salary;
      s.bpjsEmp += i.bpjs_employee;
      s.bpjsEr += i.bpjs_employer;
      s.tax += i.pph21 + i.contractor_tax;
      s.net += i.net_salary;
      s.cost += i.total_cost_to_company;
      s.ot += i.overtime_pay;
      s.comm += i.commission;
    }
    return s;
  }, [items]);

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-gray-800">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="border-b bg-gray-50 text-[10px] font-medium uppercase text-gray-500">
            <tr>
              <th className="px-2 py-1.5 text-left">Name</th>
              <th className="px-2 py-1.5 text-left">Dept</th>
              <th className="px-2 py-1.5 text-center">Days</th>
              <th className="px-2 py-1.5 text-center">OT hrs</th>
              <th className="px-2 py-1.5 text-right">Base</th>
              <th className="px-2 py-1.5 text-right">Allowances</th>
              <th className="px-2 py-1.5 text-right">OT Pay</th>
              <th className="px-2 py-1.5 text-right">Comm.</th>
              <th className="px-2 py-1.5 text-right">Gross</th>
              {showBpjs && (
                <>
                  <th className="px-2 py-1.5 text-right">BPJS Emp</th>
                  <th className="px-2 py-1.5 text-right">BPJS Er</th>
                </>
              )}
              <th className="px-2 py-1.5 text-right">Tax</th>
              <th className="px-2 py-1.5 text-right font-bold">Net</th>
              <th className="px-2 py-1.5 text-right">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((row) => (
              <tr key={row.employee_id} className="hover:bg-gray-50">
                <td className="px-2 py-1.5 font-medium text-gray-900 whitespace-nowrap">{row.full_name}</td>
                <td className="px-2 py-1.5 text-gray-600 capitalize">{row.department}</td>
                <td className="px-2 py-1.5 text-center text-gray-600">
                  {row.present_days}/{row.working_days_in_month}
                </td>
                <td className="px-2 py-1.5 text-center text-gray-600">{formatNum(row.overtime_hours, 1)}</td>
                <td className="px-2 py-1.5 text-right font-mono text-gray-700">{formatIDR(row.prorated_salary)}</td>
                <td className="px-2 py-1.5 text-right font-mono text-gray-700">{formatIDR(row.prorated_allowances)}</td>
                <td className="px-2 py-1.5 text-right font-mono text-gray-700">{row.overtime_pay > 0 ? formatIDR(row.overtime_pay) : '-'}</td>
                <td className="px-2 py-1.5 text-right font-mono text-gray-700">{row.commission > 0 ? formatIDR(row.commission) : '-'}</td>
                <td className="px-2 py-1.5 text-right font-mono text-gray-800 font-medium">{formatIDR(row.gross_salary)}</td>
                {showBpjs && (
                  <>
                    <td className="px-2 py-1.5 text-right font-mono text-orange-600">{formatIDR(row.bpjs_employee)}</td>
                    <td className="px-2 py-1.5 text-right font-mono text-orange-600">{formatIDR(row.bpjs_employer)}</td>
                  </>
                )}
                <td className="px-2 py-1.5 text-right font-mono text-red-600">
                  {formatIDR(row.pph21 + row.contractor_tax)}
                </td>
                <td className="px-2 py-1.5 text-right font-mono text-green-700 font-bold">{formatIDR(row.net_salary)}</td>
                <td className="px-2 py-1.5 text-right font-mono text-blue-600">{formatIDR(row.total_cost_to_company)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t-2 border-gray-300 bg-gray-50 text-xs font-semibold">
            <tr>
              <td className="px-2 py-2 text-gray-800" colSpan={2}>Subtotal</td>
              <td className="px-2 py-2" colSpan={2}></td>
              <td className="px-2 py-2" colSpan={2}></td>
              <td className="px-2 py-2 text-right font-mono">{sub.ot > 0 ? formatIDR(sub.ot) : '-'}</td>
              <td className="px-2 py-2 text-right font-mono">{sub.comm > 0 ? formatIDR(sub.comm) : '-'}</td>
              <td className="px-2 py-2 text-right font-mono text-gray-800">{formatIDR(sub.gross)}</td>
              {showBpjs && (
                <>
                  <td className="px-2 py-2 text-right font-mono text-orange-600">{formatIDR(sub.bpjsEmp)}</td>
                  <td className="px-2 py-2 text-right font-mono text-orange-600">{formatIDR(sub.bpjsEr)}</td>
                </>
              )}
              <td className="px-2 py-2 text-right font-mono text-red-600">{formatIDR(sub.tax)}</td>
              <td className="px-2 py-2 text-right font-mono text-green-700">{formatIDR(sub.net)}</td>
              <td className="px-2 py-2 text-right font-mono text-blue-600">{formatIDR(sub.cost)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </Card>
  );
}

// ── Summary Card ─────────────────────────────────────────────

function SummaryCard({
  label,
  value,
  sub,
  color = 'text-gray-900',
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <Card>
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</p>
      <p className={`mt-1 text-lg font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </Card>
  );
}
