import { useQuery } from '@tanstack/react-query';
import { referenceApi, type ReferenceItem, type AllReferenceData } from '@/api/reference';

export type { ReferenceItem, AllReferenceData };

export function useReferenceData() {
  return useQuery<AllReferenceData>({
    queryKey: ['reference', 'all'],
    queryFn: () => referenceApi.getAll(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useCollections() {
  return useQuery<ReferenceItem[]>({
    queryKey: ['reference', 'collections'],
    queryFn: async () => {
      const raw = await referenceApi.getCollections();
      // API returns {id, name} or {value, label} — normalize
      return (raw as unknown as { id?: string; name?: string; value?: string; label?: string }[]).map((c) => ({
        value: c.value || c.name || '',
        label: c.label || c.name || '',
      }));
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useApplicationMethods() {
  return useQuery({
    queryKey: ['reference', 'application-methods'],
    queryFn: () => referenceApi.getApplicationMethods(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useFinishingTypes() {
  return useQuery<{ id: string; name: string }[]>({
    queryKey: ['reference', 'finishing-types'],
    queryFn: () => referenceApi.getFinishingTypes(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useColors() {
  return useQuery<ReferenceItem[]>({
    queryKey: ['reference', 'colors'],
    queryFn: async () => {
      const raw = await referenceApi.getColors();
      // API returns {id, name}, normalize to {value, label}
      return (raw as unknown as { id: string; name: string }[]).map((c) => ({
        value: c.name,
        label: c.name,
      }));
    },
    staleTime: 5 * 60 * 1000,
  });
}
