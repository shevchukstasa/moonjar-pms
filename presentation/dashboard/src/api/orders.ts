import apiClient from './client';

export interface OrderListParams {
  page?: number;
  per_page?: number;
  factory_id?: string;
  status?: string;
  search?: string;
  tab?: 'current' | 'archive';
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface CancellationRequestItem {
  id: string;
  order_number: string;
  client: string;
  client_location: string | null;
  factory_id: string;
  factory_name: string;
  status: string;
  current_stage: string;
  positions_count: number;
  positions_ready: number;
  final_deadline: string | null;
  external_id: string | null;
  cancellation_requested_at: string | null;
  cancellation_decision: 'pending' | 'accepted' | 'rejected' | null;
  cancellation_decided_at: string | null;
}

export const ordersApi = {
  list: (params?: OrderListParams) =>
    apiClient.get('/orders', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/orders/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/orders', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/orders/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/orders/${id}`).then((r) => r.data),
  ship: (id: string) =>
    apiClient.patch(`/orders/${id}/ship`).then((r) => r.data),
  // Cancellation request management
  listCancellationRequests: (params?: { factory_id?: string; decision?: string }) =>
    apiClient.get('/orders/cancellation-requests', { params }).then((r) => r.data),
  acceptCancellation: (id: string) =>
    apiClient.post(`/orders/${id}/accept-cancellation`).then((r) => r.data),
  rejectCancellation: (id: string) =>
    apiClient.post(`/orders/${id}/reject-cancellation`).then((r) => r.data),
};
