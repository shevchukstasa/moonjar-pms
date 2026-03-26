import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { shipmentsApi, ShipmentCreate, ShipmentUpdate } from '@/api/shipments';

export function useShipments(orderId?: string) {
  return useQuery({
    queryKey: ['shipments', { order_id: orderId }],
    queryFn: () => shipmentsApi.list({ order_id: orderId }),
    enabled: !!orderId,
  });
}

export function useShipment(id?: string) {
  return useQuery({
    queryKey: ['shipments', id],
    queryFn: () => shipmentsApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateShipment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ShipmentCreate) => shipmentsApi.create(data),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['shipments', { order_id: variables.order_id }] });
      qc.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

export function useUpdateShipment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ShipmentUpdate }) =>
      shipmentsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shipments'] });
    },
  });
}

export function useMarkShipped() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => shipmentsApi.ship(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shipments'] });
      qc.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

export function useMarkDelivered() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, received_by }: { id: string; received_by?: string }) =>
      shipmentsApi.deliver(id, received_by),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shipments'] });
      qc.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

export function useCancelShipment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => shipmentsApi.cancel(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shipments'] });
      qc.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}
