import apiClient from './client';

export const defectsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/defects', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/defects/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/defects', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/defects/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/defects/${id}`).then((r) => r.data),
};
