import apiClient from './client';

export const exportApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/export', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/export/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/export', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/export/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/export/${id}`).then((r) => r.data),
};
