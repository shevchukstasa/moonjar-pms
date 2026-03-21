import apiClient from './client';

export interface FinishedGoodsItem {
  id: string;
  factory_id: string;
  factory_name: string | null;
  color: string;
  size: string;
  collection: string | null;
  product_type: string;
  quantity: number;
  reserved_quantity: number;
  available: number;
  updated_at: string | null;
}

export interface FinishedGoodsListParams {
  page?: number;
  per_page?: number;
  factory_id?: string;
  color?: string;
  size?: string;
  collection?: string;
}

export interface FinishedGoodsListResponse {
  items: FinishedGoodsItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface StockUpsertInput {
  factory_id: string;
  color: string;
  size: string;
  collection?: string;
  product_type?: string;
  quantity: number;
  reserved_quantity?: number;
}

export interface StockUpdateInput {
  quantity?: number;
  reserved_quantity?: number;
}

export interface AvailabilityParams {
  color: string;
  size: string;
  needed: number;
  factory_id?: string;
  collection?: string;
}

export interface FactoryAvailability {
  factory_id: string;
  factory_name: string;
  available: number;
  quantity: number;
  reserved: number;
}

export interface AvailabilityResponse {
  needed: number;
  home_factory: FactoryAvailability | null;
  all_factories: FactoryAvailability[];
  total_available: number;
  sufficient_on_home: boolean;
  sufficient_total: boolean;
  best_single_factory: FactoryAvailability | null;
}

export const finishedGoodsApi = {
  list: (params?: FinishedGoodsListParams) =>
    apiClient.get<FinishedGoodsListResponse>('/finished-goods', { params }).then((r) => r.data),

  upsert: (data: StockUpsertInput) =>
    apiClient.post<FinishedGoodsItem>('/finished-goods', data).then((r) => r.data),

  update: (id: string, data: StockUpdateInput) =>
    apiClient.patch<FinishedGoodsItem>(`/finished-goods/${id}`, data).then((r) => r.data),

  checkAvailability: (params: AvailabilityParams) =>
    apiClient.get<AvailabilityResponse>('/finished-goods/availability', { params }).then((r) => r.data),
};
