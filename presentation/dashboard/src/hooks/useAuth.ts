import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import apiClient from '@/api/client';
import { roleRoutes } from '@/lib/roleRoutes';

export function useAuth() {
  const { user, isAuthenticated, login, logout } = useAuthStore();
  const navigate = useNavigate();
  const signOut = async () => { try { await apiClient.post('/auth/logout'); } catch {} logout(); navigate('/login'); };
  return { user, isAuthenticated, login, signOut, defaultRoute: user ? roleRoutes[user.role] : '/login' };
}
