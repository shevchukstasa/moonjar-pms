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

export interface ChangeRequestItem {
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
  change_req_requested_at: string | null;
  change_req_status: 'pending' | 'approved' | 'rejected' | 'none';
  change_req_payload: Record<string, unknown> | null;
  change_summary: Record<string, unknown>;
}

// --- PDF Upload types ---
export interface FieldConfidence {
  value: number;
  source: string; // "regex" | "table" | "positional" | "fallback" | "not_found"
}

export interface PdfParsedItem {
  color: string;
  size: string;
  quantity_pcs: number;
  quantity_sqm: number | null;
  application: string | null;
  finishing: string | null;
  collection: string | null;
  product_type: string;
  application_type: string | null;
  place_of_application: string | null;
  thickness: number;
  field_confidence?: Record<string, FieldConfidence>;
}

export interface PdfParsedOrder {
  order_number: string;
  client: string;
  client_location: string | null;
  sales_manager_name: string | null;
  factory_id: string;
  document_date: string | null;
  final_deadline: string | null;
  desired_delivery_date: string | null;
  mandatory_qc: boolean;
  notes: string | null;
  items: PdfParsedItem[];
  field_confidence?: Record<string, FieldConfidence>;
}

export interface PdfParseResult {
  parsed_order: PdfParsedOrder;
  confidence: number;
  warnings: string[];
  template_id: string;
  template_name: string;
  template_match_score: number;
  validation_errors: string[];
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
  // Change request management
  listChangeRequests: (params?: { factory_id?: string }) =>
    apiClient.get('/orders/change-requests', { params }).then((r) => r.data),
  approveChange: (id: string) =>
    apiClient.post(`/orders/${id}/approve-change`).then((r) => r.data),
  rejectChange: (id: string) =>
    apiClient.post(`/orders/${id}/reject-change`).then((r) => r.data),
  // PDF upload
  uploadPdf: (file: File, factoryId: string): Promise<PdfParseResult> => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`/orders/upload-pdf?factory_id=${factoryId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data);
  },
  // PDF confirm (reviewed parsed data -> create order)
  confirmPdf: (data: Record<string, unknown>) =>
    apiClient.post('/orders/confirm-pdf', data).then((r) => r.data),
  // Reprocess order (re-run position/task generation)
  reprocessOrder: (orderId: string) =>
    apiClient.post(`/orders/${orderId}/reprocess`).then((r) => r.data),
  // Reschedule order (recalculate dates, assign kilns, reserve materials)
  rescheduleOrder: (orderId: string) =>
    apiClient.post(`/orders/${orderId}/reschedule`).then((r) => r.data),
};
