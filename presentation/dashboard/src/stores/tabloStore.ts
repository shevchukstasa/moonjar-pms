import { create } from 'zustand';

interface TabloState {
  activeTab: string;
  delayUnit: 'hours' | 'days';
  filters: Record<string, string>;
  expandedBatches: Set<string>;
  setActiveTab: (tab: string) => void;
  setDelayUnit: (unit: 'hours' | 'days') => void;
  setFilter: (key: string, value: string) => void;
  clearFilters: () => void;
  toggleBatch: (id: string) => void;
}

export const useTabloStore = create<TabloState>((set) => ({
  activeTab: 'glazing',
  delayUnit: 'hours',
  filters: {},
  expandedBatches: new Set(),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setDelayUnit: (unit) => set({ delayUnit: unit }),
  setFilter: (key, value) => set((s) => ({ filters: { ...s.filters, [key]: value } })),
  clearFilters: () => set({ filters: {} }),
  toggleBatch: (id) =>
    set((s) => {
      const next = new Set(s.expandedBatches);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { expandedBatches: next };
    }),
}));
