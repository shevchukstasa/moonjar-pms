import apiClient from './client';

export const kilnsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/kilns', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/kilns/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/kilns', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/kilns/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/kilns/${id}`).then((r) => r.data),
};
