import apiClient from './client';

export interface PositionListParams {
  page?: number;
  per_page?: number;
  factory_id?: string;
  order_id?: string;
  status?: string;
  batch_id?: string;
  section?: 'glazing' | 'firing' | 'sorting';
  split_category?: string;   // e.g. 'color_mismatch' to list PM decision queue
}

export interface ColorMismatchResolveRequest {
  refire_qty: number;   // Already glazed → re-fire only (skips re-glazing)
  reglaze_qty: number;  // Needs full re-glaze + re-fire → SENT_TO_GLAZING
  stock_qty: number;    // Acceptable shade → PACKED (enters QC flow)
  notes?: string;
}

export interface SortingSplitRequest {
  good_quantity: number;
  refire_quantity: number;          // Already glazed; bubbles/underfired → back to kiln
  repair_quantity: number;          // Needs re-glazing → SENT_TO_GLAZING
  color_mismatch_quantity: number;  // Wrong color → re-starts from PLANNED
  grinding_quantity: number;
  write_off_quantity: number;
  notes?: string;
}

export interface BlockingSummaryResponse {
  total_blocked: number;
  by_type: Record<string, number>;
  positions: BlockedPositionInfo[];
}

export interface BlockedPositionInfo {
  id: string;
  order_number: string;
  position_label: string;
  color: string;
  size: string;
  collection: string | null;
  quantity: number;
  status: string;
  blocking_reason: string;
  blocking_since: string | null;
  related_tasks: { task_id: string; type: string; status: string; description: string; created_at: string | null }[];
  material_shortages: { name: string; deficit: number; required: number; available: number }[];
  recipe_id: string | null;
  factory_id: string;
}

export interface MaterialReservationResponse {
  position_id: string;
  recipe_name: string | null;
  materials: MaterialReservationItem[];
  has_recipe: boolean;
}

export interface MaterialReservationItem {
  material_id: string;
  name: string;
  type: string;
  required: number;
  reserved: number;
  available: number;
  deficit: number;
  status: 'reserved' | 'force_reserved' | 'partially_reserved' | 'available' | 'insufficient';
}

export interface ForceUnblockResponse {
  position_id: string;
  previous_status: string;
  new_status: string;
  blocking_tasks_closed: number;
  negative_balances: { material_id: string; material_name: string; balance: number; reserved: number; resulting_effective: number }[];
  audit_note: string;
}

export const positionsApi = {
  list: (params?: PositionListParams) =>
    apiClient.get('/positions', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/positions/${id}`).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/positions/${id}`, data).then((r) => r.data),
  changeStatus: (id: string, status: string, notes?: string) =>
    apiClient.post(`/positions/${id}/status`, { status, notes }).then((r) => r.data),
  split: (id: string, data: SortingSplitRequest) =>
    apiClient.post(`/positions/${id}/split`, data).then((r) => r.data),
  stockAvailability: (id: string) =>
    apiClient.get(`/positions/${id}/stock-availability`).then((r) => r.data),
  resolveColorMismatch: (id: string, data: ColorMismatchResolveRequest) =>
    apiClient.post(`/positions/${id}/resolve-color-mismatch`, data).then((r) => r.data),
  allowedTransitions: (id: string) =>
    apiClient.get(`/positions/${id}/allowed-transitions`).then((r) => r.data as { current_status: string; allowed: string[] }),

  // --- Blocking & Reservations ---
  blockingSummary: (factoryId?: string) =>
    apiClient.get<BlockingSummaryResponse>('/positions/blocking-summary', {
      params: factoryId ? { factory_id: factoryId } : {},
    }).then((r) => r.data),
  materialReservations: (id: string) =>
    apiClient.get<MaterialReservationResponse>(`/positions/${id}/material-reservations`).then((r) => r.data),
  forceUnblock: (id: string, notes: string) =>
    apiClient.post<ForceUnblockResponse>(`/positions/${id}/force-unblock`, { notes }).then((r) => r.data),
};
