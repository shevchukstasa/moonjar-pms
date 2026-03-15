import apiClient from './client';

export interface NotificationPreference {
  id: string;
  user_id: string;
  notification_type: string;
  channel: 'in_app' | 'telegram' | 'both';
  created_at: string;
}

export const notificationsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/notifications', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/notifications/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/notifications', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/notifications/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/notifications/${id}`).then((r) => r.data),

  // Notification preferences
  listPreferences: () =>
    apiClient.get<NotificationPreference[]>('/notification-preferences').then((r) => r.data),
  createPreference: (data: { notification_type: string; channel: string }) =>
    apiClient.post<NotificationPreference>('/notification-preferences', data).then((r) => r.data),
  updatePreference: (id: string, data: { channel: string }) =>
    apiClient.patch<NotificationPreference>(`/notification-preferences/${id}`, data).then((r) => r.data),
  deletePreference: (id: string) =>
    apiClient.delete(`/notification-preferences/${id}`).then((r) => r.data),
};
