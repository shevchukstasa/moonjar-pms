import apiClient from './client';

// --- Types ---

export interface FinancialSummary {
  period: { from: string; to: string };
  opex_total: number;
  capex_total: number;
  revenue: number;
  margin: number;
  margin_percent: number;
  cost_per_sqm: number;
  output_sqm: number;
  breakdown: { entry_type: string; category: string; total: number }[];
}

export interface FinancialEntry {
  id: string;
  factory_id: string;
  entry_type: string;
  category: string;
  amount: number;
  currency: string;
  description: string | null;
  entry_date: string;
  created_at: string;
}

// --- API Functions ---

export const financialsApi = {
  getSummary: (params?: { factory_id?: string; date_from?: string; date_to?: string }) =>
    apiClient.get<FinancialSummary>('/financials/summary', { params }).then((r) => r.data),

  list: (params?: { factory_id?: string; page?: number; per_page?: number }) =>
    apiClient.get<{ items: FinancialEntry[]; total: number }>('/financials', { params }).then((r) => r.data),

  create: (data: Omit<FinancialEntry, 'id' | 'created_at'>) =>
    apiClient.post<FinancialEntry>('/financials', data).then((r) => r.data),
};
