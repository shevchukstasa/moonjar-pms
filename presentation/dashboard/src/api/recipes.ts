import apiClient from './client';

export const recipesApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/recipes', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/recipes/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/recipes', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/recipes/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/recipes/${id}`).then((r) => r.data),
};
