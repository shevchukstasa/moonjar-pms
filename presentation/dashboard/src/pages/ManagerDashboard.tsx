import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOrders } from '@/hooks/useOrders';
import { usePositions } from '@/hooks/usePositions';
import { useUiStore } from '@/stores/uiStore';
import { useDebounce } from '@/hooks/useDebounce';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Tabs } from '@/components/ui/Tabs';
import { Pagination } from '@/components/ui/Pagination';
import { SearchInput } from '@/components/ui/SearchInput';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { DataTable } from '@/components/ui/Table';
import { FactorySelector } from '@/components/layout/FactorySelector';
import { OrderCreateDialog } from '@/components/orders/OrderCreateDialog';
import type { OrderListParams } from '@/api/orders';

const ORDER_STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New' },
  { value: 'in_production', label: 'In Production' },
  { value: 'partially_ready', label: 'Partially Ready' },
  { value: 'ready_for_shipment', label: 'Ready for Shipment' },
  { value: 'cancelled', label: 'Cancelled' },
];

export default function ManagerDashboard() {
  const navigate = useNavigate();
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);

  const [orderTab, setOrderTab] = useState<'current' | 'archive'>('current');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const debouncedSearch = useDebounce(search, 400);

  const ordersParams = useMemo<OrderListParams>(() => {
    const p: OrderListParams = { page, per_page: 20, tab: orderTab };
    if (activeFactoryId) p.factory_id = activeFactoryId;
    if (debouncedSearch) p.search = debouncedSearch;
    if (statusFilter) p.status = statusFilter;
    return p;
  }, [page, orderTab, activeFactoryId, debouncedSearch, statusFilter]);

  const { data: ordersData, isLoading: ordersLoading } = useOrders(ordersParams);
  const { data: positionsData } = usePositions(
    activeFactoryId ? { factory_id: activeFactoryId } : undefined,
  );

  const orders = ordersData?.items || [];
  const totalOrders = ordersData?.total || 0;
  const totalPages = Math.ceil(totalOrders / 20) || 1;
  const positionsTotal = positionsData?.total || 0;

  const activeOrders = orders.filter(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (o: any) => o.status !== 'cancelled' && o.status !== 'ready_for_shipment',
  ).length;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const orderColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    { key: 'order_number', header: 'Order #' },
    { key: 'client', header: 'Client' },
    {
      key: 'final_deadline',
      header: 'Deadline',
      render: (item) => item.final_deadline ? new Date(item.final_deadline).toLocaleDateString() : '\u2014',
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <Badge status={item.status} />,
    },
    {
      key: 'positions',
      header: 'Positions',
      render: (item) => (
        <span className="text-sm">
          <span className="font-medium text-green-600">{item.positions_ready || 0}</span>
          <span className="text-gray-400"> / </span>
          <span>{item.positions_count || 0}</span>
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Production Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">Manage orders, positions, and production schedule</p>
        </div>
        <FactorySelector />
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <div className="text-sm text-gray-500">Active Orders</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{orderTab === 'current' ? activeOrders : '\u2014'}</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Total Positions</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{positionsTotal}</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Orders in List</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{totalOrders}</div>
        </Card>
      </div>

      {/* Sub-tabs */}
      <Tabs
        tabs={[
          { id: 'current', label: 'Current Orders' },
          { id: 'archive', label: 'Archive' },
        ]}
        activeTab={orderTab}
        onChange={(id) => { setOrderTab(id as 'current' | 'archive'); setPage(1); }}
      />

      {/* Filters */}
      <div className="flex items-center gap-3">
        <SearchInput
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search orders..."
          className="w-64"
        />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          {ORDER_STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <div className="flex-1" />
        <Button onClick={() => setCreateOpen(true)}>+ Create Order</Button>
        <Button variant="secondary" onClick={() => navigate('/tablo')}>
          Tablo
        </Button>
      </div>

      {/* Orders Table */}
      {ordersLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : orders.length === 0 ? (
        <EmptyState title="No orders found" description={search ? 'Try a different search term' : 'Create your first order'} />
      ) : (
        <>
          <DataTable
            columns={orderColumns}
            data={orders}
            onRowClick={(item) => navigate(`/manager/orders/${item.id}`)}
          />
          <div className="flex justify-center">
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </div>
        </>
      )}

      <OrderCreateDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
