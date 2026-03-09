import { create } from 'zustand';

interface FactoryBrief { id: string; name: string; }

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  language?: string;
  is_active?: boolean;
  factories?: FactoryBrief[];
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (user: User) => void;
  logout: () => void;
  updateUser: (data: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  login: (user) => set({ user, isAuthenticated: true }),
  logout: () => set({ user: null, isAuthenticated: false }),
  updateUser: (data) => set((s) => ({ user: s.user ? { ...s.user, ...data } : null })),
}));
