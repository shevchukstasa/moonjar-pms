import apiClient from './client';

// ── Types ────────────────────────────────────────────────────

export interface Employee {
  id: string;
  factory_id: string;
  factory_name: string | null;
  full_name: string;
  position: string;
  phone: string | null;
  hire_date: string | null;
  is_active: boolean;
  employment_type: string;
  department: string;
  work_schedule: string;
  bpjs_mode: string;
  employment_category: string;
  commission_rate: number | null;
  base_salary: number;
  allowance_bike: number;
  allowance_housing: number;
  allowance_food: number;
  allowance_bpjs: number;
  allowance_other: number;
  allowance_other_note: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface EmployeeListResponse {
  items: Employee[];
  total: number;
  page: number;
  per_page: number;
}

export interface EmployeeCreatePayload {
  factory_id: string;
  full_name: string;
  position: string;
  phone?: string | null;
  hire_date?: string | null;
  is_active?: boolean;
  employment_type?: string;
  department?: string;
  work_schedule?: string;
  bpjs_mode?: string;
  employment_category?: string;
  commission_rate?: number | null;
  base_salary?: number;
  allowance_bike?: number;
  allowance_housing?: number;
  allowance_food?: number;
  allowance_bpjs?: number;
  allowance_other?: number;
  allowance_other_note?: string | null;
}

export interface EmployeeUpdatePayload {
  full_name?: string;
  position?: string;
  phone?: string | null;
  hire_date?: string | null;
  is_active?: boolean;
  employment_type?: string;
  department?: string;
  work_schedule?: string;
  bpjs_mode?: string;
  employment_category?: string;
  commission_rate?: number | null;
  base_salary?: number;
  allowance_bike?: number;
  allowance_housing?: number;
  allowance_food?: number;
  allowance_bpjs?: number;
  allowance_other?: number;
  allowance_other_note?: string | null;
}

export interface AttendanceRecord {
  id: string;
  employee_id: string;
  employee_name: string | null;
  date: string;
  status: string;
  overtime_hours: number;
  notes: string | null;
  recorded_by: string | null;
  created_at: string | null;
}

export interface AttendanceListResponse {
  items: AttendanceRecord[];
}

export interface AttendanceCreatePayload {
  date: string;
  status: string;
  overtime_hours?: number;
  notes?: string | null;
}

export interface AttendanceUpdatePayload {
  status?: string;
  overtime_hours?: number;
  notes?: string | null;
}

export interface PayrollItem {
  employee_id: string;
  full_name: string;
  position: string;
  department: string;
  employment_category: string;
  work_schedule: string;
  working_days_in_month: number;
  present_days: number;
  absent_days: number;
  sick_days: number;
  leave_days: number;
  half_days: number;
  effective_days: number;
  overtime_hours: number;
  base_salary: number;
  daily_rate: number;
  hourly_rate: number;
  prorated_salary: number;
  allowance_bike: number;
  allowance_housing: number;
  allowance_food: number;
  allowance_bpjs: number;
  allowance_other: number;
  total_allowances: number;
  prorated_allowances: number;
  overtime_pay: number;
  commission_rate: number;
  commission: number;
  gross_salary: number;
  bpjs_employee: number;
  bpjs_employer: number;
  pph21: number;
  contractor_tax: number;
  absence_deduction: number;
  total_deductions: number;
  net_salary: number;
  total_cost_to_company: number;
}

export interface PayrollTotals {
  total_employees: number;
  formal_count: number;
  contractor_count: number;
  total_gross: number;
  total_bpjs_employer: number;
  total_bpjs_employee: number;
  total_pph21: number;
  total_contractor_tax: number;
  total_net: number;
  total_cost: number;
  total_overtime_pay: number;
  total_commission: number;
}

export interface PayrollSummaryResponse {
  items: PayrollItem[];
  totals: PayrollTotals;
  factory_id: string | null;
  year: number;
  month: number;
}

// Legacy type alias for backward compat
export type PayrollSummaryItem = PayrollItem;

// ── API client ───────────────────────────────────────────────

export const employeesApi = {
  list: (params: {
    factory_id?: string;
    is_active?: boolean;
    department?: string;
    employment_category?: string;
    page?: number;
    per_page?: number;
  }): Promise<EmployeeListResponse> =>
    apiClient.get('/employees', { params }).then((r) => r.data),

  get: (id: string): Promise<Employee> =>
    apiClient.get(`/employees/${id}`).then((r) => r.data),

  create: (data: EmployeeCreatePayload): Promise<Employee> =>
    apiClient.post('/employees', data).then((r) => r.data),

  update: (id: string, data: EmployeeUpdatePayload): Promise<Employee> =>
    apiClient.patch(`/employees/${id}`, data).then((r) => r.data),

  deactivate: (id: string): Promise<{ status: string; id: string }> =>
    apiClient.delete(`/employees/${id}`).then((r) => r.data),

  // Attendance
  getAttendance: (
    employeeId: string,
    params: { start_date?: string; end_date?: string; year?: number; month?: number },
  ): Promise<AttendanceListResponse> =>
    apiClient.get(`/employees/${employeeId}/attendance`, { params }).then((r) => r.data),

  recordAttendance: (employeeId: string, data: AttendanceCreatePayload): Promise<AttendanceRecord> =>
    apiClient.post(`/employees/${employeeId}/attendance`, data).then((r) => r.data),

  updateAttendance: (attendanceId: string, data: AttendanceUpdatePayload): Promise<AttendanceRecord> =>
    apiClient.patch(`/employees/attendance/${attendanceId}`, data).then((r) => r.data),

  // Payroll
  payrollSummary: (params: {
    factory_id?: string;
    year: number;
    month: number;
  }): Promise<PayrollSummaryResponse> =>
    apiClient.get('/employees/payroll-summary', { params }).then((r) => r.data),
};
