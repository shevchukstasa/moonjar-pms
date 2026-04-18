import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { designsApi, type StoneDesign, type DesignCreateInput, type DesignUpdateInput } from '@/api/designs';

export type { StoneDesign, DesignCreateInput, DesignUpdateInput };

export function useDesigns(params?: { typology?: string; include_inactive?: boolean }) {
  return useQuery({
    queryKey: ['designs', params],
    queryFn: () => designsApi.list(params),
  });
}

export function useCreateDesign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DesignCreateInput) => designsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['designs'] });
      qc.invalidateQueries({ queryKey: ['materials'] });
    },
  });
}

export function useUpdateDesign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DesignUpdateInput }) =>
      designsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['designs'] });
      qc.invalidateQueries({ queryKey: ['materials'] });
    },
  });
}

export function useDeleteDesign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => designsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['designs'] });
      qc.invalidateQueries({ queryKey: ['materials'] });
    },
  });
}
