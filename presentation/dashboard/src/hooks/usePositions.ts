import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { positionsApi, type PositionListParams, type SortingSplitRequest, type ColorMismatchResolveRequest } from '@/api/positions';

export interface PositionItem {
  id: string;
  order_id: string;
  order_item_id: string;
  parent_position_id: string | null;
  factory_id: string;
  status: string;
  batch_id: string | null;
  resource_id: string | null;
  quantity: number;
  quantity_with_defect_margin: number | null;
  color: string;
  size: string;
  application: string | null;
  finishing: string | null;
  collection: string | null;
  product_type: string;
  shape: string | null;
  split_category: string | null;
  is_merged: boolean;
  priority_order: number;
  order_number: string;
  created_at: string | null;
  updated_at: string | null;
}

export function usePositions(params?: PositionListParams) {
  return useQuery<{ items: PositionItem[]; total: number }>({
    queryKey: ['positions', params],
    queryFn: () => positionsApi.list(params),
  });
}

export function usePosition(id?: string) {
  return useQuery({
    queryKey: ['positions', id],
    queryFn: () => positionsApi.get(id!),
    enabled: !!id,
  });
}

export function useChangePositionStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: string; notes?: string }) =>
      positionsApi.changeStatus(id, status, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['positions'] });
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['schedule'] });
    },
  });
}

export function useSplitPosition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: SortingSplitRequest }) =>
      positionsApi.split(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['positions'] });
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['schedule'] });
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useStockAvailability(positionId?: string) {
  return useQuery({
    queryKey: ['stock-availability', positionId],
    queryFn: () => positionsApi.stockAvailability(positionId!),
    enabled: !!positionId,
  });
}

export function useAllowedTransitions(positionId?: string) {
  return useQuery<{ current_status: string; allowed: string[] }>({
    queryKey: ['positions', positionId, 'allowed-transitions'],
    queryFn: () => positionsApi.allowedTransitions(positionId!),
    enabled: !!positionId,
    staleTime: 0,          // always fresh when dropdown opens
  });
}

export function useResolveColorMismatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ColorMismatchResolveRequest }) =>
      positionsApi.resolveColorMismatch(id, data),
    onSuccess: () => {
      // Invalidate positions (mismatch list refreshes), orders, tasks (new tasks may appear)
      qc.invalidateQueries({ queryKey: ['positions'] });
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}
