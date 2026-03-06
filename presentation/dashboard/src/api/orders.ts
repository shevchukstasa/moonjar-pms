import apiClient from './client';

export interface OrderListParams {
  page?: number;
  per_page?: number;
  factory_id?: string;
  status?: string;
  search?: string;
  tab?: 'current' | 'archive';
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export const ordersApi = {
  list: (params?: OrderListParams) =>
    apiClient.get('/orders', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/orders/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/orders', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/orders/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/orders/${id}`).then((r) => r.data),
};
