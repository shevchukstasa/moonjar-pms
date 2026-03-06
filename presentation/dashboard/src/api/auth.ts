import apiClient from './client';

export const authApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/auth', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/auth/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/auth', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/auth/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/auth/${id}`).then((r) => r.data),
};
