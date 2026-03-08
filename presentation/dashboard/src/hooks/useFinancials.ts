import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { financialsApi } from '@/api/financials';

export function useFinancialSummary(params?: { factory_id?: string; date_from?: string; date_to?: string }) {
  return useQuery({
    queryKey: ['financial-summary', params],
    queryFn: () => financialsApi.getSummary(params),
    staleTime: 60_000,
  });
}

export function useFinancialEntries(params?: { factory_id?: string; page?: number; per_page?: number }) {
  return useQuery({
    queryKey: ['financial-entries', params],
    queryFn: () => financialsApi.list(params),
  });
}

export function useCreateFinancialEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: financialsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['financial-entries'] });
      qc.invalidateQueries({ queryKey: ['financial-summary'] });
    },
  });
}
