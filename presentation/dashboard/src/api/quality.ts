import apiClient from './client';

export interface InspectionItem {
  id: string;
  position_id: string | null;
  factory_id: string;
  stage: string;
  result: string;
  defect_cause_id: string | null;
  defect_cause: { id: string; code: string; description: string } | null;
  notes: string | null;
  checked_by: string | null;
  checked_by_name: string | null;
  created_at: string | null;
  order_number?: string;
  color?: string;
  size?: string;
  quantity?: number;
  position_status?: string;
}

export interface QcPositionItem {
  id: string;
  order_id: string;
  order_number: string | null;
  factory_id: string;
  status: string;
  color: string;
  size: string;
  quantity: number;
  product_type: string;
}

export interface QualityStats {
  pending_qc: number;
  blocked: number;
  open_problem_cards: number;
  inspections_today: number;
}

export interface InspectionInput {
  position_id: string;
  factory_id: string;
  stage?: string;
  result: 'ok' | 'defect';
  defect_cause_id?: string;
  notes?: string;
}

export interface ChecklistItem {
  id: string;
  position_id: string;
  factory_id: string;
  check_type: 'pre_kiln' | 'final';
  checklist_results: Record<string, 'pass' | 'fail' | 'na'>;
  overall_result: 'pass' | 'fail' | 'needs_rework';
  checked_by: string | null;
  checked_by_name: string | null;
  notes: string | null;
  created_at: string | null;
  order_number?: string;
  color?: string;
  size?: string;
  quantity?: number;
  position_status?: string;
}

export interface ChecklistInput {
  position_id: string;
  factory_id: string;
  checklist_results: Record<string, 'pass' | 'fail' | 'na'>;
  overall_result: string;
  notes?: string;
}

export interface ChecklistItemsDef {
  check_type: string;
  items: Record<string, string>;
}

export const qualityApi = {
  listInspections: (params?: Record<string, unknown>) =>
    apiClient.get('/quality/inspections', { params }).then((r) => r.data),
  createInspection: (data: InspectionInput) =>
    apiClient.post('/quality/inspections', data).then((r) => r.data),
  updateInspection: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/quality/inspections/${id}`, data).then((r) => r.data),
  getPositionsForQc: (params?: { factory_id?: string }) =>
    apiClient.get('/quality/positions-for-qc', { params }).then((r) => r.data),
  getStats: (params?: { factory_id?: string }) =>
    apiClient.get('/quality/stats', { params }).then((r) => r.data),

  // Structured checklists
  getChecklistItems: (checkType: 'pre_kiln' | 'final') =>
    apiClient.get<ChecklistItemsDef>('/quality/checklist-items', { params: { check_type: checkType } }).then((r) => r.data),

  createPreKilnCheck: (data: ChecklistInput) =>
    apiClient.post<ChecklistItem>('/quality/pre-kiln-check', data).then((r) => r.data),
  listPreKilnChecks: (params?: { position_id?: string; factory_id?: string }) =>
    apiClient.get('/quality/pre-kiln-checks', { params }).then((r) => r.data),

  createFinalCheck: (data: ChecklistInput) =>
    apiClient.post<ChecklistItem>('/quality/final-check', data).then((r) => r.data),
  listFinalChecks: (params?: { position_id?: string; factory_id?: string }) =>
    apiClient.get('/quality/final-checks', { params }).then((r) => r.data),
};
