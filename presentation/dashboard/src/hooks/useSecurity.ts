import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { securityApi } from '@/api/security';

export function useAuditLog(params?: { page?: number; per_page?: number; action?: string; actor_id?: string }) {
  return useQuery({
    queryKey: ['audit-log', params],
    queryFn: () => securityApi.getAuditLog(params),
  });
}

export function useAuditLogSummary() {
  return useQuery({
    queryKey: ['audit-log-summary'],
    queryFn: () => securityApi.getAuditLogSummary(),
    staleTime: 30_000,
  });
}

export function useActiveSessions(params?: { page?: number; per_page?: number; user_id?: string }) {
  return useQuery({
    queryKey: ['active-sessions', params],
    queryFn: () => securityApi.getSessions(params),
  });
}

export function useRevokeSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => securityApi.revokeSession(sessionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['active-sessions'] }),
  });
}

export function useRevokeAllSessions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => securityApi.revokeAllSessions(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['active-sessions'] }),
  });
}
