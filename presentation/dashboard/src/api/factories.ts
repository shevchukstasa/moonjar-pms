import apiClient from './client';

export const factoriesApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/factories', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/factories/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/factories', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/factories/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/factories/${id}`).then((r) => r.data),
};
