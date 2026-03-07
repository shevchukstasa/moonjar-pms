import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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

export function useCreateFactory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; location?: string; timezone?: string; is_active?: boolean }) =>
      factoriesApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['factories'] }); },
  });
}

export function useUpdateFactory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      factoriesApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['factories'] }); },
  });
}
