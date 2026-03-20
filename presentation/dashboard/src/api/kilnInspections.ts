import apiClient from './client';

export interface InspectionItem {
  id: string;
  category: string;
  item_text: string;
  sort_order: number;
  is_active: boolean;
  applies_to_kiln_types: string[] | null;
}

export interface InspectionResultInput {
  item_id: string;
  result: string; // ok, not_applicable, damaged, needs_repair
  notes?: string;
}

export interface InspectionResult {
  id: string;
  item_id: string;
  category: string | null;
  item_text: string | null;
  result: string;
  notes: string | null;
}

export interface Inspection {
  id: string;
  resource_id: string;
  resource_name: string | null;
  factory_id: string;
  inspection_date: string;
  inspected_by_id: string;
  inspected_by_name: string | null;
  notes: string | null;
  created_at: string | null;
  results: InspectionResult[];
  summary: { total: number; ok: number; issues: number; not_applicable: number };
}

export interface RepairLog {
  id: string;
  resource_id: string;
  resource_name: string | null;
  factory_id: string;
  date_reported: string | null;
  reported_by_id: string;
  reported_by_name: string | null;
  issue_description: string;
  diagnosis: string | null;
  repair_actions: string | null;
  spare_parts_used: string | null;
  technician: string | null;
  date_completed: string | null;
  status: string;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export const kilnInspectionsApi = {
  // Inspection items (template)
  getItems: () =>
    apiClient.get('/kiln-inspections/items').then((r) => r.data),

  // Inspections CRUD
  listInspections: (params?: Record<string, string>) =>
    apiClient.get('/kiln-inspections', { params }).then((r) => r.data),

  getInspection: (id: string) =>
    apiClient.get(`/kiln-inspections/${id}`).then((r) => r.data),

  createInspection: (data: {
    resource_id: string;
    factory_id: string;
    inspection_date: string;
    results: InspectionResultInput[];
    notes?: string;
  }) => apiClient.post('/kiln-inspections', data).then((r) => r.data),

  // Matrix view
  getMatrix: (params?: Record<string, string>) =>
    apiClient.get('/kiln-inspections/matrix', { params }).then((r) => r.data),

  // Repair logs
  listRepairs: (params?: Record<string, string>) =>
    apiClient.get('/kiln-inspections/repairs', { params }).then((r) => r.data),

  createRepair: (data: Record<string, unknown>) =>
    apiClient.post('/kiln-inspections/repairs', data).then((r) => r.data),

  updateRepair: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/kiln-inspections/repairs/${id}`, data).then((r) => r.data),

  deleteRepair: (id: string) =>
    apiClient.delete(`/kiln-inspections/repairs/${id}`).then((r) => r.data),
};
