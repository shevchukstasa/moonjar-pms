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
  termination_date: string | null;
  is_active: boolean;
  employment_type: string;
  department: string;
  work_schedule: string;
  bpjs_mode: string;
  employment_category: string;
  commission_rate: number | null;
  pay_period: string;
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
  termination_date?: string | null;
  is_active?: boolean;
  employment_type?: string;
  department?: string;
  work_schedule?: string;
  bpjs_mode?: string;
  employment_category?: string;
  commission_rate?: number | null;
  pay_period?: string;
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
  termination_date?: string | null;
  is_active?: boolean;
  employment_type?: string;
  department?: string;
  work_schedule?: string;
  bpjs_mode?: string;
  employment_category?: string;
  commission_rate?: number | null;
  pay_period?: string;
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
  hours_worked: number | null;
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
  hours_worked?: number | null;
  notes?: string | null;
}

export interface AttendanceUpdatePayload {
  status?: string;
  overtime_hours?: number;
  hours_worked?: number | null;
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
  advances_total?: number;
  net_salary_after_advances?: number;
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

  deleteAttendance: (attendanceId: string): Promise<{ status: string; id: string }> =>
    apiClient.delete(`/employees/attendance/${attendanceId}`).then((r) => r.data),

  // Payroll
  payrollSummary: (params: {
    factory_id?: string;
    year: number;
    month: number;
  }): Promise<PayrollSummaryResponse> =>
    apiClient.get('/employees/payroll-summary', { params }).then((r) => r.data),

  payrollPdf: (params: {
    factory_id?: string;
    year: number;
    month: number;
  }): Promise<Blob> =>
    apiClient
      .get('/employees/payroll-pdf', { params, responseType: 'blob' })
      .then((r) => r.data),

  payrollPdfEmployee: (params: {
    employee_id: string;
    year: number;
    month: number;
  }): Promise<Blob> =>
    apiClient
      .get('/employees/payroll-pdf-employee', { params, responseType: 'blob' })
      .then((r) => r.data),

  // Salary Advances
  getAdvances: (
    employeeId: string,
    params: { year?: number; month?: number },
  ): Promise<AdvanceListResponse> =>
    apiClient.get(`/employees/${employeeId}/advances`, { params }).then((r) => r.data),

  createAdvance: (employeeId: string, data: AdvanceCreatePayload): Promise<AdvanceRecord> =>
    apiClient.post(`/employees/${employeeId}/advances`, data).then((r) => r.data),

  updateAdvance: (advanceId: string, data: AdvanceUpdatePayload): Promise<AdvanceRecord> =>
    apiClient.patch(`/employees/advances/${advanceId}`, data).then((r) => r.data),

  deleteAdvance: (advanceId: string): Promise<{ status: string; id: string }> =>
    apiClient.delete(`/employees/advances/${advanceId}`).then((r) => r.data),

  // HR Costs (owner/ceo only)
  hrCostsYearly: (params: {
    year: number;
    factory_id?: string;
  }): Promise<HRCostsYearlyResponse> =>
    apiClient.get('/employees/hr-costs/yearly', { params }).then((r) => r.data),

  hrCostsEmployeeHistory: (params: {
    employee_id: string;
    year: number;
  }): Promise<HRCostsEmployeeHistoryResponse> =>
    apiClient
      .get(`/employees/hr-costs/employee/${params.employee_id}/history`, { params: { year: params.year } })
      .then((r) => r.data),
};

// ── Salary Advance types ─────────────────────────────────────

export interface AdvanceRecord {
  id: string;
  employee_id: string;
  date: string;         // date cash was given
  amount: number;
  deduct_year: number;  // which year to deduct from payroll
  deduct_month: number; // which month to deduct (1-12)
  notes: string | null;
  recorded_by: string | null;
  created_at: string | null;
}

export interface AdvanceListResponse {
  items: AdvanceRecord[];
}

export interface AdvanceCreatePayload {
  date: string;
  amount: number;
  deduct_year?: number;
  deduct_month?: number;
  carry_amount?: number; // if set: auto-splits into two records
  notes?: string | null;
}

export interface AdvanceUpdatePayload {
  date?: string;
  amount?: number;
  deduct_year?: number;
  deduct_month?: number;
  notes?: string | null;
}

// ── HR Costs types ──────────────────────────────────────────

export interface HRCostsDepartmentBreakdown {
  department: string;
  employees: number;
  total_gross: number;
  total_bpjs_employer: number;
  total_pph21: number;
  total_contractor_tax: number;
  total_net: number;
  total_cost: number;
  total_overtime_pay: number;
  total_commission: number;
  leave_compensation: number;
}

export interface HRCostsDepartmentYearTotals {
  department: string;
  peak_employees: number;
  total_gross: number;
  total_bpjs_employer: number;
  total_pph21: number;
  total_contractor_tax: number;
  total_net: number;
  total_cost: number;
  total_overtime_pay: number;
  total_commission: number;
  leave_compensation: number;
}

export interface HRCostsMonthEntry {
  month: number;
  month_name: string;
  total_employees: number;
  formal_count: number;
  contractor_count: number;
  total_gross: number;
  total_bpjs_employer: number;
  total_company_bpjs_for_employee: number;
  total_pph21: number;
  total_pph21_borne_by_company: number;
  total_contractor_tax: number;
  total_net: number;
  total_cost: number;
  total_overtime_pay: number;
  total_commission: number;
  leave_compensation: number;
  terminations: number;
  by_department: HRCostsDepartmentBreakdown[];
}

export interface HRCostsYearlyResponse {
  year: number;
  factory_id: string | null;
  months: HRCostsMonthEntry[];
  year_totals: {
    total_employees: number;
    total_gross: number;
    total_bpjs_employer: number;
    total_company_bpjs_for_employee: number;
    total_pph21: number;
    total_contractor_tax: number;
    total_net: number;
    total_cost: number;
    total_overtime_pay: number;
    total_commission: number;
    total_leave_compensation: number;
    terminations_count: number;
  };
  by_department: HRCostsDepartmentYearTotals[];
}

export interface HRCostsEmployeeMonthEntry {
  month: number;
  month_name: string;
  present_days: number;
  absent_days: number;
  sick_days: number;
  leave_days: number;
  gross_salary: number;
  net_salary: number;
  total_cost_to_company: number;
  bpjs_employer: number;
  pph21: number;
  overtime_pay: number;
  commission: number;
  leave_compensation: number;
  is_termination_month: boolean;
}

export interface HRCostsEmployeeHistoryResponse {
  employee_id: string;
  full_name: string;
  position: string;
  hire_date: string | null;
  termination_date: string | null;
  year: number;
  months: HRCostsEmployeeMonthEntry[];
}
