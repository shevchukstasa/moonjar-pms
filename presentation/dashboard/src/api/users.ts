import apiClient from './client';

export const usersApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/users', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/users/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/users', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/users/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/users/${id}`).then((r) => r.data),
};
