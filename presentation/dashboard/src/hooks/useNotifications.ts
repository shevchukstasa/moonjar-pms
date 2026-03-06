import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
export function useNotifications() { return useQuery({ queryKey: ['notifications', 'unread-count'], queryFn: () => apiClient.get('/notifications?unread_only=true&per_page=1').then((r) => r.data), refetchInterval: 60_000 }); }
