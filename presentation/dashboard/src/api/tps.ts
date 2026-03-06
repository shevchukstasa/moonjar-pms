import apiClient from './client';

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
};
