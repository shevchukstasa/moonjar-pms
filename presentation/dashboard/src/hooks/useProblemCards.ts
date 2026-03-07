import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { problemCardsApi, type ProblemCardItem } from '@/api/problemCards';

export type { ProblemCardItem };

export function useProblemCards(factoryId?: string, status?: string) {
  const params: Record<string, string> = {};
  if (factoryId) params.factory_id = factoryId;
  if (status) params.status = status;
  return useQuery<{ items: ProblemCardItem[]; total: number }>({
    queryKey: ['problem-cards', params],
    queryFn: () => problemCardsApi.list(Object.keys(params).length > 0 ? params : undefined),
  });
}

export function useCreateProblemCard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { factory_id: string; location?: string; description: string }) =>
      problemCardsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['problem-cards'] });
      qc.invalidateQueries({ queryKey: ['quality-stats'] });
    },
  });
}

export function useUpdateProblemCard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      problemCardsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['problem-cards'] });
      qc.invalidateQueries({ queryKey: ['quality-stats'] });
    },
  });
}
