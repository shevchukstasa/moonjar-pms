import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import type { ListParams } from '@/types/api';
export function useMaterials(params?: ListParams) { return useQuery({ queryKey: ['materials', params], queryFn: () => apiClient.get('/materials', { params }).then((r) => r.data) }); }
