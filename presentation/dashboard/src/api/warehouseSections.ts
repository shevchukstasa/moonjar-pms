import apiClient from './client';

export interface WarehouseSection {
  id: string;
  factory_id: string | null;
  factory_name?: string | null;
  code: string;
  name: string;
  description: string | null;
  managed_by: string | null;
  managed_by_name: string | null;
  warehouse_type: string;
  display_order: number;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface WarehouseSectionInput {
  factory_id?: string | null;
  code: string;
  name: string;
  description?: string;
  managed_by?: string | null;
  warehouse_type?: string;
  display_order?: number;
  is_default?: boolean;
  is_active?: boolean;
}

export interface WarehouseSectionUpdate {
  factory_id?: string | null;
  code?: string;
  name?: string;
  description?: string;
  managed_by?: string | null;
  warehouse_type?: string;
  display_order?: number;
  is_default?: boolean;
  is_active?: boolean;
}

export interface WarehouseSectionListParams {
  factory_id?: string;
  warehouse_type?: string;
  managed_by?: string;
  include_global?: boolean;
  page?: number;
  per_page?: number;
}

export const warehouseSectionsApi = {
  list: (params?: WarehouseSectionListParams) =>
    apiClient.get('/warehouse-sections', { params }).then((r) => r.data),

  listAll: (includeInactive = false) =>
    apiClient.get('/warehouse-sections/all', { params: { include_inactive: includeInactive } }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get(`/warehouse-sections/${id}`).then((r) => r.data),

  create: (data: WarehouseSectionInput) =>
    apiClient.post('/warehouse-sections', data).then((r) => r.data),

  update: (id: string, data: WarehouseSectionUpdate) =>
    apiClient.patch(`/warehouse-sections/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/warehouse-sections/${id}`).then((r) => r.data),
};
