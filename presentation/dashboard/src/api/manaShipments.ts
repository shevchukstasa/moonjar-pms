import apiClient from './client';

export interface ManaShipmentItem {
  color: string;
  size: string;
  quantity: number;
  reason: string;
  source_order_id?: string;
  source_position_id?: string;
}

export interface ManaShipment {
  id: string;
  factory_id: string;
  items_json: ManaShipmentItem[];
  status: 'pending' | 'confirmed' | 'shipped';
  confirmed_by: string | null;
  confirmed_at: string | null;
  shipped_at: string | null;
  notes: string | null;
  created_at: string;
}

export const manaShipmentsApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get('/mana-shipments', { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get(`/mana-shipments/${id}`).then((r) => r.data),

  update: (id: string, data: { notes?: string }) =>
    apiClient.patch(`/mana-shipments/${id}`, data).then((r) => r.data),

  confirm: (id: string) =>
    apiClient.post(`/mana-shipments/${id}/confirm`).then((r) => r.data),

  ship: (id: string) =>
    apiClient.post(`/mana-shipments/${id}/ship`).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/mana-shipments/${id}`).then((r) => r.data),
};
