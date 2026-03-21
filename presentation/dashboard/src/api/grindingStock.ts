import apiClient from './client';

// ── Types ──────────────────────────────────────────────

export interface GrindingStockItem {
  id: string;
  factory_id: string;
  color: string;
  size: string;
  quantity: number;
  source_order_id: string | null;
  source_position_id: string | null;
  status: string;
  decided_by: string | null;
  decided_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface GrindingStockListResponse {
  items: GrindingStockItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface GrindingStockStats {
  stats: Record<string, Record<string, number>>;
}

export interface GrindingStockDecisionInput {
  decision: 'grinding' | 'pending' | 'sent_to_mana';
  notes?: string;
}

// ── API client ─────────────────────────────────────────

export const grindingStockApi = {
  list: (params?: {
    factory_id?: string;
    status?: string;
    page?: number;
    per_page?: number;
  }): Promise<GrindingStockListResponse> =>
    apiClient.get('/grinding-stock', { params }).then((r) => r.data),

  stats: (): Promise<GrindingStockStats> =>
    apiClient.get('/grinding-stock/stats').then((r) => r.data),

  get: (id: string): Promise<GrindingStockItem> =>
    apiClient.get(`/grinding-stock/${id}`).then((r) => r.data),

  decide: (id: string, data: GrindingStockDecisionInput): Promise<GrindingStockItem> =>
    apiClient.post(`/grinding-stock/${id}/decide`, data).then((r) => r.data),
};
