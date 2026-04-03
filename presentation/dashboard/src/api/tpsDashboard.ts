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

// ── Constants ────────────────────────────────────────────────

export const PRODUCTION_STAGES = [
  { value: 'incoming_inspection', label: 'Incoming Inspection' },
  { value: 'engobe', label: 'Engobe Application' },
  { value: 'engobe_check', label: 'Engobe Check' },
  { value: 'glazing', label: 'Glazing' },
  { value: 'pre_kiln_check', label: 'Pre-Kiln Check' },
  { value: 'kiln_loading', label: 'Kiln Loading' },
  { value: 'firing', label: 'Firing' },
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
