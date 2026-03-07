import apiClient from './client';

export interface QmBlockItem {
  id: string;
  factory_id: string;
  block_type: string;
  position_id: string | null;
  batch_id: string | null;
  reason: string;
  severity: string;
  blocked_by: string;
  resolved_by: string | null;
  resolved_at: string | null;
  resolution_note: string | null;
  created_at: string;
}

export const qmBlocksApi = {
  list: (params?: { factory_id?: string; page?: number; per_page?: number }) =>
    apiClient.get('/qm-blocks', { params }).then((r) => r.data),
  resolve: (id: string, data: { resolved_by: string; resolved_at: string; resolution_note: string }) =>
    apiClient.patch(`/qm-blocks/${id}`, data).then((r) => r.data),
};
