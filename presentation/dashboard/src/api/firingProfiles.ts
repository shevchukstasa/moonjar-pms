import apiClient from './client';

export interface FiringProfile {
  id: string;
  name: string;
  temperature_group_id: string | null;
  temperature_group_name: string | null;
  max_temperature: number;
  target_temperature: number;
  total_duration_hours: number;
  ramp_rate: number | null;
  cooling_type: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface FiringProfileForm {
  name: string;
  temperature_group_id?: string | null;
  max_temperature?: number;
  target_temperature?: number;
  total_duration_hours: number;
  ramp_rate?: number | null;
  cooling_type?: string | null;
  is_active?: boolean;
}

export const firingProfilesApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/firing-profiles', { params }).then((r) => r.data),
  create: (data: FiringProfileForm) =>
    apiClient.post('/firing-profiles', data).then((r) => r.data),
  update: (id: string, data: Partial<FiringProfileForm>) =>
    apiClient.patch(`/firing-profiles/${id}`, data).then((r) => r.data),
  delete: (id: string) =>
    apiClient.delete(`/firing-profiles/${id}`).then((r) => r.data),
};
