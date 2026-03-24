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
    queryFn: () => referenceApi.getCollections(),
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
    queryFn: () => referenceApi.getColors(),
    staleTime: 5 * 60 * 1000,
  });
}
