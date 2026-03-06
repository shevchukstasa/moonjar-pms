import apiClient from './client';

export const qualityApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/quality', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/quality/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/quality', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/quality/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/quality/${id}`).then((r) => r.data),
};
