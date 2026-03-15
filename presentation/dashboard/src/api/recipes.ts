import apiClient from './client';

export interface TemperatureGroupInfo {
  id: string;
  name: string;
  min_temperature: number;
  max_temperature: number;
  description: string | null;
  is_default: boolean;
}

export interface RecipeItem {
  id: string;
  name: string;
  color_collection: string | null;
  description: string | null;
  recipe_type: string;
  color_type: string | null;
  client_name: string | null;
  specific_gravity: number | null;
  consumption_spray_ml_per_sqm: number | null;
  consumption_brush_ml_per_sqm: number | null;
  is_default: boolean;
  glaze_settings: Record<string, unknown>;
  is_active: boolean;
  ingredients_count?: number;
  materials?: RecipeMaterialItem[];
  temperature_groups?: TemperatureGroupInfo[];
  created_at: string;
  updated_at: string;
}

export interface RecipeMaterialItem {
  id: string;
  recipe_id: string;
  material_id: string;
  material_name: string | null;
  material_type: string | null;
  quantity_per_unit: number;
  unit: string;
  notes: string | null;
}

export interface RecipeMaterialBulkItem {
  material_id: string;
  quantity_per_unit: number;
  unit?: string;
  notes?: string;
}

export const recipesApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/recipes', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/recipes/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/recipes', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/recipes/${id}`, data).then((r) => r.data),
  remove: (id: string) =>
    apiClient.delete(`/recipes/${id}`).then((r) => r.data),
  // Materials (ingredients)
  listMaterials: (recipeId: string) =>
    apiClient.get(`/recipes/${recipeId}/materials`).then((r) => r.data),
  bulkUpdateMaterials: (recipeId: string, materials: RecipeMaterialBulkItem[]) =>
    apiClient.put(`/recipes/${recipeId}/materials`, { materials }).then((r) => r.data),
};
