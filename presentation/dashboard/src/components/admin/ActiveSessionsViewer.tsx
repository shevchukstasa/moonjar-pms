import { useState } from 'react';
import { Monitor, Trash2, LogOut } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { useActiveSessions, useRevokeSession, useRevokeAllSessions } from '@/hooks/useSecurity';

export function ActiveSessionsViewer() {
  const [page] = useState(1);
  const { data, isLoading } = useActiveSessions({ page, per_page: 50 });
  const revokeSession = useRevokeSession();
  const revokeAll = useRevokeAllSessions();

  if (isLoading) {
    return <Spinner />;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Monitor className="h-4 w-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-700">
            {data?.total ?? 0} active sessions
          </span>
        </div>
        <button
          onClick={() => revokeAll.mutate()}
          disabled={revokeAll.isPending}
          className="inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
        >
          <LogOut className="h-3.5 w-3.5" />
          Revoke All Others
        </button>
      </div>

      {data && data.items.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-3 py-2 text-left font-medium text-gray-500">Device</th>
                <th className="px-3 py-2 text-left font-medium text-gray-500">IP Address</th>
                <th className="px-3 py-2 text-left font-medium text-gray-500">Created</th>
                <th className="px-3 py-2 text-left font-medium text-gray-500">Expires</th>
                <th className="px-3 py-2 text-right font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.items.map((session) => {
                const isCurrentLikely = data.items.indexOf(session) === data.items.length - 1;
                return (
                  <tr key={session.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1.5">
                        <Monitor className="h-3.5 w-3.5 text-gray-400" />
                        <span className="text-gray-900">
                          {session.device_label || (session.user_agent ? session.user_agent.slice(0, 40) + '...' : 'Unknown device')}
                        </span>
                        {isCurrentLikely && (
                          <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700">Current</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-gray-500">{session.ip_address || '—'}</td>
                    <td className="px-3 py-2 text-gray-500">
                      {session.created_at ? new Date(session.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-3 py-2 text-gray-500">
                      {session.expires_at ? new Date(session.expires_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => revokeSession.mutate(session.id)}
                        disabled={revokeSession.isPending}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                      >
                        <Trash2 className="h-3 w-3" />
                        Revoke
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <Card className="py-8 text-center text-sm text-gray-500">
          No active sessions
        </Card>
      )}
    </div>
  );
}
