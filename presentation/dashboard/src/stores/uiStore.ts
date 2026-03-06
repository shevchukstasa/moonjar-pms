import { create } from 'zustand';

interface UiState {
  sidebarOpen: boolean;
  activeFactoryId: string | null;
  toggleSidebar: () => void;
  setActiveFactory: (id: string | null) => void;
}

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  activeFactoryId: null,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setActiveFactory: (id) => set({ activeFactoryId: id }),
}));
