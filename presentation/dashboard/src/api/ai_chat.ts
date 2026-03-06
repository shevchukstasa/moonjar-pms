import apiClient from './client';

export const ai_chatApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/ai-chat', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/ai-chat/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/ai-chat', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/ai-chat/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/ai-chat/${id}`).then((r) => r.data),
};
