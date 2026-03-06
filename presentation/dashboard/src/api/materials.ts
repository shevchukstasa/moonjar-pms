import apiClient from './client';

export const materialsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/materials', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/materials/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/materials', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/materials/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/materials/${id}`).then((r) => r.data),
};
