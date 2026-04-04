import apiClient from './client';

// ── Types ────────────────────────────────────────────────────

export interface ProcessStepItem {
  id: string;
  name: string;
  factory_id: string;
  stage: string | null;
  sequence: number;
  norm_time_minutes: number | null;
  productivity_rate: number | null;
  productivity_unit: string | null;
  measurement_basis: string | null;
  shift_count: number;
  applicable_collections: string[];
  applicable_methods: string[];
  applicable_product_types: string[];
  auto_calibrate: boolean;
  calibration_ema: number | null;
  last_calibrated_at: string | null;
  is_active: boolean;
  notes: string | null;
  // Computed (from calibration status endpoint)
  actual_rate_7d?: number | null;
  drift_percent?: number | null;
  data_points?: number;
}

export interface CalibrationStatus {
  step_id: string;
  step_name: string;
  stage: string;
  planned_rate: number | null;
  actual_rate_7d: number | null;
  drift_percent: number | null;
  data_points: number;
  auto_calibrate: boolean;
  last_calibrated_at: string | null;
  productivity_unit: string | null;
}

export interface CalibrationSuggestion {
  step_id: string;
  step_name: string;
  stage: string;
  current_rate: number;
  suggested_rate: number;
  ema_value: number;
  drift_percent: number;
  data_points: number;
  auto_calibrate: boolean;
  applied: boolean;
}

export interface CalibrationLogEntry {
  id: string;
  factory_id: string;
  process_step_id: string;
  step_name?: string;
  previous_rate: number;
  new_rate: number;
  ema_value: number | null;
  data_points: number;
  trigger: string;
  approved_by: string | null;
  created_at: string;
}

export interface ProcessStepCreate {
  name: string;
  factory_id: string;
  stage?: string;
  sequence?: number;
  norm_time_minutes?: number;
  productivity_rate?: number;
  productivity_unit?: string;
  measurement_basis?: string;
  shift_count?: number;
  applicable_collections?: string[];
  applicable_methods?: string[];
  applicable_product_types?: string[];
  auto_calibrate?: boolean;
  notes?: string;
}

// ── Stage Speed Types ────────────────────────────────────────

