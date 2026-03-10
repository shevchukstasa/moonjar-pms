import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';

export function useNotifications(params?: { per_page?: number; unread_only?: boolean }) {
  return useQuery({
    queryKey: ['notifications', params],
    queryFn: () =>
      apiClient
        .get('/notifications', { params })
        .then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 50_000,
  });
}

export function useUnreadNotificationsCount() {
  return useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: () =>
      apiClient
        .get('/notifications', { params: { unread_only: true, per_page: 1 } })
        .then((r) => r.data as { total: number; unread_count: number }),
    refetchInterval: 60_000,
    staleTime: 50_000,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.patch(`/notifications/${id}/read`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiClient.post('/notifications/read-all').then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}
