import { create } from 'zustand';
import apiClient from '../api/client';

interface FactoryBrief {
  id: string;
  name: string;
}

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  language?: string;
  factories?: FactoryBrief[];
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  selectedFactoryId: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
  setFactory: (id: string) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  loading: false,
  error: null,
  selectedFactoryId: localStorage.getItem('wh_factory_id'),

  login: async (email: string, password: string) => {
    set({ loading: true, error: null });
    try {
      const res = await apiClient.post('/auth/login', { email, password });
      const user = res.data.user ?? res.data;
      set({ user, isAuthenticated: true, loading: false });
      // Auto-select first factory if none selected
      if (!get().selectedFactoryId && user.factories?.length) {
        const fid = user.factories[0].id;
        set({ selectedFactoryId: fid });
        localStorage.setItem('wh_factory_id', fid);
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Login gagal. Periksa email dan kata sandi.';
      set({ loading: false, error: msg });
      throw err;
    }
  },

  logout: () => {
    apiClient.post('/auth/logout').catch(() => {});
    set({ user: null, isAuthenticated: false, error: null });
  },

  checkAuth: async () => {
    try {
      const res = await apiClient.get('/auth/me');
      const user = res.data;
      set({ user, isAuthenticated: true });
      if (!get().selectedFactoryId && user.factories?.length) {
        const fid = user.factories[0].id;
        set({ selectedFactoryId: fid });
        localStorage.setItem('wh_factory_id', fid);
      }
    } catch {
      set({ user: null, isAuthenticated: false });
    }
  },

  setFactory: (id: string) => {
    set({ selectedFactoryId: id });
    localStorage.setItem('wh_factory_id', id);
  },

  clearError: () => set({ error: null }),
}));
