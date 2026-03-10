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

// --- Cancellation requests ---

export function useCancellationRequests(params?: { factory_id?: string; decision?: string }) {
  return useQuery({
    queryKey: ['orders', 'cancellation-requests', params],
    queryFn: () => ordersApi.listCancellationRequests(params),
    // Poll every 30s so PM sees new requests promptly
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}

export function useAcceptCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => ordersApi.acceptCancellation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['orders', 'cancellation-requests'] });
    },
  });
}

export function useRejectCancellation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => ordersApi.rejectCancellation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['orders', 'cancellation-requests'] });
    },
  });
}

// --- Change requests ---

export function useChangeRequests(params?: { factory_id?: string }) {
  return useQuery({
    queryKey: ['orders', 'change-requests', params],
    queryFn: () => ordersApi.listChangeRequests(params),
    // Poll every 60s (less urgent than cancellations)
    refetchInterval: 60_000,
    staleTime: 50_000,
  });
}

export function useApproveChange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => ordersApi.approveChange(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['orders', 'change-requests'] });
    },
  });
}

export function useRejectChange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => ordersApi.rejectChange(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['orders', 'change-requests'] });
    },
  });
}

// --- Ship order ---

export function useShipOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => ordersApi.ship(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}
