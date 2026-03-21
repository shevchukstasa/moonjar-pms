import apiClient from './client';

export interface KilnFiringSchedule {
  id: string;
  kiln_id: string;
  name: string;
  schedule_data: Record<string, unknown>;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface KilnFiringScheduleForm {
  kiln_id: string;
  name: string;
  schedule_data?: Record<string, unknown>;
  is_default?: boolean;
}

export const kilnFiringSchedulesApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/kiln-firing-schedules', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/kiln-firing-schedules/${id}`).then((r) => r.data),
  create: (data: KilnFiringScheduleForm) =>
    apiClient.post('/kiln-firing-schedules', data).then((r) => r.data),
  update: (id: string, data: Partial<KilnFiringScheduleForm>) =>
    apiClient.patch(`/kiln-firing-schedules/${id}`, data).then((r) => r.data),
  delete: (id: string) =>
    apiClient.delete(`/kiln-firing-schedules/${id}`).then((r) => r.data),
};
