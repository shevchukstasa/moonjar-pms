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

export const reportsApi = {
  ordersSummary: (params?: ReportParams) =>
    apiClient.get<OrdersSummary>('/reports/orders-summary', { params }).then((r) => r.data),

  kilnLoad: (params?: ReportParams) =>
    apiClient.get<KilnLoadReport>('/reports/kiln-load', { params }).then((r) => r.data),
};
