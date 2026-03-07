import apiClient from './client';

export interface PackingPhotoListParams {
  position_id?: string;
  order_id?: string;
  page?: number;
  per_page?: number;
}

export interface PackingPhotoItem {
  id: string;
  order_id: string;
  position_id: string | null;
  photo_url: string;
  uploaded_by: string | null;
  uploaded_at: string;
  notes: string | null;
  order_number: string | null;
  uploader_name: string | null;
}

export interface PackingPhotoCreatePayload {
  order_id: string;
  position_id?: string;
  photo_url: string;
  notes?: string;
}

export const packingPhotosApi = {
  list: (params?: PackingPhotoListParams) =>
    apiClient.get('/packing-photos', { params }).then((r) => r.data),

  create: (data: PackingPhotoCreatePayload) =>
    apiClient.post('/packing-photos', data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/packing-photos/${id}`).then((r) => r.data),
};
