import apiClient from './client';

export interface ShipmentItemCreate {
  position_id: string;
  quantity_shipped: number;
  box_number?: number | null;
  notes?: string | null;
}

export interface ShipmentCreate {
  order_id: string;
  tracking_number?: string | null;
  carrier?: string | null;
  shipping_method?: string | null;
  total_boxes?: number | null;
  total_weight_kg?: number | null;
  estimated_delivery?: string | null;
  notes?: string | null;
  items: ShipmentItemCreate[];
}

export interface ShipmentUpdate {
  tracking_number?: string | null;
  carrier?: string | null;
  shipping_method?: string | null;
  total_boxes?: number | null;
  total_weight_kg?: number | null;
  estimated_delivery?: string | null;
  received_by?: string | null;
  delivery_note_url?: string | null;
  notes?: string | null;
}

export interface ShipmentItem {
  id: string;
  shipment_id: string;
  position_id: string;
  quantity_shipped: number;
  box_number?: number | null;
  notes?: string | null;
  color?: string | null;
  size?: string | null;
  position_label?: string | null;
}

export interface Shipment {
  id: string;
  order_id: string;
  factory_id: string;
  tracking_number?: string | null;
  carrier?: string | null;
  shipping_method?: string | null;
  total_pieces: number;
  total_boxes?: number | null;
  total_weight_kg?: number | null;
  status: string;
  shipped_at?: string | null;
  estimated_delivery?: string | null;
  delivered_at?: string | null;
  shipped_by?: string | null;
  received_by?: string | null;
  delivery_note_url?: string | null;
  notes?: string | null;
  created_at: string;
  items: ShipmentItem[];
}

export interface ShipmentListResponse {
  items: Shipment[];
  total: number;
  page: number;
  per_page: number;
}

export const shipmentsApi = {
  list: (params?: { order_id?: string; factory_id?: string; status?: string }) =>
    apiClient.get<ShipmentListResponse>('/shipments', { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Shipment>(`/shipments/${id}`).then((r) => r.data),

  create: (data: ShipmentCreate) =>
    apiClient.post<Shipment>('/shipments', data).then((r) => r.data),

  update: (id: string, data: ShipmentUpdate) =>
    apiClient.patch<Shipment>(`/shipments/${id}`, data).then((r) => r.data),

  ship: (id: string) =>
    apiClient.post<Shipment>(`/shipments/${id}/ship`).then((r) => r.data),

  deliver: (id: string, received_by?: string) =>
    apiClient.post<Shipment>(`/shipments/${id}/deliver`, null, {
      params: received_by ? { received_by } : undefined,
    }).then((r) => r.data),

  cancel: (id: string) =>
    apiClient.delete(`/shipments/${id}`).then((r) => r.data),
};
