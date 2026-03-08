import apiClient from './client';

// --- Types ---

export interface DashboardSummary {
  orders_in_progress: number;
  total_orders: number;
  output_sqm: number;
  on_time_rate: number;
  defect_rate: number;
  kiln_utilization: number;
  oee: number;
  cost_per_sqm: number;
}

export interface DailyOutput {
  date: string;
  output_sqm: number;
  output_pcs: number;
}

export interface PipelineStage {
  stage: string;
  count: number;
  sqm: number;
}

export interface CriticalPosition {
  position_id: string;
  order_number: string | null;
  status: string;
  color: string;
  size: string;
  quantity: number;
  delay_hours: number;
  deadline: string | null;
}

export interface ProductionMetrics {
  daily_output: DailyOutput[];
  pipeline_funnel: PipelineStage[];
  critical_positions: CriticalPosition[];
}

export interface DeficitItem {
  material_id: string;
  name: string;
  balance: number;
  min_balance: number;
  deficit: number;
  unit: string;
  material_type: string;
  factory_id: string;
}

export interface MaterialMetrics {
  deficit_items: DeficitItem[];
  deficit_count: number;
}

export interface FactoryComparison extends DashboardSummary {
  factory_id: string;
  factory_name: string;
  factory_location: string | null;
}

export interface BufferHealthItem {
  health: 'green' | 'yellow' | 'red';
  hours: number;
  target: number;
  buffered_count: number;
  buffered_sqm: number;
  kiln_id: string;
  kiln_name: string;
  factory_name?: string;
}

export interface TrendDataPoint {
  date: string;
  label: string;
  value: number;
}

export interface ActivityFeedItem {
  id: string;
  type: string;
  title: string;
  message: string | null;
  created_at: string | null;
  is_read: boolean;
  related_entity_type: string | null;
  related_entity_id: string | null;
}

// --- API Functions ---

export const analyticsApi = {
  getDashboardSummary: (params?: { factory_id?: string; date_from?: string; date_to?: string }) =>
    apiClient.get<DashboardSummary>('/analytics/dashboard-summary', { params }).then((r) => r.data),

  getProductionMetrics: (params?: { factory_id?: string; date_from?: string; date_to?: string }) =>
    apiClient.get<ProductionMetrics>('/analytics/production-metrics', { params }).then((r) => r.data),

  getMaterialMetrics: (params?: { factory_id?: string }) =>
    apiClient.get<MaterialMetrics>('/analytics/material-metrics', { params }).then((r) => r.data),

  getFactoryComparison: () =>
    apiClient.get<FactoryComparison[]>('/analytics/factory-comparison').then((r) => r.data),

  getBufferHealth: (params?: { factory_id?: string }) =>
    apiClient.get<{ items: BufferHealthItem[] }>('/analytics/buffer-health', { params }).then((r) => r.data),

  getTrendData: (metric: string, params?: { factory_id?: string; months?: number }) =>
    apiClient.get<TrendDataPoint[]>(`/analytics/trend-data`, { params: { metric, ...params } }).then((r) => r.data),

  getActivityFeed: (params?: { factory_id?: string; limit?: number }) =>
    apiClient.get<ActivityFeedItem[]>('/analytics/activity-feed', { params }).then((r) => r.data),
};
