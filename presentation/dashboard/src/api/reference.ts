import apiClient from './client';

export const referenceApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/reference', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/reference/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/reference', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/reference/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/reference/${id}`).then((r) => r.data),
};
