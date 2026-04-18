import apiClient from './client';

export interface StoneDesign {
  id: string;
  code: string;
  name: string;
  name_id: string | null;
  typology: string | null;
  photo_url: string | null;
  description: string | null;
  display_order: number;
  is_active: boolean;
  material_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface DesignCreateInput {
  code: string;
  name: string;
  name_id?: string | null;
  typology?: string | null;
  photo_url?: string | null;
  description?: string | null;
  display_order?: number;
}

export type DesignUpdateInput = Partial<DesignCreateInput> & { is_active?: boolean };

export const designsApi = {
  list: (params?: { typology?: string; include_inactive?: boolean }) =>
    apiClient
      .get('/designs', { params })
      .then((r) => r.data as { items: StoneDesign[]; total: number }),

  get: (id: string) =>
    apiClient.get(`/designs/${id}`).then((r) => r.data as StoneDesign),

  create: (data: DesignCreateInput) =>
    apiClient.post('/designs', data).then((r) => r.data as StoneDesign),

  update: (id: string, data: DesignUpdateInput) =>
    apiClient.patch(`/designs/${id}`, data).then((r) => r.data as StoneDesign),

  remove: (id: string) =>
    apiClient.delete(`/designs/${id}`).then((r) => r.data),
};
