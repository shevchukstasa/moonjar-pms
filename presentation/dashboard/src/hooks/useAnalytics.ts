import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/api/analytics';

export function useDashboardSummary(params?: { factory_id?: string; date_from?: string; date_to?: string }) {
  return useQuery({
    queryKey: ['dashboard-summary', params],
    queryFn: () => analyticsApi.getDashboardSummary(params),
    staleTime: 60_000,
  });
}

export function useProductionMetrics(params?: { factory_id?: string; date_from?: string; date_to?: string }) {
  return useQuery({
    queryKey: ['production-metrics', params],
    queryFn: () => analyticsApi.getProductionMetrics(params),
    staleTime: 30_000,
  });
}

export function useMaterialMetrics(params?: { factory_id?: string }) {
  return useQuery({
    queryKey: ['material-metrics', params],
    queryFn: () => analyticsApi.getMaterialMetrics(params),
    staleTime: 60_000,
  });
}

export function useFactoryComparison() {
  return useQuery({
    queryKey: ['factory-comparison'],
    queryFn: () => analyticsApi.getFactoryComparison(),
    staleTime: 60_000,
  });
}

export function useBufferHealth(params?: { factory_id?: string }) {
  return useQuery({
    queryKey: ['buffer-health', params],
    queryFn: () => analyticsApi.getBufferHealth(params),
    refetchInterval: 60_000,
  });
}

export function useTrendData(metric: string, factoryId?: string, months = 6) {
  return useQuery({
    queryKey: ['trend-data', metric, factoryId, months],
    queryFn: () => analyticsApi.getTrendData(metric, { factory_id: factoryId, months }),
    staleTime: 5 * 60_000,
  });
}

export function useActivityFeed(params?: { factory_id?: string; limit?: number }) {
  return useQuery({
    queryKey: ['activity-feed', params],
    queryFn: () => analyticsApi.getActivityFeed(params),
    refetchInterval: 30_000,
  });
}
