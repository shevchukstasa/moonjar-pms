import apiClient from './client';

export interface BatchListParams {
  page?: number;
  per_page?: number;
  factory_id?: string;
  resource_id?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
}

export const scheduleApi = {
  resources: (params?: { factory_id?: string; resource_type?: string }) =>
    apiClient.get('/schedule/resources', { params }).then((r) => r.data),

  batches: (params?: BatchListParams) =>
    apiClient.get('/schedule/batches', { params }).then((r) => r.data),
  createBatch: (data: { resource_id: string; factory_id: string; batch_date: string; position_ids?: string[]; notes?: string }) =>
    apiClient.post('/schedule/batches', data).then((r) => r.data),

  glazingSchedule: (params?: { factory_id?: string }) =>
    apiClient.get('/schedule/glazing-schedule', { params }).then((r) => r.data),
  firingSchedule: (params?: { factory_id?: string }) =>
    apiClient.get('/schedule/firing-schedule', { params }).then((r) => r.data),
  sortingSchedule: (params?: { factory_id?: string }) =>
    apiClient.get('/schedule/sorting-schedule', { params }).then((r) => r.data),

  qcSchedule: (params?: { factory_id?: string }) =>
    apiClient.get('/schedule/qc-schedule', { params }).then((r) => r.data),

  kilnSchedule: (params?: { factory_id?: string }) =>
    apiClient.get('/schedule/kiln-schedule', { params }).then((r) => r.data),

  reorderPositions: (positionIds: string[]) =>
    apiClient.patch('/schedule/positions/reorder', { position_ids: positionIds }).then((r) => r.data),

  assignBatchPositions: (batchId: string, positionIds: string[]) =>
    apiClient.post(`/schedule/batches/${batchId}/positions`, { position_ids: positionIds }).then((r) => r.data),

  autoFormBatches: (data: { factory_id: string; target_date?: string; mode?: string }) =>
    apiClient.post('/batches/auto-form', data).then((r) => r.data),

  productionSchedule: (params: { factory_id: string; days?: number }) =>
    apiClient.get('/schedule/production-schedule', { params }).then((r) => r.data),
};