export interface StageSpeedItem {
  id: string;
  typology_id: string;
  factory_id: string;
  stage: string;
  productivity_rate: number;
  rate_unit: string;       // 'pcs' | 'sqm'
  rate_basis: string;      // 'per_person' | 'per_brigade'
  time_unit: string;       // 'min' | 'hour' | 'shift'
  shift_count: number;
  brigade_size: number;
  auto_calibrate: boolean;
  calibration_ema?: number | null;
  last_calibrated_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface StageSpeedCreate {
  typology_id: string;
  factory_id: string;
  stage: string;
  productivity_rate: number;
  rate_unit?: string;
  rate_basis?: string;
  time_unit?: string;
  shift_count?: number;
  brigade_size?: number;
}

export interface StageSpeedMatrix {
  typology_id: string;
  typology_name: string;
  speeds: StageSpeedItem[];
}

// ── Production Line Resources ────────────────────────────────

export interface LineResourceItem {
  id: string;
  factory_id: string;
  resource_type: string;   // 'work_table' | 'drying_rack' | 'glazing_board'
  name: string;
  capacity_sqm: number | null;
  capacity_boards: number | null;
  capacity_pcs: number | null;
  num_units: number;
  notes: string | null;
  is_active: boolean;
}

export interface LineResourceCreate {
  factory_id: string;
  resource_type: string;
  name: string;
  capacity_sqm?: number;
  capacity_boards?: number;
  capacity_pcs?: number;
  num_units?: number;
  notes?: string;
}

// ── Typology Types ───────────────────────────────────────────

export interface KilnCapacityItem {
  kiln_id: string;
  kiln_name: string | null;
  capacity_sqm: number | null;
  capacity_pcs: number | null;
  loading_method: string | null;
  num_levels: number | null;
  ai_adjusted_sqm: number | null;
  ref_size: string | null;
}

export interface TypologyItem {
  id: string;
  factory_id: string;
  name: string;
  product_types: string[];
  place_of_application: string[];
  collections: string[];
  methods: string[];
  min_size_cm: number | null;
  max_size_cm: number | null;
  max_short_side_cm: number | null;
  preferred_loading: string;
  min_firing_temp: number | null;
  max_firing_temp: number | null;
  shift_count: number;
  auto_calibrate: boolean;
  is_active: boolean;
  priority: number;
  notes: string | null;
  capacities?: KilnCapacityItem[];
}

export interface TypologyCreate {
  name: string;
  factory_id: string;
  product_types?: string[];
  place_of_application?: string[];
  collections?: string[];
  methods?: string[];
  min_size_cm?: number;
  max_size_cm?: number;
  max_short_side_cm?: number;
  preferred_loading?: string;
  min_firing_temp?: number;
  max_firing_temp?: number;
  shift_count?: number;
  auto_calibrate?: boolean;
  priority?: number;
  notes?: string;
}

// ── API functions ────────────────────────────────────────────

export const tpsDashboardApi = {
  // Process Steps CRUD
  listSteps: async (factoryId: string, filters?: {
    collection?: string;
    method?: string;
    product_type?: string;
    stage?: string;
  }): Promise<{ items: ProcessStepItem[]; total: number }> => {
    const params = new URLSearchParams({ factory_id: factoryId });
    if (filters?.collection) params.set('collection', filters.collection);
    if (filters?.method) params.set('method', filters.method);
    if (filters?.product_type) params.set('product_type', filters.product_type);
    if (filters?.stage) params.set('stage', filters.stage);
    const { data } = await apiClient.get(`/tps/process-steps?${params}`);
    return data;
  },

  getPipeline: async (factoryId: string, filters?: {
    collection?: string;
    method?: string;
    product_type?: string;
  }): Promise<{ items: ProcessStepItem[] }> => {
    const params = new URLSearchParams({ factory_id: factoryId });
    if (filters?.collection) params.set('collection', filters.collection);
    if (filters?.method) params.set('method', filters.method);
    if (filters?.product_type) params.set('product_type', filters.product_type);
    const { data } = await apiClient.get(`/tps/process-steps/pipeline?${params}`);
    return data;
  },

  createStep: async (payload: ProcessStepCreate): Promise<ProcessStepItem> => {
    const { data } = await apiClient.post('/tps/process-steps', payload);
    return data;
  },

  updateStep: async (stepId: string, payload: Partial<ProcessStepCreate>): Promise<ProcessStepItem> => {
    const { data } = await apiClient.patch(`/tps/process-steps/${stepId}`, payload);
    return data;
  },

  deleteStep: async (stepId: string): Promise<void> => {
    await apiClient.delete(`/tps/process-steps/${stepId}`);
  },

  reorderSteps: async (stepIds: string[]): Promise<void> => {
    await apiClient.patch('/tps/process-steps/reorder', { step_ids: stepIds });
  },

  // Calibration
  getCalibrationStatus: async (factoryId: string): Promise<CalibrationStatus[]> => {
    const { data } = await apiClient.get(`/tps/calibration/status?factory_id=${factoryId}`);
    return data;
  },

  runCalibration: async (factoryId: string): Promise<CalibrationSuggestion[]> => {
    const { data } = await apiClient.post('/tps/calibration/run', { factory_id: factoryId });
    return data;
  },

  applyCalibration: async (stepId: string, newRate: number): Promise<void> => {
    await apiClient.post('/tps/calibration/apply', { step_id: stepId, new_rate: newRate });
  },

  getCalibrationLog: async (factoryId: string, stepId?: string): Promise<{ items: CalibrationLogEntry[] }> => {
    const params = new URLSearchParams({ factory_id: factoryId });
    if (stepId) params.set('process_step_id', stepId);
    const { data } = await apiClient.get(`/tps/calibration/log?${params}`);
    return data;
  },

  // Typologies
  listTypologies: async (factoryId: string): Promise<{ items: TypologyItem[] }> => {
    const { data } = await apiClient.get(`/tps/typologies?factory_id=${factoryId}`);
    return data;
  },

  createTypology: async (payload: TypologyCreate): Promise<TypologyItem> => {
    const { data } = await apiClient.post('/tps/typologies', payload);
    return data;
  },

  updateTypology: async (id: string, payload: Partial<TypologyCreate>): Promise<TypologyItem> => {
    const { data } = await apiClient.patch(`/tps/typologies/${id}`, payload);
    return data;
  },

  deleteTypology: async (id: string): Promise<void> => {
    await apiClient.delete(`/tps/typologies/${id}`);
  },

  calculateTypology: async (id: string): Promise<{ results: unknown[] }> => {
    const { data } = await apiClient.post(`/tps/typologies/${id}/calculate`);
    return data;
  },

  calculateAllTypologies: async (factoryId: string): Promise<{ results: unknown[] }> => {
    const { data } = await apiClient.post('/tps/typologies/calculate-all', { factory_id: factoryId });
    return data;
  },
};

// ── Stage Typology Speeds API ─────────────────────────────────

export const stageSpeedsApi = {
  list: async (params?: { typology_id?: string; factory_id?: string; stage?: string }): Promise<{ items: StageSpeedItem[] }> => {
    const { data } = await apiClient.get('/tps/stage-speeds', { params });
    return data;
  },

  matrix: async (factoryId?: string): Promise<{ items: StageSpeedMatrix[] }> => {
    const { data } = await apiClient.get('/tps/stage-speeds/matrix', { params: { factory_id: factoryId } });
    return data;
  },

  create: async (payload: StageSpeedCreate): Promise<StageSpeedItem> => {
    const { data } = await apiClient.post('/tps/stage-speeds', payload);
    return data;
  },

  update: async (id: string, payload: Partial<StageSpeedCreate>): Promise<StageSpeedItem> => {
    const { data } = await apiClient.patch(`/tps/stage-speeds/${id}`, payload);
    return data;
  },

  remove: async (id: string): Promise<void> => {
    await apiClient.delete(`/tps/stage-speeds/${id}`);
  },
};

// ── Production Line Resources API ────────────────────────────

export const lineResourcesApi = {
  list: async (factoryId: string, resourceType?: string): Promise<{ items: LineResourceItem[] }> => {
    const params: Record<string, string> = { factory_id: factoryId };
    if (resourceType) params.resource_type = resourceType;
    const { data } = await apiClient.get('/tps/line-resources', { params });
    return data;
  },

  create: async (payload: LineResourceCreate): Promise<{ id: string }> => {
    const { data } = await apiClient.post('/tps/line-resources', payload);
    return data;
  },

  update: async (id: string, payload: Partial<LineResourceCreate>): Promise<void> => {
    await apiClient.patch(`/tps/line-resources/${id}`, payload);
  },

  remove: async (id: string): Promise<void> => {
    await apiClient.delete(`/tps/line-resources/${id}`);
  },
};

// ── Constants ────────────────────────────────────────────────

export const PRODUCTION_STAGES = [
  { value: 'unpacking_sorting', label: 'Unpacking & Sorting onto Boards' },
  { value: 'engobe', label: 'Engobe Application' },
  { value: 'drying_engobe', label: 'Drying (after Engobe)' },
  { value: 'glazing', label: 'Glazing' },
  { value: 'drying_glaze', label: 'Drying (after Glaze)' },
  { value: 'edge_cleaning_loading', label: 'Edge Cleaning + Kiln Loading' },
  { value: 'firing', label: 'Firing' },
  { value: 'kiln_cooling_initial', label: 'Kiln Cooling (for unloading)' },
  { value: 'kiln_unloading', label: 'Kiln Unloading' },
  { value: 'kiln_cooling_full', label: 'Kiln Cooling (for next load)' },
  { value: 'tile_cooling', label: 'Tile Cooling (before Sorting)' },
  { value: 'sorting', label: 'Sorting' },
  { value: 'packing', label: 'Packing' },
  { value: 'quality_check', label: 'Quality Check' },
];

export const PRODUCTIVITY_UNITS = [
  { value: 'sqm/hour', label: 'm\u00b2/hour' },
  { value: 'pcs/hour', label: 'pcs/hour' },
  { value: 'liters/hour', label: 'liters/hour' },
  { value: 'sqm/shift', label: 'm\u00b2/shift' },
  { value: 'pcs/shift', label: 'pcs/shift' },
  { value: 'sqm/min', label: 'm\u00b2/min' },
  { value: 'pcs/min', label: 'pcs/min' },
];

export const RATE_UNITS = [
  { value: 'pcs', label: 'pcs' },
  { value: 'sqm', label: 'm\u00b2' },
];

export const RATE_BASIS = [
  { value: 'per_person', label: '/ person' },
  { value: 'per_brigade', label: '/ brigade' },
  { value: 'fixed_duration', label: 'fixed duration' },
];

export const TIME_UNITS = [
  { value: 'min', label: '/ min' },
  { value: 'hour', label: '/ hour' },
  { value: 'shift', label: '/ shift' },
];

export const COLLECTIONS = [
  { value: 'authentic', label: 'Authentic' },
  { value: 'creative', label: 'Creative' },
  { value: 'silk_screen', label: 'Silk Screen' },
  { value: 'stencil', label: 'Stencil' },
  { value: 'gold', label: 'Gold' },
  { value: 'raku', label: 'Raku' },
  { value: 'exclusive', label: 'Exclusive' },
  { value: 'top_table', label: 'Top Table' },
  { value: 'wash_basin', label: 'Wash Basin' },
];

export const APPLICATION_METHODS = [
  { value: 'ss', label: 'SS (Spray+Spray)' },
  { value: 's', label: 'S (Spray only)' },
  { value: 'bs', label: 'BS (Brush+Spray)' },
  { value: 'sb', label: 'SB (Spray+Brush)' },
  { value: 'splashing', label: 'Splashing' },
  { value: 'stencil', label: 'Stencil' },
  { value: 'silk_screen', label: 'Silk Screen' },
  { value: 'gold', label: 'Gold' },
  { value: 'raku', label: 'Raku' },
];

export const PLACE_OF_APPLICATION = [
  { value: 'face_only', label: 'Face Only' },
  { value: 'edges_1', label: 'Face + 1 Edge' },
  { value: 'edges_2', label: 'Face + 2 Edges' },
  { value: 'all_edges', label: 'All Edges' },
  { value: 'with_back', label: 'All Surfaces' },
];

export const PRODUCT_TYPES = [
  { value: 'tile', label: 'Tile' },
  { value: 'countertop', label: 'Countertop' },
  { value: 'sink', label: 'Sink' },
  { value: '_3d', label: '3D Product' },
];

export const LOADING_METHODS = [
  { value: 'auto', label: 'Auto (optimal)' },
  { value: 'flat', label: 'Flat (face up)' },
  { value: 'edge', label: 'Edge (standing)' },
];

export const LINE_RESOURCE_TYPES = [
  { value: 'work_table', label: 'Work Table', icon: '🪵', capacityLabel: 'Area (m\u00b2) / Boards' },
  { value: 'drying_rack', label: 'Drying Rack / Shelving', icon: '📐', capacityLabel: 'Area (m\u00b2) / Boards' },
  { value: 'glazing_board', label: 'Glazing Board', icon: '📋', capacityLabel: 'Total boards' },
];

// ── Kiln Shelves ────────────────────────────────────────────

export interface KilnShelfItem {
  id: string;
  resource_id: string;
  factory_id: string;
  name: string;
  length_cm: number;
  width_cm: number;
  thickness_mm: number;
  area_sqm: number;
  material: string;
  status: string;
  condition_notes: string | null;
  write_off_reason: string | null;
  write_off_photo_url: string | null;
  written_off_at: string | null;
  purchase_date: string | null;
  purchase_cost: number | null;
  firing_cycles_count: number;
  max_firing_cycles: number | null;
  is_active: boolean;
}

export interface KilnShelfCreate {
  resource_id: string;
  factory_id: string;
  name: string;
  length_cm: number;
  width_cm: number;
  thickness_mm?: number;
  material?: string;
  purchase_date?: string;
  purchase_cost?: number;
  max_firing_cycles?: number;
  condition_notes?: string;
}

export const kilnShelvesApi = {
  list: async (factoryId: string, resourceId?: string, includeWrittenOff = false): Promise<{ items: KilnShelfItem[] }> => {
    const params: Record<string, string> = { factory_id: factoryId };
    if (resourceId) params.resource_id = resourceId;
    if (includeWrittenOff) params.include_written_off = 'true';
    const { data } = await apiClient.get('/tps/kiln-shelves', { params });
    return data;
  },

  create: async (payload: KilnShelfCreate): Promise<{ id: string }> => {
    const { data } = await apiClient.post('/tps/kiln-shelves', payload);
    return data;
  },

  update: async (id: string, payload: Partial<KilnShelfCreate>): Promise<void> => {
    await apiClient.patch(`/tps/kiln-shelves/${id}`, payload);
  },

  writeOff: async (id: string, reason: string, photoUrl?: string): Promise<{ remaining_shelves: number }> => {
    const { data } = await apiClient.post(`/tps/kiln-shelves/${id}/write-off`, {
      reason, photo_url: photoUrl,
    });
    return data;
  },

  incrementCycles: async (id: string, count = 1): Promise<{ firing_cycles_count: number; warning: string | null }> => {
    const { data } = await apiClient.post(`/tps/kiln-shelves/${id}/increment-cycles`, null, {
      params: { count },
    });
    return data;
  },
};

export const SHELF_MATERIALS = [
  { value: 'silicon_carbide', label: 'Silicon Carbide (SiC)' },
  { value: 'cordierite', label: 'Cordierite' },
  { value: 'mullite', label: 'Mullite' },
  { value: 'alumina', label: 'Alumina' },
  { value: 'other', label: 'Other' },
];
