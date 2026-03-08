import { useState } from 'react';
import { Shield, AlertTriangle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { Pagination } from '@/components/ui/Pagination';
import { useAuditLog, useAuditLogSummary } from '@/hooks/useSecurity';

const actionColors: Record<string, string> = {
  login_success: 'bg-green-100 text-green-800',
  login_failed: 'bg-red-100 text-red-800',
  logout: 'bg-gray-100 text-gray-800',
  role_change: 'bg-yellow-100 text-yellow-800',
  token_refresh: 'bg-blue-100 text-blue-800',
  session_revoke: 'bg-orange-100 text-orange-800',
};

export function AuditLogViewer() {
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState<string>('');

  const { data: summary, isLoading: loadingSummary } = useAuditLogSummary();
  const { data: auditLog, isLoading: loadingLog } = useAuditLog({
    page,
    per_page: 25,
    action: actionFilter || undefined,
  });

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      {loadingSummary ? (
        <Spinner />
      ) : summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card className="p-3">
            <p className="text-xs text-gray-500">Failed Logins (24h)</p>
            <p className="mt-1 text-xl font-bold text-red-600">{summary.failed_logins_24h}</p>
          </Card>
          <Card className="p-3">
            <p className="text-xs text-gray-500">Unique IPs (24h)</p>
            <p className="mt-1 text-xl font-bold text-gray-900">{summary.unique_ips_24h}</p>
          </Card>
          <Card className="p-3">
            <p className="text-xs text-gray-500">Total Events (24h)</p>
            <p className="mt-1 text-xl font-bold text-gray-900">{summary.total_events_24h}</p>
          </Card>
          <Card className="p-3">
            <p className="text-xs text-gray-500">Anomalies</p>
            <p className="mt-1 text-xl font-bold text-orange-600">{summary.anomalies.length}</p>
          </Card>
        </div>
      )}

      {/* Anomalies */}
      {summary?.anomalies && summary.anomalies.length > 0 && (
        <Card className="border-red-200 bg-red-50 p-3">
          <h4 className="flex items-center gap-1.5 text-sm font-semibold text-red-800">
            <AlertTriangle className="h-4 w-4" />
            Anomalies Detected
          </h4>
          <div className="mt-2 space-y-1">
            {summary.anomalies.map((a, i) => (
              <p key={i} className="text-xs text-red-700">
                IP {a.ip_address}: {a.failed_attempts} failed login attempts
              </p>
            ))}
          </div>
        </Card>
      )}

      {/* Filter */}
      <div className="flex items-center gap-2">
        <Shield className="h-4 w-4 text-gray-400" />
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          className="rounded-md border border-gray-300 bg-white px-2 py-1 text-sm"
        >
          <option value="">All Actions</option>
          <option value="login_success">Login Success</option>
          <option value="login_failed">Login Failed</option>
          <option value="logout">Logout</option>
          <option value="role_change">Role Change</option>
          <option value="token_refresh">Token Refresh</option>
          <option value="session_revoke">Session Revoke</option>
          <option value="settings_change">Settings Change</option>
        </select>
      </div>

      {/* Audit Log Table */}
      {loadingLog ? (
        <Spinner />
      ) : auditLog && (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-3 py-2 text-left font-medium text-gray-500">Time</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-500">Action</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-500">Actor</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-500">IP</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-500">Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {auditLog.items.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-gray-500 whitespace-nowrap">
                      {entry.created_at ? new Date(entry.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${actionColors[entry.action] || 'bg-gray-100 text-gray-800'}`}>
                        {entry.action}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-900">{entry.actor_email || '—'}</td>
                    <td className="px-3 py-2 text-gray-500 font-mono text-xs">{entry.ip_address || '—'}</td>
                    <td className="px-3 py-2 text-gray-500">{entry.target_entity || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            totalPages={Math.ceil(auditLog.total / 25)}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
