import apiClient from './client';

export const suppliersApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/suppliers', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/suppliers/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/suppliers', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/suppliers/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/suppliers/${id}`).then((r) => r.data),
};
