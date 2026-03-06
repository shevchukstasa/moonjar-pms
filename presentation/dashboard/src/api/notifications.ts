import apiClient from './client';

export const notificationsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/notifications', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/notifications/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/notifications', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/notifications/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/notifications/${id}`).then((r) => r.data),
};
