import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import type { ListParams } from '@/types/api';
export function useTasks(params?: ListParams) { return useQuery({ queryKey: ['tasks', params], queryFn: () => apiClient.get('/tasks', { params }).then((r) => r.data) }); }
