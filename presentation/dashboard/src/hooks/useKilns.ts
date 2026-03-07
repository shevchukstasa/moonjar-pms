import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { kilnsApi, kilnConstantsApi, kilnLoadingRulesApi, type KilnListParams, type KilnCreateData } from '@/api/kilns';

export interface KilnItem {
  id: string;
  name: string;
  factory_id: string;
  kiln_type: string;
  status: string;
  kiln_dimensions_cm: { width: number; depth: number; height: number } | null;
  kiln_working_area_cm: { width: number; depth: number; height: number } | null;
  kiln_multi_level: boolean;
  kiln_coefficient: number | null;
  num_levels: number;
  capacity_sqm: number | null;
  capacity_pcs: number | null;
  is_active: boolean;
  loading_rules: Record<string, unknown> | null;
  loading_rules_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface KilnConstantItem {
  id: string;
  constant_name: string;
  value: number;
  unit: string | null;
  description: string | null;
  updated_at: string;
  updated_by: string | null;
}

export function useKilns(params?: KilnListParams) {
  return useQuery<{ items: KilnItem[]; total: number }>({
    queryKey: ['kilns', params],
    queryFn: () => kilnsApi.list(params),
  });
}

export function useKiln(id: string | null) {
  return useQuery<KilnItem>({
    queryKey: ['kilns', id],
    queryFn: () => kilnsApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateKiln() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: KilnCreateData) => kilnsApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kilns'] }); qc.invalidateQueries({ queryKey: ['schedule'] }); },
  });
}

export function useUpdateKiln() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<KilnCreateData> }) => kilnsApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kilns'] }); qc.invalidateQueries({ queryKey: ['schedule'] }); },
  });
}

export function useUpdateKilnStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => kilnsApi.updateStatus(id, status),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kilns'] }); qc.invalidateQueries({ queryKey: ['schedule'] }); },
  });
}

export function useKilnConstants() {
  return useQuery<{ items: KilnConstantItem[]; total: number }>({
    queryKey: ['kiln-constants'],
    queryFn: () => kilnConstantsApi.list(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdateKilnConstant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { value?: number; unit?: string; description?: string } }) =>
      kilnConstantsApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kiln-constants'] }); },
  });
}

export function useUpdateLoadingRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, rules }: { id: string; rules: Record<string, unknown> }) =>
      kilnLoadingRulesApi.update(id, { rules }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kilns'] }); },
  });
}

export function useCreateLoadingRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { kiln_id: string; rules: Record<string, unknown> }) =>
      kilnLoadingRulesApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['kilns'] }); },
  });
}
