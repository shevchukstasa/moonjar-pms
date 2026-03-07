import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { qualityApi, type InspectionItem, type QcPositionItem, type QualityStats, type InspectionInput } from '@/api/quality';

export type { InspectionItem, QcPositionItem, QualityStats };

export function useInspections(params?: Record<string, unknown>) {
  return useQuery<{ items: InspectionItem[]; total: number }>({
    queryKey: ['inspections', params],
    queryFn: () => qualityApi.listInspections(params),
  });
}

export function usePositionsForQc(factoryId?: string) {
  const params = factoryId ? { factory_id: factoryId } : undefined;
  return useQuery<{ items: QcPositionItem[]; total: number }>({
    queryKey: ['positions-for-qc', params],
    queryFn: () => qualityApi.getPositionsForQc(params),
  });
}

export function useQualityStats(factoryId?: string) {
  const params = factoryId ? { factory_id: factoryId } : undefined;
  return useQuery<QualityStats>({
    queryKey: ['quality-stats', params],
    queryFn: () => qualityApi.getStats(params),
  });
}

export function useCreateInspection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: InspectionInput) => qualityApi.createInspection(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inspections'] });
      qc.invalidateQueries({ queryKey: ['positions-for-qc'] });
      qc.invalidateQueries({ queryKey: ['quality-stats'] });
      qc.invalidateQueries({ queryKey: ['qm-blocks'] });
    },
  });
}

export function useUpdateInspection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      qualityApi.updateInspection(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inspections'] });
      qc.invalidateQueries({ queryKey: ['positions-for-qc'] });
      qc.invalidateQueries({ queryKey: ['quality-stats'] });
      qc.invalidateQueries({ queryKey: ['qm-blocks'] });
    },
  });
}
