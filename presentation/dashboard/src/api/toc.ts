import apiClient from './client';

export const tocApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/toc', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/toc/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/toc', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/toc/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/toc/${id}`).then((r) => r.data),
};
