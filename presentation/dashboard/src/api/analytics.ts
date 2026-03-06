import apiClient from './client';

export const analyticsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/analytics', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/analytics/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/analytics', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/analytics/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/analytics/${id}`).then((r) => r.data),
};
