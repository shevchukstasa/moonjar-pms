import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ordersApi, type OrderListParams } from '@/api/orders';

export function useOrders(params?: OrderListParams) {
  return useQuery({
    queryKey: ['orders', params],
    queryFn: () => ordersApi.list(params),
  });
}

export function useOrder(id?: string) {
  return useQuery({
    queryKey: ['orders', id],
    queryFn: () => ordersApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => ordersApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  });
}

export function useUpdateOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      ordersApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  });
}

export function useCancelOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => ordersApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  });
}
