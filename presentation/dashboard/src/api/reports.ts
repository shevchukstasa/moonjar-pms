import apiClient from './client';

export interface ReportParams {
  factory_id?: string;
  date_from?: string;
  date_to?: string;
}

export interface OrdersSummary {
  period: { from: string; to: string };
  total_orders: number;
  completed: number;
  in_progress: number;
  on_time_count: number;
  on_time_percent: number;
  avg_completion_days: number;
}

export interface KilnLoadItem {
  kiln_id: string;
  kiln_name: string;
  factory_id: string;
  capacity_sqm: number;
  total_batches: number;
  done_batches: number;
  total_loaded_sqm: number;
  avg_load_sqm: number;
  utilization_percent: number;
}

export interface KilnLoadReport {
  period: { from: string; to: string };
  kilns: KilnLoadItem[];
}

export interface DailyProductionRow {
  order_number: string;
  color: string;
  method: string;
  size: string;
  sorted: number;
  refire: number;
  repair: number;
  grinding: number;
  color_mismatch: number;
  write_off: number;
  total_reject: number;
  packed: number;
  defect_rate_pct: number;
}

export interface DailyProductionReport {
  date: string;
  factory: string;
  factory_id: string;
  summary: {
    total_sorted: number;
    total_refire: number;
    total_repair: number;
    total_grinding: number;
    total_color_mismatch: number;
    total_write_off: number;
    total_reject: number;
    total_packed: number;
    defect_rate_pct: number;
  };
  rows: DailyProductionRow[];
}

export interface DailyProductionParams {
  factory_id: string;
  date?: string;
  order_id?: string;
}

export const reportsApi = {
  ordersSummary: (params?: ReportParams) =>
    apiClient.get<OrdersSummary>('/reports/orders-summary', { params }).then((r) => r.data),

  kilnLoad: (params?: ReportParams) =>
    apiClient.get<KilnLoadReport>('/reports/kiln-load', { params }).then((r) => r.data),

  dailyProduction: (params: DailyProductionParams) =>
    apiClient.get<DailyProductionReport>('/reports/daily-production', { params }).then((r) => r.data),
};
