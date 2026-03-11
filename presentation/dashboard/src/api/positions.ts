import apiClient from './client';

export interface PositionListParams {
  page?: number;
  per_page?: number;
  factory_id?: string;
  order_id?: string;
  status?: string;
  batch_id?: string;
  section?: 'glazing' | 'firing' | 'sorting';
}

export interface SortingSplitRequest {
  good_quantity: number;
  refire_quantity: number;          // Already glazed; bubbles/underfired → back to kiln
  repair_quantity: number;          // Needs re-glazing → SENT_TO_GLAZING
  color_mismatch_quantity: number;  // Wrong color → re-starts from PLANNED
  grinding_quantity: number;
  write_off_quantity: number;
  notes?: string;
}

export const positionsApi = {
  list: (params?: PositionListParams) =>
    apiClient.get('/positions', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/positions/${id}`).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/positions/${id}`, data).then((r) => r.data),
  changeStatus: (id: string, status: string, notes?: string) =>
    apiClient.post(`/positions/${id}/status`, { status, notes }).then((r) => r.data),
  split: (id: string, data: SortingSplitRequest) =>
    apiClient.post(`/positions/${id}/split`, data).then((r) => r.data),
  stockAvailability: (id: string) =>
    apiClient.get(`/positions/${id}/stock-availability`).then((r) => r.data),
};
