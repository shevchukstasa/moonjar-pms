import apiClient from './client';

export interface ConsumptionRuleItem {
  id: string;
  rule_number: number;
  name: string;
  description: string | null;
  collection: string | null;
  color_collection: string | null;
  product_type: string | null;
  size_id: string | null;
  size_name: string | null;
  shape: string | null;
  thickness_mm_min: number | null;
  thickness_mm_max: number | null;
  place_of_application: string | null;
  recipe_type: string | null;
  application_method: string | null;
  consumption_ml_per_sqm: number;
  coats: number;
  specific_gravity_override: number | null;
  priority: number;
  is_active: boolean;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ConsumptionRuleInput {
  rule_number: number;
  name: string;
  description?: string | null;
  collection?: string | null;
  color_collection?: string | null;
  product_type?: string | null;
  size_id?: string | null;
  shape?: string | null;
  thickness_mm_min?: number | null;
  thickness_mm_max?: number | null;
  place_of_application?: string | null;
  recipe_type?: string | null;
  application_method?: string | null;
  consumption_ml_per_sqm: number;
  coats?: number;
  specific_gravity_override?: number | null;
  priority?: number;
  is_active?: boolean;
  notes?: string | null;
}

export const consumptionRulesApi = {
  list: (params?: Record<string, string | boolean>) =>
    apiClient.get('/consumption-rules', { params }).then((r) => r.data as ConsumptionRuleItem[]),

  get: (id: string) =>
    apiClient.get(`/consumption-rules/${id}`).then((r) => r.data as ConsumptionRuleItem),

  create: (data: ConsumptionRuleInput) =>
    apiClient.post('/consumption-rules', data).then((r) => r.data as ConsumptionRuleItem),

  update: (id: string, data: Partial<ConsumptionRuleInput>) =>
    apiClient.patch(`/consumption-rules/${id}`, data).then((r) => r.data as ConsumptionRuleItem),

  remove: (id: string) =>
    apiClient.delete(`/consumption-rules/${id}`).then((r) => r.data),
};
