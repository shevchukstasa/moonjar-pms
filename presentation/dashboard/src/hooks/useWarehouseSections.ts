import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  warehouseSectionsApi,
  type WarehouseSection,
  type WarehouseSectionInput,
  type WarehouseSectionUpdate,
  type WarehouseSectionListParams,
} from '@/api/warehouseSections';

export type { WarehouseSection };

export function useWarehouseSections(params?: WarehouseSectionListParams) {
  return useQuery<{ items: WarehouseSection[]; total: number }>({
    queryKey: ['warehouse-sections', params],
    queryFn: () => warehouseSectionsApi.list({ ...params, per_page: 200 }),
    staleTime: 5 * 60_000,
  });
}

export function useAllWarehouseSections(includeInactive = false) {
  return useQuery<{ items: WarehouseSection[]; total: number }>({
    queryKey: ['warehouse-sections', 'all', includeInactive],
    queryFn: () => warehouseSectionsApi.listAll(includeInactive),
    staleTime: 5 * 60_000,
  });
}

export function useCreateWarehouseSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: WarehouseSectionInput) => warehouseSectionsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['warehouse-sections'] });
    },
  });
}

export function useUpdateWarehouseSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WarehouseSectionUpdate }) =>
      warehouseSectionsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['warehouse-sections'] });
    },
  });
}

export function useDeleteWarehouseSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => warehouseSectionsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['warehouse-sections'] });
    },
  });
}
