import apiClient from './client';

export interface PackagingCapacity {
  id: string;
  size_id: string;
  size_name: string | null;
  pieces_per_box: number | null;
  sqm_per_box: number | null;
}

export interface PackagingSpacerRule {
  id: string;
  size_id: string;
  size_name: string | null;
  spacer_material_id: string;
  spacer_material_name: string | null;
  spacer_material_code: string | null;
  qty_per_box: number;
}

export interface PackagingBoxType {
  id: string;
  material_id: string;
  material_name: string | null;
  material_code: string | null;
  name: string;
  notes: string | null;
  is_active: boolean;
  capacities: PackagingCapacity[];
  spacer_rules: PackagingSpacerRule[];
  created_at: string | null;
  updated_at: string | null;
}

export interface SizeItem {
  id: string;
  name: string;
  width_mm: number;
  height_mm: number;
  thickness_mm: number | null;
  shape: string | null;
  is_custom: boolean;
}

export const packagingApi = {
  list: () =>
    apiClient.get('/packaging').then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/packaging/${id}`).then((r) => r.data),
  create: (data: { material_id: string; name: string; notes?: string; is_active?: boolean }) =>
    apiClient.post('/packaging', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/packaging/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/packaging/${id}`).then((r) => r.data),

  setCapacities: (boxTypeId: string, capacities: Array<{ size_id: string; pieces_per_box?: number; sqm_per_box?: number }>) =>
    apiClient.put(`/packaging/${boxTypeId}/capacities`, { capacities }).then((r) => r.data),

  setSpacers: (boxTypeId: string, spacers: Array<{ size_id: string; spacer_material_id: string; qty_per_box: number }>) =>
    apiClient.put(`/packaging/${boxTypeId}/spacers`, { spacers }).then((r) => r.data),

  listSizes: () =>
    apiClient.get('/packaging/sizes').then((r) => r.data),
};
