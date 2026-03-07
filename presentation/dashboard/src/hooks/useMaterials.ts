import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { materialsApi, type MaterialListParams, type MaterialItem, type TransactionItem, type TransactionInput } from '@/api/materials';

export type { MaterialItem, TransactionItem };

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
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      materialsApi.update(id, data),
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
