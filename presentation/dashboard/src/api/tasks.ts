import apiClient from './client';

export interface TaskListParams {
  page?: number;
  per_page?: number;
  factory_id?: string;
  assigned_to?: string;
  assigned_role?: string;
  status?: string;
  task_type?: string;
}

export interface TaskItem {
  id: string;
  factory_id: string;
  type: string;
  status: string;
  assigned_to: string | null;
  assigned_to_name: string | null;
  assigned_role: string | null;
  related_order_id: string | null;
  related_order_number: string | null;
  related_position_id: string | null;
  blocking: boolean;
  description: string | null;
  priority: number;
  due_at: string | null;
  created_at: string | null;
  metadata_json: Record<string, unknown> | null;
}

export interface ShortageResolutionInput {
  decision: 'manufacture' | 'decline';
  target_factory_id?: string;
  manufacture_quantity?: number;
  notes?: string;
}

export interface SizeResolutionInput {
  size_id?: string;
  create_new_size?: boolean;
  new_size_name?: string;
  new_size_width_mm?: number;
  new_size_height_mm?: number;
  new_size_thickness_mm?: number;
  new_size_shape?: string;
}

export const tasksApi = {
  list: (params?: TaskListParams) =>
    apiClient.get('/tasks', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/tasks/${id}`).then((r) => r.data),
  complete: (id: string) =>
    apiClient.post(`/tasks/${id}/complete`).then((r) => r.data),
  resolveShortage: (id: string, data: ShortageResolutionInput) =>
    apiClient.post(`/tasks/${id}/resolve-shortage`, data).then((r) => r.data),
  resolveSize: (id: string, data: SizeResolutionInput) =>
    apiClient.post(`/tasks/${id}/resolve-size`, data).then((r) => r.data),
};
