import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import type { ListParams } from '@/types/api';
export function useOrders(params?: ListParams) { return useQuery({ queryKey: ['orders', params], queryFn: () => apiClient.get('/orders', { params }).then((r) => r.data) }); }
