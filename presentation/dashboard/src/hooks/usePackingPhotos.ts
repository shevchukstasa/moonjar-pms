import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  packingPhotosApi,
  type PackingPhotoListParams,
  type PackingPhotoItem,
} from '@/api/packingPhotos';
import { uploadFile } from '@/hooks/useSupabaseUpload';

export function usePackingPhotos(params?: PackingPhotoListParams) {
  return useQuery<{ items: PackingPhotoItem[]; total: number }>({
    queryKey: ['packing-photos', params],
    queryFn: () => packingPhotosApi.list(params),
    enabled: !!params?.position_id,
  });
}

export interface UploadPackingPhotoArgs {
  file: File;
  orderId: string;
  positionId: string;
  notes?: string;
}

export function useUploadPackingPhoto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, orderId, positionId, notes }: UploadPackingPhotoArgs) => {
      // 1. Upload to Supabase Storage
      const timestamp = Date.now();
      const ext = file.name.split('.').pop() || 'jpg';
      const path = `${orderId}/${positionId}_${timestamp}.${ext}`;
      const publicUrl = await uploadFile('packing-photos', path, file);

      // 2. Save metadata to backend
      return packingPhotosApi.create({
        order_id: orderId,
        position_id: positionId,
        photo_url: publicUrl,
        notes,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['packing-photos'] });
    },
  });
}

export function useDeletePackingPhoto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => packingPhotosApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['packing-photos'] });
    },
  });
}
