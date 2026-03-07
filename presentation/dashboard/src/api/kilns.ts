import apiClient from './client';

export interface KilnListParams {
  factory_id?: string;
  status?: string;
  page?: number;
  per_page?: number;
}

export interface KilnCreateData {
  name: string;
  factory_id: string;
  kiln_type: string;
  kiln_dimensions_cm?: { width: number; depth: number; height: number };
  kiln_working_area_cm?: { width: number; depth: number; height: number };
  kiln_multi_level?: boolean;
  kiln_coefficient?: number;
  num_levels?: number;
  capacity_sqm?: number;
  capacity_pcs?: number;
}

export const kilnsApi = {
  list: (params?: KilnListParams) =>
    apiClient.get('/kilns', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/kilns/${id}`).then((r) => r.data),
  create: (data: KilnCreateData) =>
    apiClient.post('/kilns', data).then((r) => r.data),
  update: (id: string, data: Partial<KilnCreateData>) =>
    apiClient.patch(`/kilns/${id}`, data).then((r) => r.data),
  updateStatus: (id: string, status: string) =>
    apiClient.patch(`/kilns/${id}/status?status=${status}`).then((r) => r.data),
};

export const kilnConstantsApi = {
  list: () =>
    apiClient.get('/kiln-constants').then((r) => r.data),
  update: (id: string, data: { value?: number; unit?: string; description?: string }) =>
    apiClient.patch(`/kiln-constants/${id}`, data).then((r) => r.data),
};

export const kilnLoadingRulesApi = {
  list: () =>
    apiClient.get('/kiln-loading-rules').then((r) => r.data),
  create: (data: { kiln_id: string; rules: Record<string, unknown> }) =>
    apiClient.post('/kiln-loading-rules', data).then((r) => r.data),
  update: (id: string, data: { rules: Record<string, unknown> }) =>
    apiClient.patch(`/kiln-loading-rules/${id}`, data).then((r) => r.data),
};
