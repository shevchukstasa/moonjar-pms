import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { consumptionRulesApi, type ConsumptionRuleItem, type ConsumptionRuleInput } from '@/api/consumptionRules';

export function useConsumptionRules(includeInactive = false) {
  return useQuery<ConsumptionRuleItem[]>({
    queryKey: ['consumption-rules', { includeInactive }],
    queryFn: () =>
      consumptionRulesApi.list(includeInactive ? { include_inactive: true } : undefined),
  });
}

export function useCreateConsumptionRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ConsumptionRuleInput) => consumptionRulesApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['consumption-rules'] });
    },
  });
}

export function useUpdateConsumptionRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ConsumptionRuleInput> }) =>
      consumptionRulesApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['consumption-rules'] });
    },
  });
}

export function useDeleteConsumptionRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => consumptionRulesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['consumption-rules'] });
    },
  });
}
