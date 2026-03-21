import apiClient from './client';

export interface Reconciliation {
  id: string;
  factory_id: string;
  section_id: string | null;
  status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
  started_by: string;
  completed_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface ReconciliationItem {
  id: string;
  material_id: string;
  material_name: string;
  system_quantity: number;
  actual_quantity: number;
  difference: number;
  reason: string | null;
  explanation: string | null;
  adjustment_applied: boolean;
}

export interface ReconciliationItemInput {
  material_id: string;
  expected_qty: number;
  actual_qty: number;
  reason?: string;
  explanation?: string;
}

export const reconciliationsApi = {
  list: (params?: Record<string, string>) =>
    apiClient.get('/reconciliations', { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get(`/reconciliations/${id}`).then((r) => r.data),

  create: (data: { factory_id: string; started_by: string; status?: string; notes?: string }) =>
    apiClient.post('/reconciliations', data).then((r) => r.data),

  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/reconciliations/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/reconciliations/${id}`).then((r) => r.data),

  // Items
  listItems: (reconciliationId: string) =>
    apiClient.get(`/reconciliations/${reconciliationId}/items`).then((r) => r.data),

  addItems: (reconciliationId: string, items: ReconciliationItemInput[]) =>
    apiClient.post(`/reconciliations/${reconciliationId}/items`, items).then((r) => r.data),

  // Complete
  complete: (reconciliationId: string) =>
    apiClient.post(`/reconciliations/${reconciliationId}/complete`).then((r) => r.data),
};
