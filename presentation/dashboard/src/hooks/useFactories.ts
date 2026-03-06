import { useQuery } from '@tanstack/react-query';
import { factoriesApi } from '@/api/factories';

export interface Factory {
  id: string;
  name: string;
  location: string | null;
  timezone: string | null;
  is_active: boolean;
}

export function useFactories() {
  return useQuery<{ items: Factory[]; total: number }>({
    queryKey: ['factories'],
    queryFn: () => factoriesApi.list(),
    staleTime: 5 * 60 * 1000, // 5 min cache
  });
}
