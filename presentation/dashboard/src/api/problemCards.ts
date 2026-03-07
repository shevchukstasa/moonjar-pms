import apiClient from './client';

export interface ProblemCardItem {
  id: string;
  factory_id: string;
  location: string | null;
  description: string;
  actions: string | null;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export const problemCardsApi = {
  list: (params?: { factory_id?: string; status?: string; page?: number; per_page?: number }) =>
    apiClient.get('/problem-cards', { params }).then((r) => r.data),
  create: (data: { factory_id: string; location?: string; description: string }) =>
    apiClient.post('/problem-cards', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/problem-cards/${id}`, data).then((r) => r.data),
};
