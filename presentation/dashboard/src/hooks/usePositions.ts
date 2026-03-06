import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import type { ListParams } from '@/types/api';
export function usePositions(params?: ListParams) { return useQuery({ queryKey: ['positions', params], queryFn: () => apiClient.get('/positions', { params }).then((r) => r.data) }); }
