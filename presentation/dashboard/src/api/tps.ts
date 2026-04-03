import apiClient from './client';

export interface TpsParameter {
  id: string;
  stage: string;
  // Backend actual field names
  metric_name: string | null;
  target_value: number | null;
  tolerance_percent: number | null;
  unit: string | null;
  factory_id: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
  // Legacy aliases (may not be present)
  target_cycle_time_min?: number;
  standard_batch_size?: number;
  tolerance_pct?: number;
}

export const tpsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/tps', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/tps/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/tps', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/tps/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/tps/${id}`).then((r) => r.data),
  // TPS Parameters
  listParameters: (params?: Record<string, unknown>) =>
    apiClient.get('/tps/parameters', { params }).then((r) => r.data),
  updateParameter: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/tps/parameters/${id}`, data).then((r) => r.data),
};
