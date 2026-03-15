import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationsApi, type NotificationPreference } from '@/api/notifications';

export function useNotificationPreferences() {
  return useQuery<NotificationPreference[]>({
    queryKey: ['notification-preferences'],
    queryFn: () => notificationsApi.listPreferences(),
  });
}

export function useCreatePreference() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { notification_type: string; channel: string }) =>
      notificationsApi.createPreference(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });
}

export function useUpdatePreference() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { channel: string } }) =>
      notificationsApi.updatePreference(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });
}

export function useDeletePreference() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.deletePreference(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });
}
