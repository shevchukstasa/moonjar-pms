import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dashboardAccessApi, type DashboardAccessItem } from '@/api/dashboardAccess';
import { usersApi } from '@/api/users';
import { useAuthStore } from '@/stores/authStore';
import { DataTable } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Spinner } from '@/components/ui/Spinner';
import { Pagination } from '@/components/ui/Pagination';
import { ROLE_OPTIONS } from '@/types/forms';

const DASHBOARD_TYPES = [
  { value: 'owner', label: 'Owner' },
  { value: 'ceo', label: 'CEO' },
  { value: 'manager', label: 'Manager' },
  { value: 'admin', label: 'Admin' },
  { value: 'warehouse', label: 'Warehouse' },
  { value: 'quality', label: 'Quality' },
  { value: 'purchaser', label: 'Purchaser' },
  { value: 'packing', label: 'Packing' },
] as const;

type UserBrief = { id: string; name: string; email: string; role: string };

export default function DashboardAccessPage() {
  const currentUser = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [roleFilter, setRoleFilter] = useState('');
  const [grantOpen, setGrantOpen] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<DashboardAccessItem | null>(null);

  // Grant form state
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedDashboards, setSelectedDashboards] = useState<string[]>([]);

  // Fetch access list
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-access', page],
    queryFn: () => dashboardAccessApi.list({ page, per_page: 50 }),
  });

  // Fetch all users for the grant dialog & for resolving names in the table
  const { data: usersData } = useQuery<{ items: { id: string; name: string; email: string; role: string; is_active: boolean }[]; total: number }>({
    queryKey: ['users', { per_page: 200 }],
    queryFn: () => usersApi.list({ per_page: 200 }),
  });

  const usersMap = useMemo(() => {
    const map: Record<string, UserBrief> = {};
    for (const u of usersData?.items || []) {
      map[u.id] = u;
    }
    return map;
  }, [usersData]);

  const activeUsers = useMemo(
    () => (usersData?.items || []).filter((u) => u.is_active),
    [usersData],
  );

  // Filter items by role
  const items = useMemo(() => {
    const all = data?.items || [];
    if (!roleFilter) return all;
    return all.filter((item) => usersMap[item.user_id]?.role === roleFilter);
  }, [data, roleFilter, usersMap]);

  const total = data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / 50));

  // Mutations
  const createMutation = useMutation({
    mutationFn: (payload: { user_id: string; dashboard_type: string; granted_by: string }) =>
      dashboardAccessApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-access'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => dashboardAccessApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-access'] });
    },
  });

  const handleGrant = async () => {
    if (!selectedUserId || selectedDashboards.length === 0 || !currentUser) return;
    for (const dt of selectedDashboards) {
      await createMutation.mutateAsync({
        user_id: selectedUserId,
        dashboard_type: dt,
        granted_by: currentUser.id,
      });
    }
    setGrantOpen(false);
    setSelectedUserId('');
    setSelectedDashboards([]);
  };

  const toggleDashboard = (val: string) => {
    setSelectedDashboards((prev) =>
      prev.includes(val) ? prev.filter((d) => d !== val) : [...prev, val],
    );
  };

  const roleLabel = (role: string) =>
    ROLE_OPTIONS.find((r) => r.value === role)?.label || role.replace(/_/g, ' ');

  const dashboardLabel = (dt: string) =>
    DASHBOARD_TYPES.find((d) => d.value === dt)?.label || dt;

  // Group grants by user for the "Granted Dashboards" column
  const grantsByUser = useMemo(() => {
    const map: Record<string, DashboardAccessItem[]> = {};
    for (const item of items) {
      if (!map[item.user_id]) map[item.user_id] = [];
      map[item.user_id].push(item);
    }
    return map;
  }, [items]);

  // Deduplicated rows — one per user
  const userRows = useMemo(() => {
    return Object.entries(grantsByUser).map(([userId, grants]) => ({
      userId,
      user: usersMap[userId],
      grants,
    }));
  }, [grantsByUser, usersMap]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    {
      key: 'name',
      header: 'Name',
      render: (row: (typeof userRows)[0]) => (
        <span className="font-medium">{row.user?.name || 'Unknown'}</span>
      ),
    },
    {
      key: 'email',
      header: 'Email',
      render: (row: (typeof userRows)[0]) => (
        <span className="text-gray-600">{row.user?.email || '-'}</span>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      render: (row: (typeof userRows)[0]) => (
        <span className="text-sm font-medium capitalize">
          {row.user ? roleLabel(row.user.role) : '-'}
        </span>
      ),
    },
    {
      key: 'dashboards',
      header: 'Granted Dashboards',
      render: (row: (typeof userRows)[0]) => (
        <div className="flex flex-wrap gap-1">
          {row.grants.map((g) => (
            <span
              key={g.id}
              className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700"
            >
              {dashboardLabel(g.dashboard_type)}
              <button
                onClick={(e) => { e.stopPropagation(); setRevokeTarget(g); }}
                className="ml-0.5 text-blue-400 hover:text-red-500"
                title="Revoke"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      ),
    },
    {
      key: 'granted_by',
      header: 'Granted By',
      render: (row: (typeof userRows)[0]) => {
        const granter = usersMap[row.grants[0]?.granted_by];
        return <span className="text-sm text-gray-600">{granter?.name || '-'}</span>;
      },
    },
    {
      key: 'granted_at',
      header: 'Date',
      render: (row: (typeof userRows)[0]) => {
        const date = row.grants[0]?.granted_at;
        return (
          <span className="text-sm text-gray-500">
            {date ? new Date(date).toLocaleDateString() : '-'}
          </span>
        );
      },
    },
  ];

  if (isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard Access</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage which dashboards each user can see beyond their default role.
          </p>
        </div>
        <Button onClick={() => setGrantOpen(true)}>Grant Access</Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="w-56">
          <Select
            value={roleFilter}
            onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
            options={[{ value: '', label: 'All Roles' }, ...ROLE_OPTIONS.map((r) => ({ value: r.value, label: r.label }))]}
            label="Filter by Role"
          />
        </div>
        <div className="text-sm text-gray-500">
          {items.length} grant{items.length !== 1 ? 's' : ''} across {userRows.length} user{userRows.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Table */}
      {userRows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 py-12 text-center text-gray-500">
          No dashboard access grants found.
        </div>
      ) : (
        <DataTable columns={columns} data={userRows as unknown as Record<string, unknown>[]} />
      )}

      {totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      )}

      {/* Grant Access Dialog */}
      <Dialog open={grantOpen} onClose={() => setGrantOpen(false)} title="Grant Dashboard Access" className="w-[480px]">
        <div className="space-y-4">
          <Select
            label="User"
            value={selectedUserId}
            onChange={(e) => setSelectedUserId(e.target.value)}
            options={[
              { value: '', label: 'Select a user...' },
              ...activeUsers.map((u) => ({
                value: u.id,
                label: `${u.name} (${u.email}) — ${roleLabel(u.role)}`,
              })),
            ]}
          />

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Dashboard Types
            </label>
            <div className="grid grid-cols-2 gap-2">
              {DASHBOARD_TYPES.map((dt) => (
                <label
                  key={dt.value}
                  className="flex cursor-pointer items-center gap-2 rounded-md border border-gray-200 px-3 py-2 text-sm hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    checked={selectedDashboards.includes(dt.value)}
                    onChange={() => toggleDashboard(dt.value)}
                    className="h-4 w-4 rounded border-gray-300 text-primary-500 focus:ring-primary-500"
                  />
                  {dt.label}
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setGrantOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleGrant}
              disabled={!selectedUserId || selectedDashboards.length === 0 || createMutation.isPending}
            >
              {createMutation.isPending ? 'Granting...' : 'Grant Access'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Revoke Confirmation */}
      <ConfirmDialog
        open={!!revokeTarget}
        onClose={() => setRevokeTarget(null)}
        onConfirm={() => {
          if (revokeTarget) deleteMutation.mutate(revokeTarget.id);
          setRevokeTarget(null);
        }}
        title="Revoke Dashboard Access"
        message={
          revokeTarget
            ? `Revoke "${dashboardLabel(revokeTarget.dashboard_type)}" dashboard access from ${usersMap[revokeTarget.user_id]?.name || 'this user'}?`
            : ''
        }
      />
    </div>
  );
}
