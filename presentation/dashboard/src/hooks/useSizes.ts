import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sizesApi, type SizeItem, type SizeInput } from '@/api/sizes';

export type { SizeItem, SizeInput };

export function useSizes() {
  return useQuery<{ items: SizeItem[]; total: number }>({
    queryKey: ['sizes'],
    queryFn: () => sizesApi.list(),
  });
}

export function useCreateSize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SizeInput) => sizesApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sizes'] });
      qc.invalidateQueries({ queryKey: ['packaging-sizes'] });
    },
  });
}

export function useUpdateSize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SizeInput> }) => sizesApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sizes'] });
      qc.invalidateQueries({ queryKey: ['packaging-sizes'] });
    },
  });
}

export function useDeleteSize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => sizesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sizes'] });
      qc.invalidateQueries({ queryKey: ['packaging-sizes'] });
    },
  });
}
