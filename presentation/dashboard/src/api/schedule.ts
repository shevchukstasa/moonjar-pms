import apiClient from './client';

export const scheduleApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/schedule', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/schedule/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/schedule', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/schedule/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/schedule/${id}`).then((r) => r.data),
};
