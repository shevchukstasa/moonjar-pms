import apiClient from './client';

// ── Types ──────────────────────────────────────────────

export interface MaintenanceType {
  id: string;
  name: string;
  description: string | null;
  duration_hours: number | null;
  requires_empty_kiln: boolean;
  requires_cooled_kiln: boolean;
  requires_power_off: boolean;
  default_interval_days: number | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface MaintenanceSchedule {
  id: string;
  resource_id: string;
  kiln_name: string | null;
  maintenance_type: string;
  maintenance_type_id: string | null;
  maintenance_type_details: MaintenanceType | null;
  scheduled_date: string;
  scheduled_time: string | null;
  estimated_duration_hours: number | null;
  status: string;
  notes: string | null;
  completed_at: string | null;
  completed_by_id: string | null;
  created_by: string | null;
  factory_id: string | null;
  factory_name: string | null;
  is_recurring: boolean;
  recurrence_interval_days: number | null;
  requires_empty_kiln: boolean;
  requires_cooled_kiln: boolean;
  requires_power_off: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface MaintenanceTypeInput {
  name: string;
  description?: string;
  duration_hours?: number;
  requires_empty_kiln?: boolean;
  requires_cooled_kiln?: boolean;
  requires_power_off?: boolean;
  default_interval_days?: number | null;
  is_active?: boolean;
}

export interface MaintenanceScheduleInput {
  maintenance_type?: string;
  maintenance_type_id?: string;
  scheduled_date: string;
  scheduled_time?: string;
  estimated_duration_hours?: number;
  notes?: string;
  factory_id?: string;
  is_recurring?: boolean;
  recurrence_interval_days?: number;
}

// ── API client ─────────────────────────────────────────

export const kilnMaintenanceApi = {
  // --- Maintenance Types ---
  listTypes: (): Promise<{ items: MaintenanceType[] }> =>
    apiClient.get('/kiln-maintenance/types').then((r) => r.data),

  createType: (data: MaintenanceTypeInput): Promise<MaintenanceType> =>
    apiClient.post('/kiln-maintenance/types', data).then((r) => r.data),

  updateType: (id: string, data: Partial<MaintenanceTypeInput>): Promise<MaintenanceType> =>
    apiClient.put(`/kiln-maintenance/types/${id}`, data).then((r) => r.data),

  deleteType: (id: string): Promise<void> =>
    apiClient.delete(`/kiln-maintenance/types/${id}`).then(() => undefined),

  // --- Upcoming (factory-wide) ---
  listUpcoming: (params?: { factory_id?: string; days?: number }): Promise<{
    items: MaintenanceSchedule[];
    total: number;
    date_range: { start: string; end: string };
  }> => apiClient.get('/kiln-maintenance/upcoming', { params }).then((r) => r.data),

  // --- All maintenance (history / general list) ---
  listAll: (params?: Record<string, string>): Promise<{
    items: MaintenanceSchedule[];
    total: number;
    page: number;
    per_page: number;
  }> => apiClient.get('/kiln-maintenance', { params }).then((r) => r.data),

  // --- Schedule for specific kiln ---
  scheduleForKiln: (kilnId: string, data: MaintenanceScheduleInput): Promise<MaintenanceSchedule> =>
    apiClient.post(`/kiln-maintenance/kilns/${kilnId}`, data).then((r) => r.data),

  // --- Complete ---
  complete: (kilnId: string, scheduleId: string, notes?: string): Promise<MaintenanceSchedule> =>
    apiClient
      .post(`/kiln-maintenance/kilns/${kilnId}/${scheduleId}/complete`, { notes: notes || undefined })
      .then((r) => r.data),

  // --- Cancel (delete) ---
  cancel: (kilnId: string, scheduleId: string): Promise<void> =>
    apiClient.delete(`/kiln-maintenance/kilns/${kilnId}/${scheduleId}`).then(() => undefined),
};
