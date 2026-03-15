import apiClient from './client';

export interface MaterialListParams {
  page?: number;
  per_page?: number;
  factory_id?: string;
  material_type?: string;
  warehouse_section?: string;
  low_stock?: boolean;
  search?: string;
}

export interface MaterialItem {
  id: string;
  stock_id: string | null;
  name: string;
  factory_id: string | null;
  balance: number;
  min_balance: number;
  min_balance_recommended: number | null;
  min_balance_auto: boolean;
  avg_daily_consumption: number;
  avg_monthly_consumption: number;
  unit: string;
  material_type: string;
  warehouse_section: string | null;
  supplier_id: string | null;
  supplier_name: string | null;
  is_low_stock: boolean;
  deficit?: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface TransactionItem {
  id: string;
  material_id: string;
  factory_id: string | null;
  type: string;
  quantity: number;
  related_order_id: string | null;
  related_position_id: string | null;
  reason: string | null;
  notes: string | null;
  created_by: string | null;
  created_by_name: string | null;
  created_at: string | null;
}

export interface TransactionInput {
  material_id: string;
  factory_id: string;
  type: 'receive' | 'manual_write_off';
  quantity: number;
  reason?: string;
  notes?: string;
}

export interface ConsumptionAdjustmentItem {
  id: string;
  factory_id: string;
  position_id: string;
  position_number: number | null;
  order_number: string | null;
  material_id: string;
  material_name: string | null;
  expected_qty: number;
  actual_qty: number;
  variance_pct: number | null;
  shape: string | null;
  product_type: string | null;
  suggested_coefficient: number | null;
  status: 'pending' | 'approved' | 'rejected';
  approved_by: string | null;
  approved_by_name: string | null;
  approved_at: string | null;
  notes: string | null;
  created_at: string | null;
}

export const materialsApi = {
  list: (params?: MaterialListParams) =>
    apiClient.get('/materials', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/materials/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    apiClient.post('/materials', data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/materials/${id}`, data).then((r) => r.data),
  listTransactions: (materialId: string, params?: { page?: number; per_page?: number }) =>
    apiClient.get(`/materials/${materialId}/transactions`, { params }).then((r) => r.data),
  createTransaction: (data: TransactionInput) =>
    apiClient.post('/materials/transactions', data).then((r) => r.data),
  getLowStock: (params?: { factory_id?: string }) =>
    apiClient.get('/materials/low-stock', { params }).then((r) => r.data),
  createPurchaseRequest: (data: Record<string, unknown>) =>
    apiClient.post('/materials/purchase-requests', data).then((r) => r.data),
  // Consumption adjustments
  listConsumptionAdjustments: (params?: { factory_id?: string; status?: string; page?: number; per_page?: number }) =>
    apiClient.get('/materials/consumption-adjustments', { params }).then((r) => r.data),
  approveAdjustment: (id: string, data?: { notes?: string }) =>
    apiClient.post(`/materials/consumption-adjustments/${id}/approve`, data || {}).then((r) => r.data),
  rejectAdjustment: (id: string, data?: { notes?: string }) =>
    apiClient.post(`/materials/consumption-adjustments/${id}/reject`, data || {}).then((r) => r.data),
};
