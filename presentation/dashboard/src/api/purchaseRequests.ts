import apiClient from './client';

export interface PurchaseRequestItem {
  id: string;
  factory_id: string;
  supplier_id: string | null;
  supplier_name: string | null;
  materials_json: Record<string, unknown> | Array<Record<string, unknown>>;
  status: string;
  source: string;
  approved_by: string | null;
  approved_by_name: string | null;
  ordered_at: string | null;
  expected_delivery_date: string | null;
  actual_delivery_date: string | null;
  received_quantity_json: Record<string, unknown> | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PurchaserStats {
  active_requests: number;
  pending_approval: number;
  awaiting_delivery: number;
  overdue_deliveries: number;
}

export const purchaseRequestsApi = {
  list: (params?: { factory_id?: string; status?: string; supplier_id?: string; page?: number; per_page?: number }) =>
    apiClient.get('/purchaser', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/purchaser/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/purchaser', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/purchaser/${id}`, data).then((r) => r.data),
  changeStatus: (id: string, data: { status: string; notes?: string; expected_delivery_date?: string; actual_delivery_date?: string }) =>
    apiClient.patch(`/purchaser/${id}/status`, data).then((r) => r.data),
  getStats: (params?: { factory_id?: string }) =>
    apiClient.get('/purchaser/stats', { params }).then((r) => r.data),
  listDeliveries: (params?: { factory_id?: string; page?: number; per_page?: number }) =>
    apiClient.get('/purchaser/deliveries', { params }).then((r) => r.data),
};
