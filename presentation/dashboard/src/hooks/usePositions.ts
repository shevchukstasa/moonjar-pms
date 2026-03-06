import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { positionsApi, type PositionListParams } from '@/api/positions';

export function usePositions(params?: PositionListParams) {
  return useQuery({
    queryKey: ['positions', params],
    queryFn: () => positionsApi.list(params),
  });
}

export function usePosition(id?: string) {
  return useQuery({
    queryKey: ['positions', id],
    queryFn: () => positionsApi.get(id!),
    enabled: !!id,
  });
}

export function useChangePositionStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: string; notes?: string }) =>
      positionsApi.changeStatus(id, status, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['positions'] });
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['schedule'] });
    },
  });
}
