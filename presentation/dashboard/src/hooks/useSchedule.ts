import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { scheduleApi, type BatchListParams } from '@/api/schedule';

export function useResources(params?: { factory_id?: string; resource_type?: string }) {
  return useQuery({
    queryKey: ['schedule', 'resources', params],
    queryFn: () => scheduleApi.resources(params),
  });
}

export function useBatches(params?: BatchListParams) {
  return useQuery({
    queryKey: ['schedule', 'batches', params],
    queryFn: () => scheduleApi.batches(params),
  });
}

export function useCreateBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { resource_id: string; factory_id: string; batch_date: string; position_ids?: string[]; notes?: string }) =>
      scheduleApi.createBatch(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['schedule'] });
      qc.invalidateQueries({ queryKey: ['positions'] });
    },
  });
}

export function useGlazingSchedule(factoryId?: string | null) {
  return useQuery({
    queryKey: ['schedule', 'glazing', factoryId],
    queryFn: () => scheduleApi.glazingSchedule(factoryId ? { factory_id: factoryId } : undefined),
  });
}

export function useFiringSchedule(factoryId?: string | null) {
  return useQuery({
    queryKey: ['schedule', 'firing', factoryId],
    queryFn: () => scheduleApi.firingSchedule(factoryId ? { factory_id: factoryId } : undefined),
  });
}

export function useSortingSchedule(factoryId?: string | null) {
  return useQuery({
    queryKey: ['schedule', 'sorting', factoryId],
    queryFn: () => scheduleApi.sortingSchedule(factoryId ? { factory_id: factoryId } : undefined),
  });
}

export function useQcSchedule(factoryId?: string | null) {
  return useQuery({
    queryKey: ['schedule', 'qc', factoryId],
    queryFn: () => scheduleApi.qcSchedule(factoryId ? { factory_id: factoryId } : undefined),
  });
}

export function useKilnSchedule(factoryId?: string | null) {
  return useQuery({
    queryKey: ['schedule', 'kilns', factoryId],
    queryFn: () => scheduleApi.kilnSchedule(factoryId ? { factory_id: factoryId } : undefined),
  });
}

export function useReorderPositions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (positionIds: string[]) => scheduleApi.reorderPositions(positionIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['schedule'] });
      qc.invalidateQueries({ queryKey: ['positions'] });
    },
  });
}

export function useAssignBatchPositions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ batchId, positionIds }: { batchId: string; positionIds: string[] }) =>
      scheduleApi.assignBatchPositions(batchId, positionIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['schedule'] });
      qc.invalidateQueries({ queryKey: ['positions'] });
    },
  });
}

export function useProductionSchedule(factoryId?: string | null, days = 7) {
  return useQuery({
    queryKey: ['schedule', 'production', factoryId, days],
    queryFn: () => scheduleApi.productionSchedule({ factory_id: factoryId!, days }),
    enabled: !!factoryId,
  });
}

export function useAutoFormBatches() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { factory_id: string; target_date?: string; mode?: string }) =>
      scheduleApi.autoFormBatches(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['schedule'] });
      qc.invalidateQueries({ queryKey: ['positions'] });
    },
  });
}
