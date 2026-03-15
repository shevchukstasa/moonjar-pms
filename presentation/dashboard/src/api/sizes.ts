import apiClient from './client';

export interface SizeItem {
  id: string;
  name: string;
  width_mm: number;
  height_mm: number;
  thickness_mm: number | null;
  shape: string | null;
  is_custom: boolean;
  created_at: string | null;
}

export interface SizeInput {
  name: string;
  width_mm: number;
  height_mm: number;
  thickness_mm?: number | null;
  shape?: string;
  is_custom?: boolean;
}

export const sizesApi = {
  list: () =>
    apiClient.get('/sizes').then((r) => r.data as { items: SizeItem[]; total: number }),

  get: (id: string) =>
    apiClient.get(`/sizes/${id}`).then((r) => r.data as SizeItem),

  create: (data: SizeInput) =>
    apiClient.post('/sizes', data).then((r) => r.data as SizeItem),

  update: (id: string, data: Partial<SizeInput>) =>
    apiClient.patch(`/sizes/${id}`, data).then((r) => r.data as SizeItem),

  remove: (id: string) =>
    apiClient.delete(`/sizes/${id}`).then((r) => r.data),
};
