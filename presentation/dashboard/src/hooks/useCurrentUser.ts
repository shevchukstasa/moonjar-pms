import { useAuthStore } from '@/stores/authStore';
export function useCurrentUser() { return useAuthStore((s) => s.user); }
