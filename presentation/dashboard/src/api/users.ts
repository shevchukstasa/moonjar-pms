import apiClient from './client';

export interface UserListParams {
  page?: number;
  per_page?: number;
  role?: string;
  is_active?: boolean;
  search?: string;
  factory_id?: string;
}

export const usersApi = {
  list: (params?: UserListParams) =>
    apiClient.get('/users', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/users/${id}`).then((r) => r.data),
  create: (data: { email: string; name: string; role: string; password: string; factory_ids?: string[]; language?: string }) =>
    apiClient.post('/users', data).then((r) => r.data),
  update: (id: string, data: { name?: string; role?: string; language?: string; factory_ids?: string[] }) =>
    apiClient.patch(`/users/${id}`, data).then((r) => r.data),
  toggleActive: (id: string) =>
    apiClient.post(`/users/${id}/toggle-active`).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/users/${id}`).then((r) => r.data),
};
