import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { purchaseRequestsApi, type PurchaseRequestItem, type PurchaserStats } from '@/api/purchaseRequests';

export type { PurchaseRequestItem, PurchaserStats };

export function usePurchaseRequests(params?: { factory_id?: string; status?: string; supplier_id?: string }) {
  return useQuery<{ items: PurchaseRequestItem[]; total: number }>({
    queryKey: ['purchase-requests', params],
    queryFn: () => purchaseRequestsApi.list(params),
  });
}

export function usePurchaserStats(factoryId?: string) {
  const params = factoryId ? { factory_id: factoryId } : undefined;
  return useQuery<PurchaserStats>({
    queryKey: ['purchaser-stats', params],
    queryFn: () => purchaseRequestsApi.getStats(params),
  });
}

export function useDeliveries(factoryId?: string) {
  const params = factoryId ? { factory_id: factoryId } : undefined;
  return useQuery<{ items: PurchaseRequestItem[]; total: number }>({
    queryKey: ['deliveries', params],
    queryFn: () => purchaseRequestsApi.listDeliveries(params),
  });
}

export function useCreatePurchaseRequestPurchaser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => purchaseRequestsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purchase-requests'] });
      qc.invalidateQueries({ queryKey: ['purchaser-stats'] });
    },
  });
}

export function useDeletePurchaseRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => purchaseRequestsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purchase-requests'] });
      qc.invalidateQueries({ queryKey: ['purchaser-stats'] });
      qc.invalidateQueries({ queryKey: ['deliveries'] });
    },
  });
}

export function useChangeRequestStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { status: string; notes?: string; expected_delivery_date?: string } }) =>
      purchaseRequestsApi.changeStatus(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purchase-requests'] });
      qc.invalidateQueries({ queryKey: ['purchaser-stats'] });
      qc.invalidateQueries({ queryKey: ['deliveries'] });
      qc.invalidateQueries({ queryKey: ['materials'] });
    },
  });
}
