import { useState, useMemo } from 'react';
import { useUsers, type UserItem } from '@/hooks/useUsers';
import { DataTable } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { Pagination } from '@/components/ui/Pagination';
import { SearchInput } from '@/components/ui/SearchInput';
import { UserCreateDialog } from '@/components/users/UserCreateDialog';
import { UserEditDialog } from '@/components/users/UserEditDialog';
import { ROLE_OPTIONS } from '@/types/forms';

const STATUS_FILTER = [
  { value: '', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
];

export default function UsersPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [editUser, setEditUser] = useState<UserItem | null>(null);

  const params = useMemo(() => {
    const p: Record<string, unknown> = { page, per_page: 50 };
    if (search) p.search = search;
    if (roleFilter) p.role = roleFilter;
    if (statusFilter === 'active') p.is_active = true;
    if (statusFilter === 'inactive') p.is_active = false;
    return p;
  }, [page, search, roleFilter, statusFilter]);

  const { data, isLoading } = useUsers(params);

  const users = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / 50));

  const roleLabel = (role: string) =>
    ROLE_OPTIONS.find((r) => r.value === role)?.label || role.replace(/_/g, ' ');

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = useMemo(
    () => [
      { key: 'name', header: 'Name' },
      { key: 'email', header: 'Email' },
      {
        key: 'role',
        header: 'Role',
        render: (u: UserItem) => (
          <span className="text-sm font-medium capitalize">{roleLabel(u.role)}</span>
        ),
      },
      {
        key: 'factories',
        header: 'Factories',
        render: (u: UserItem) =>
          u.factories.length === 0 ? (
            <span className="text-gray-400">—</span>
          ) : (
            <span className="text-sm">{u.factories.map((f) => f.name).join(', ')}</span>
          ),
      },
      {
        key: 'is_active',
        header: 'Status',
        render: (u: UserItem) => (
          <Badge
            status={u.is_active ? 'active' : 'inactive'}
            label={u.is_active ? 'Active' : 'Inactive'}
          />
        ),
      },
      {
        key: 'actions',
        header: '',
        render: (u: UserItem) => (
          <Button variant="ghost" size="sm" onClick={() => setEditUser(u)}>
            Edit
          </Button>
        ),
      },
    ],
    [],
  );

  const roleFilterOptions = useMemo(
    () => [{ value: '', label: 'All Roles' }, ...ROLE_OPTIONS],
    [],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          <p className="mt-1 text-sm text-gray-500">
            {total} user{total !== 1 ? 's' : ''} total
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>+ Create User</Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <SearchInput
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder="Search name or email..."
          className="w-56"
        />
        <select
          value={roleFilter}
          onChange={(e) => {
            setRoleFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          {roleFilterOptions.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          {STATUS_FILTER.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : users.length === 0 ? (
        <div className="py-8 text-center text-gray-400">No users found</div>
      ) : (
        <DataTable columns={columns} data={users as unknown as Record<string, unknown>[]} />
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center">
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
      )}

      {/* Dialogs */}
      <UserCreateDialog open={createOpen} onClose={() => setCreateOpen(false)} />
      <UserEditDialog open={!!editUser} onClose={() => setEditUser(null)} user={editUser} />
    </div>
  );
}
