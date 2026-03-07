import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { qmBlocksApi, type QmBlockItem } from '@/api/qmBlocks';

export type { QmBlockItem };

export function useQmBlocks(factoryId?: string) {
  const params = factoryId ? { factory_id: factoryId } : undefined;
  return useQuery<{ items: QmBlockItem[]; total: number }>({
    queryKey: ['qm-blocks', params],
    queryFn: () => qmBlocksApi.list(params),
  });
}

export function useResolveQmBlock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { resolved_by: string; resolved_at: string; resolution_note: string } }) =>
      qmBlocksApi.resolve(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['qm-blocks'] });
      qc.invalidateQueries({ queryKey: ['quality-stats'] });
      qc.invalidateQueries({ queryKey: ['positions-for-qc'] });
    },
  });
}
