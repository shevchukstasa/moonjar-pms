import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  qualityApi,
  type InspectionItem,
  type QcPositionItem,
  type QualityStats,
  type InspectionInput,
  type ChecklistItem,
  type ChecklistInput,
  type ChecklistItemsDef,
} from '@/api/quality';

export type { InspectionItem, QcPositionItem, QualityStats, ChecklistItem, ChecklistInput };

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

// ── Structured QC Checklists ─────────────────────────────────────────

export function useChecklistItems(checkType: 'pre_kiln' | 'final') {
  return useQuery<ChecklistItemsDef>({
    queryKey: ['checklist-items', checkType],
    queryFn: () => qualityApi.getChecklistItems(checkType),
    staleTime: Infinity, // Static definitions, never stale
  });
}

export function usePreKilnChecks(positionId?: string, factoryId?: string) {
  const params: Record<string, string> = {};
  if (positionId) params.position_id = positionId;
  if (factoryId) params.factory_id = factoryId;
  return useQuery<{ items: ChecklistItem[]; total: number }>({
    queryKey: ['pre-kiln-checks', params],
    queryFn: () => qualityApi.listPreKilnChecks(params),
  });
}

export function useFinalChecks(positionId?: string, factoryId?: string) {
  const params: Record<string, string> = {};
  if (positionId) params.position_id = positionId;
  if (factoryId) params.factory_id = factoryId;
  return useQuery<{ items: ChecklistItem[]; total: number }>({
    queryKey: ['final-checks', params],
    queryFn: () => qualityApi.listFinalChecks(params),
  });
}

export function useCreatePreKilnCheck() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ChecklistInput) => qualityApi.createPreKilnCheck(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pre-kiln-checks'] });
      qc.invalidateQueries({ queryKey: ['positions-for-qc'] });
      qc.invalidateQueries({ queryKey: ['quality-stats'] });
    },
  });
}

export function useCreateFinalCheck() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ChecklistInput) => qualityApi.createFinalCheck(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['final-checks'] });
      qc.invalidateQueries({ queryKey: ['positions-for-qc'] });
      qc.invalidateQueries({ queryKey: ['quality-stats'] });
    },
  });
}
