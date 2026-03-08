import apiClient from './client';

// --- Types ---

export interface AuditLogEntry {
  id: string;
  action: string;
  actor_id: string | null;
  actor_email: string | null;
  ip_address: string | null;
  user_agent: string | null;
  target_entity: string | null;
  target_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string | null;
}

export interface AuditLogSummary {
  failed_logins_24h: number;
  unique_ips_24h: number;
  total_events_24h: number;
  anomalies: { ip_address: string; failed_attempts: number }[];
}

export interface ActiveSessionEntry {
  id: string;
  user_id: string;
  ip_address: string | null;
  user_agent: string | null;
  device_label: string | null;
  created_at: string | null;
  expires_at: string | null;
}

// --- API Functions ---

export const securityApi = {
  getAuditLog: (params?: { page?: number; per_page?: number; action?: string; actor_id?: string; date_from?: string; date_to?: string }) =>
    apiClient.get<{ items: AuditLogEntry[]; total: number; page: number; per_page: number }>('/security/audit-log', { params }).then((r) => r.data),

  getAuditLogSummary: () =>
    apiClient.get<AuditLogSummary>('/security/audit-log/summary').then((r) => r.data),

  getSessions: (params?: { page?: number; per_page?: number; user_id?: string }) =>
    apiClient.get<{ items: ActiveSessionEntry[]; total: number }>('/security/sessions', { params }).then((r) => r.data),

  revokeSession: (sessionId: string) =>
    apiClient.delete(`/security/sessions/${sessionId}`).then((r) => r.data),

  revokeAllSessions: () =>
    apiClient.delete('/security/sessions').then((r) => r.data),
};
