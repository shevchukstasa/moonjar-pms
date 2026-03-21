import apiClient from './client';

export interface DashboardAccessItem {
  id: string;
  user_id: string;
  dashboard_type: string;
  granted_by: string;
  granted_at: string;
}

export interface DashboardAccessListResponse {
  items: DashboardAccessItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface DashboardAccessCreatePayload {
  user_id: string;
  dashboard_type: string;
  granted_by: string;
}

export const dashboardAccessApi = {
  list: (params?: { page?: number; per_page?: number }) =>
    apiClient.get<DashboardAccessListResponse>('/dashboard-access', { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<DashboardAccessItem>(`/dashboard-access/${id}`).then((r) => r.data),

  create: (data: DashboardAccessCreatePayload) =>
    apiClient.post<DashboardAccessItem>('/dashboard-access', data).then((r) => r.data),

  remove: (id: string) =>
    apiClient.delete(`/dashboard-access/${id}`),
};
