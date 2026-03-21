import apiClient from './client';

// ==================== Types ====================

export interface EscalationRule {
  id: string;
  factory_id: string;
  task_type: string;
  pm_timeout_hours: number;
  ceo_timeout_hours: number;
  owner_timeout_hours: number;
  night_level: number;
  is_active: boolean;
}

export interface EscalationRuleInput {
  factory_id: string;
  task_type: string;
  pm_timeout_hours: number;
  ceo_timeout_hours: number;
  owner_timeout_hours: number;
  night_level?: number;
  is_active?: boolean;
}

export interface ReceivingSetting {
  factory_id: string;
  approval_mode: 'all' | 'auto';
}

export interface DefectThreshold {
  id: string;
  material_id: string;
  material_name: string | null;
  max_defect_percent: number;
}

export interface ConsolidationSetting {
  factory_id: string;
  consolidation_window_days: number;
  urgency_threshold_days: number;
  planning_horizon_days: number;
}

export interface ServiceLeadTimeDetail {
  service_type: string;
  lead_time_days: number;
  is_custom: boolean;
}

export interface ServiceLeadTimesResponse {
  factory_id: string;
  lead_times: ServiceLeadTimeDetail[];
}

// ==================== API ====================

export const adminSettingsApi = {
  // --- Escalation Rules ---
  listEscalationRules: (factoryId: string) =>
    apiClient.get<EscalationRule[]>('/admin-settings/escalation-rules', { params: { factory_id: factoryId } }).then((r) => r.data),

  createEscalationRule: (data: EscalationRuleInput) =>
    apiClient.post<EscalationRule>('/admin-settings/escalation-rules', data).then((r) => r.data),

  updateEscalationRule: (id: string, data: Partial<EscalationRuleInput>) =>
    apiClient.patch<EscalationRule>(`/admin-settings/escalation-rules/${id}`, data).then((r) => r.data),

  deleteEscalationRule: (id: string) =>
    apiClient.delete(`/admin-settings/escalation-rules/${id}`).then((r) => r.data),

  // --- Receiving Settings ---
  getReceivingSettings: (factoryId: string) =>
    apiClient.get<ReceivingSetting>('/admin-settings/receiving-settings', { params: { factory_id: factoryId } }).then((r) => r.data),

  updateReceivingSettings: (factoryId: string, data: { approval_mode: string }) =>
    apiClient.put<ReceivingSetting>(`/admin-settings/receiving-settings/${factoryId}`, data).then((r) => r.data),

  // --- Defect Thresholds ---
  listDefectThresholds: (factoryId?: string) =>
    apiClient.get<DefectThreshold[]>('/admin-settings/defect-thresholds', { params: factoryId ? { factory_id: factoryId } : {} }).then((r) => r.data),

  upsertDefectThreshold: (materialId: string, data: { max_defect_percent: number }) =>
    apiClient.put<DefectThreshold>(`/admin-settings/defect-thresholds/${materialId}`, data).then((r) => r.data),

  deleteDefectThreshold: (materialId: string) =>
    apiClient.delete(`/admin-settings/defect-thresholds/${materialId}`).then((r) => r.data),

  // --- Consolidation Settings ---
  getConsolidationSettings: (factoryId: string) =>
    apiClient.get<ConsolidationSetting>('/admin-settings/consolidation-settings', { params: { factory_id: factoryId } }).then((r) => r.data),

  updateConsolidationSettings: (factoryId: string, data: { consolidation_window_days: number; urgency_threshold_days: number; planning_horizon_days: number }) =>
    apiClient.put<ConsolidationSetting>(`/admin-settings/consolidation-settings/${factoryId}`, data).then((r) => r.data),

  // --- Service Lead Times (existing endpoint) ---
  getServiceLeadTimes: (factoryId: string) =>
    apiClient.get<ServiceLeadTimesResponse>('/settings/service-lead-times', { params: { factory_id: factoryId } }).then((r) => r.data),

  updateServiceLeadTimes: (factoryId: string, items: { service_type: string; lead_time_days: number }[]) =>
    apiClient.put<ServiceLeadTimesResponse>(`/settings/service-lead-times/${factoryId}`, items).then((r) => r.data),

  resetServiceLeadTimes: (factoryId: string) =>
    apiClient.post(`/settings/service-lead-times/${factoryId}/reset-defaults`).then((r) => r.data),
};
