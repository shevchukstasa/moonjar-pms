import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { materialsApi, type MaterialListParams, type MaterialItem, type TransactionItem, type TransactionInput, type ConsumptionAdjustmentItem } from '@/api/materials';

export type { MaterialItem, TransactionItem, ConsumptionAdjustmentItem };

export function useMaterials(params?: MaterialListParams) {
  return useQuery<{ items: MaterialItem[]; total: number }>({
    queryKey: ['materials', params],
    queryFn: () => materialsApi.list(params),
  });
}

export function useMaterial(id: string | undefined) {
  return useQuery<MaterialItem>({
    queryKey: ['materials', id],
    queryFn: () => materialsApi.get(id!),
    enabled: !!id,
  });
}

export function useMaterialTransactions(materialId: string | undefined) {
  return useQuery<{ items: TransactionItem[]; total: number }>({
    queryKey: ['transactions', materialId],
    queryFn: () => materialsApi.listTransactions(materialId!),
    enabled: !!materialId,
  });
}

export function useLowStock(factoryId?: string) {
  const params = factoryId ? { factory_id: factoryId } : undefined;
  return useQuery<{ items: MaterialItem[]; total: number }>({
    queryKey: ['materials', 'low-stock', params],
    queryFn: () => materialsApi.getLowStock(params),
  });
}

export function useCreateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => materialsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['materials'] });
    },
  });
}

export function useUpdateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data, factoryId }: { id: string; data: Record<string, unknown>; factoryId?: string }) =>
      materialsApi.update(id, data, factoryId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['materials'] });
    },
  });
}

export function useDeleteMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, factoryId }: { id: string; factoryId?: string }) =>
      materialsApi.delete(id, factoryId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['materials'] });
    },
  });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TransactionInput) => materialsApi.createTransaction(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['materials'] });
      qc.invalidateQueries({ queryKey: ['transactions'] });
    },
  });
}

export function useCreatePurchaseRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => materialsApi.createPurchaseRequest(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['materials'] });
      qc.invalidateQueries({ queryKey: ['purchase-requests'] });
    },
  });
}

// ── Consumption Adjustments ──────────────────────────────────────

export function useConsumptionAdjustments(params?: {
  factory_id?: string;
  status?: string;
  page?: number;
  per_page?: number;
}) {
  return useQuery<{ items: ConsumptionAdjustmentItem[]; total: number }>({
    queryKey: ['consumption-adjustments', params],
    queryFn: () => materialsApi.listConsumptionAdjustments(params),
  });
}

export function useApproveAdjustment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      materialsApi.approveAdjustment(id, notes ? { notes } : undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['consumption-adjustments'] });
    },
  });
}

export function useRejectAdjustment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      materialsApi.rejectAdjustment(id, notes ? { notes } : undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['consumption-adjustments'] });
    },
  });
}
