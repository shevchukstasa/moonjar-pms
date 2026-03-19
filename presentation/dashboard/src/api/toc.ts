import apiClient from './client';

export interface TocConstraint {
  id: string;
  factory_id: string;
  constraint_type: string;
  resource_id: string | null;
  resource_name: string | null;
  is_active: boolean;
  notes: string | null;
}

export interface BufferHealth {
  health: 'green' | 'yellow' | 'red';
  hours: number;
  target: number;
  buffered_count: number;
  buffered_sqm: number;
  kiln_id: string;
  kiln_name: string;
}

export const tocApi = {
  listConstraints: (params?: Record<string, unknown>) =>
    apiClient.get('/toc/constraints', { params }).then((r) => r.data),
  updateConstraint: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/toc/constraints/${id}`, data).then((r) => r.data),
  getBufferHealth: (params?: { factory_id?: string }) =>
    apiClient.get<{ items: BufferHealth[] }>('/toc/buffer-health', { params }).then((r) => r.data),
  getBufferZones: (params?: { factory_id?: string }) =>
    apiClient.get('/toc/buffer-zones', { params }).then((r) => r.data),
};
