import { create } from 'zustand';

interface TabloState {
  activeTab: string;
  delayUnit: 'hours' | 'days';
  filters: Record<string, string>;
  setActiveTab: (tab: string) => void;
  setDelayUnit: (unit: 'hours' | 'days') => void;
  setFilter: (key: string, value: string) => void;
  clearFilters: () => void;
}

export const useTabloStore = create<TabloState>((set) => ({
  activeTab: 'glazing',
  delayUnit: 'hours',
  filters: {},
  setActiveTab: (tab) => set({ activeTab: tab }),
  setDelayUnit: (unit) => set({ delayUnit: unit }),
  setFilter: (key, value) => set((s) => ({ filters: { ...s.filters, [key]: value } })),
  clearFilters: () => set({ filters: {} }),
}));
