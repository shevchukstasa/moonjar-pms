import apiClient from './client';

// ── Types ────────────────────────────────────────────────────────────────

export interface MaterialSubgroup {
  id: string;
  group_id: string;
  group_name: string | null;
  name: string;
  code: string;
  description: string | null;
  icon: string | null;
  default_lead_time_days: number | null;
  default_unit: string;
  display_order: number;
  is_active: boolean;
  material_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface MaterialGroup {
  id: string;
  name: string;
  code: string;
  description: string | null;
  icon: string | null;
  display_order: number;
  is_active: boolean;
  subgroups: MaterialSubgroup[];
  created_at: string | null;
  updated_at: string | null;
}

export interface MaterialGroupInput {
  name: string;
  code: string;
  description?: string;
  icon?: string;
  display_order?: number;
}

export interface MaterialGroupUpdate {
  name?: string;
  code?: string;
  description?: string;
  icon?: string;
  display_order?: number;
  is_active?: boolean;
}

export interface MaterialSubgroupInput {
  group_id: string;
  name: string;
  code: string;
  description?: string;
  icon?: string;
  default_lead_time_days?: number;
  default_unit?: string;
  display_order?: number;
}

export interface MaterialSubgroupUpdate {
  group_id?: string;
  name?: string;
  code?: string;
  description?: string;
  icon?: string;
  default_lead_time_days?: number;
  default_unit?: string;
  display_order?: number;
  is_active?: boolean;
}

// ── API ──────────────────────────────────────────────────────────────────

export const materialGroupsApi = {
  // Hierarchy (nested tree)
  getHierarchy: (includeInactive = false) =>
    apiClient
      .get<MaterialGroup[]>('/material-groups/hierarchy', {
        params: includeInactive ? { include_inactive: true } : undefined,
      })
      .then((r) => r.data),

  // Groups
  listGroups: (includeInactive = false) =>
    apiClient
      .get('/material-groups/groups', {
        params: includeInactive ? { include_inactive: true } : undefined,
      })
      .then((r) => r.data),

  createGroup: (data: MaterialGroupInput) =>
    apiClient.post('/material-groups/groups', data).then((r) => r.data),

  updateGroup: (id: string, data: MaterialGroupUpdate) =>
    apiClient.put(`/material-groups/groups/${id}`, data).then((r) => r.data),

  // Subgroups
  listSubgroups: (params?: { group_id?: string; include_inactive?: boolean }) =>
    apiClient
      .get<MaterialSubgroup[]>('/material-groups/subgroups', { params })
      .then((r) => r.data),

  createSubgroup: (data: MaterialSubgroupInput) =>
    apiClient.post('/material-groups/subgroups', data).then((r) => r.data),

  updateSubgroup: (id: string, data: MaterialSubgroupUpdate) =>
    apiClient.put(`/material-groups/subgroups/${id}`, data).then((r) => r.data),
};
