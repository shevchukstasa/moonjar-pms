import { useQuery } from '@tanstack/react-query';
import { packagingApi, type PackagingBoxType, type SizeItem } from '@/api/packaging';

export type { PackagingBoxType, SizeItem };

export function usePackagingBoxTypes() {
  return useQuery<{ items: PackagingBoxType[]; total: number }>({
    queryKey: ['packaging-box-types'],
    queryFn: () => packagingApi.list(),
  });
}

export function usePackagingSizes() {
  return useQuery<{ items: SizeItem[] }>({
    queryKey: ['packaging-sizes'],
    queryFn: () => packagingApi.listSizes(),
  });
}
