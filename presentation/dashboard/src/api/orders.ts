import apiClient from './client';

export const ordersApi = {
  list: (params?: Record<string, unknown>) =>
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
