import apiClient from './client';

export const positionsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/positions', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/positions/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/positions', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/positions/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/positions/${id}`).then((r) => r.data),
};
