import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFactories, type Factory } from '@/hooks/useFactories';
import { useUsers } from '@/hooks/useUsers';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { FactoryDialog } from '@/components/admin/FactoryDialog';

export default function AdminPanelPage() {
  const navigate = useNavigate();
  const { data: factoriesData, isLoading: factoriesLoading } = useFactories();
  const { data: usersData, isLoading: usersLoading } = useUsers({ per_page: 1 });
  const [factoryDialogOpen, setFactoryDialogOpen] = useState(false);
  const [editFactory, setEditFactory] = useState<Factory | null>(null);

  const factories = factoriesData?.items || [];
  const totalUsers = usersData?.total ?? 0;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const factoryColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = useMemo(
    () => [
      { key: 'name', header: 'Name' },
      {
        key: 'location',
        header: 'Location',
        render: (f: Factory) => (
          <span className="text-sm">{f.location || <span className="text-gray-400">&mdash;</span>}</span>
        ),
      },
      {
        key: 'timezone',
        header: 'Timezone',
        render: (f: Factory) => (
          <span className="text-sm">{f.timezone || <span className="text-gray-400">&mdash;</span>}</span>
        ),
      },
      {
        key: 'is_active',
        header: 'Status',
        render: (f: Factory) => (
          <Badge
            status={f.is_active ? 'active' : 'inactive'}
            label={f.is_active ? 'Active' : 'Inactive'}
          />
        ),
      },
      {
        key: 'actions',
        header: '',
        render: (f: Factory) => (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setEditFactory(f);
              setFactoryDialogOpen(true);
            }}
          >
            Edit
          </Button>
        ),
      },
    ],
    [],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
        <p className="mt-1 text-sm text-gray-500">System configuration and reference data</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <div className="text-sm text-gray-500">Users</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {usersLoading ? <Spinner className="h-5 w-5" /> : totalUsers}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Factories</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {factoriesLoading ? <Spinner className="h-5 w-5" /> : factories.length}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Active Factories</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {factoriesLoading ? (
              <Spinner className="h-5 w-5" />
            ) : (
              factories.filter((f) => f.is_active).length
            )}
          </div>
        </Card>
      </div>

      {/* Factories Section */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Factories</h2>
          <Button
            size="sm"
            onClick={() => {
              setEditFactory(null);
              setFactoryDialogOpen(true);
            }}
          >
            + Add Factory
          </Button>
        </div>
        {factoriesLoading ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-8 w-8" />
          </div>
        ) : factories.length === 0 ? (
          <div className="py-8 text-center text-gray-400">No factories configured</div>
        ) : (
          <DataTable
            columns={factoryColumns}
            data={factories as unknown as Record<string, unknown>[]}
          />
        )}
      </div>

      {/* Quick Links */}
      <Card title="Quick Links">
        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => navigate('/users')}>
            Manage Users &rarr;
          </Button>
          <Button variant="secondary" onClick={() => navigate('/tablo')}>
            Production Tablo &rarr;
          </Button>
        </div>
      </Card>

      {/* Factory Dialog */}
      <FactoryDialog
        open={factoryDialogOpen}
        onClose={() => {
          setFactoryDialogOpen(false);
          setEditFactory(null);
        }}
        factory={editFactory}
      />
    </div>
  );
}
