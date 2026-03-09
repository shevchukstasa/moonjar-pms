import { useState, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useOrders } from '@/hooks/useOrders';
import { usePositions } from '@/hooks/usePositions';
import { useShortageTasksForManager, useTasks } from '@/hooks/useTasks';
import { useLowStock } from '@/hooks/useMaterials';
import { usePurchaseRequests } from '@/hooks/usePurchaseRequests';
import { useKilns } from '@/hooks/useKilns';
import { useQualityStats, useInspections } from '@/hooks/useQuality';
import { useProblemCards } from '@/hooks/useProblemCards';
import { useBufferHealth, useDashboardSummary } from '@/hooks/useAnalytics';
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
import { ProgressBar } from '@/components/ui/ProgressBar';
import { FactorySelector } from '@/components/layout/FactorySelector';
import { OrderCreateDialog } from '@/components/orders/OrderCreateDialog';
import { tpsApi } from '@/api/tps';
import { tocApi } from '@/api/toc';
import { defectsApi } from '@/api/defects';
import { ai_chatApi } from '@/api/ai_chat';
import type { OrderListParams } from '@/api/orders';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

type DashboardTab = 'orders' | 'tasks' | 'materials' | 'defects' | 'tps' | 'toc' | 'kilns' | 'ai_chat';

const DASHBOARD_TABS: { id: DashboardTab; label: string }[] = [
  { id: 'orders', label: 'Orders' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'materials', label: 'Materials' },
  { id: 'defects', label: 'Defects' },
  { id: 'tps', label: 'TPS' },
  { id: 'toc', label: 'TOC' },
  { id: 'kilns', label: 'Kilns' },
  { id: 'ai_chat', label: 'AI Chat' },
];

const ORDER_STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New' },
  { value: 'in_production', label: 'In Production' },
  { value: 'partially_ready', label: 'Partially Ready' },
  { value: 'ready_for_shipment', label: 'Ready for Shipment' },
  { value: 'cancelled', label: 'Cancelled' },
];

const TASK_STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  cancelled: 'bg-gray-100 text-gray-600',
};

const KILN_STATUS_COLORS: Record<string, string> = {
  idle: 'bg-gray-100 text-gray-700',
  loading: 'bg-blue-100 text-blue-700',
  firing: 'bg-orange-100 text-orange-700',
  cooling: 'bg-cyan-100 text-cyan-700',
  unloading: 'bg-yellow-100 text-yellow-700',
  maintenance: 'bg-red-100 text-red-700',
};

const BUFFER_HEALTH_COLORS: Record<string, string> = {
  green: 'bg-green-500',
  yellow: 'bg-yellow-400',
  red: 'bg-red-500',
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ManagerDashboard() {
  const navigate = useNavigate();
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);

  // --- Top-level tab ---
  const [activeTab, setActiveTab] = useState<DashboardTab>('orders');

  // --- Orders tab state ---
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
  const { data: shortageTasksData } = useShortageTasksForManager(activeFactoryId || undefined);

  const orders = ordersData?.items || [];
  const totalOrders = ordersData?.total || 0;
  const totalPages = Math.ceil(totalOrders / 20) || 1;
  const positionsTotal = positionsData?.total || 0;

  const activeOrders = orders.filter(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (o: any) => o.status !== 'cancelled' && o.status !== 'ready_for_shipment',
  ).length;

  // --- Dashboard-wide KPI ---
  const factoryParams = useMemo(
    () => (activeFactoryId ? { factory_id: activeFactoryId } : undefined),
    [activeFactoryId],
  );
  const { data: dashboardSummary } = useDashboardSummary(factoryParams);

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

      {/* KPI Cards — dashboard-wide, shown above all tabs */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Card>
          <div className="text-xs text-gray-500">Active Orders</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{orderTab === 'current' ? activeOrders : '\u2014'}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Total Positions</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{positionsTotal}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">On-Time Rate</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {dashboardSummary?.on_time_rate != null ? `${Math.round(dashboardSummary.on_time_rate)}%` : '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Defect Rate</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {dashboardSummary?.defect_rate != null ? `${dashboardSummary.defect_rate.toFixed(1)}%` : '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Kiln Utilization</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {dashboardSummary?.kiln_utilization != null ? `${Math.round(dashboardSummary.kiln_utilization)}%` : '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">OEE</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {dashboardSummary?.oee != null ? `${Math.round(dashboardSummary.oee)}%` : '\u2014'}
          </div>
        </Card>
      </div>

      {/* Main Dashboard Tabs */}
      <Tabs
        tabs={DASHBOARD_TABS}
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id as DashboardTab)}
      />

      {/* Tab Content */}
      {activeTab === 'orders' && (
        <OrdersTabContent
          orderTab={orderTab}
          setOrderTab={setOrderTab}
          page={page}
          setPage={setPage}
          search={search}
          setSearch={setSearch}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          createOpen={createOpen}
          setCreateOpen={setCreateOpen}
          ordersLoading={ordersLoading}
          orders={orders}
          totalPages={totalPages}
          orderColumns={orderColumns}
          shortageTasksData={shortageTasksData}
          navigate={navigate}
        />
      )}
      {activeTab === 'tasks' && <TasksTabContent factoryId={activeFactoryId} />}
      {activeTab === 'materials' && <MaterialsTabContent factoryId={activeFactoryId} />}
      {activeTab === 'defects' && <DefectsTabContent factoryId={activeFactoryId} />}
      {activeTab === 'tps' && <TpsTabContent factoryId={activeFactoryId} />}
      {activeTab === 'toc' && <TocTabContent factoryId={activeFactoryId} />}
      {activeTab === 'kilns' && <KilnsTabContent factoryId={activeFactoryId} navigate={navigate} />}
      {activeTab === 'ai_chat' && <AiChatTabContent factoryId={activeFactoryId} />}
    </div>
  );
}

// ===========================================================================
// TAB 1 — Orders (existing, extracted into sub-component)
// ===========================================================================

function OrdersTabContent({
  orderTab,
  setOrderTab,
  page,
  setPage,
  search,
  setSearch,
  statusFilter,
  setStatusFilter,
  createOpen,
  setCreateOpen,
  ordersLoading,
  orders,
  totalPages,
  orderColumns,
  shortageTasksData,
  navigate,
}: {
  orderTab: 'current' | 'archive';
  setOrderTab: (v: 'current' | 'archive') => void;
  page: number;
  setPage: (v: number) => void;
  search: string;
  setSearch: (v: string) => void;
  statusFilter: string;
  setStatusFilter: (v: string) => void;
  createOpen: boolean;
  setCreateOpen: (v: boolean) => void;
  ordersLoading: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  orders: any[];
  totalPages: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  orderColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  shortageTasksData: any;
  navigate: ReturnType<typeof useNavigate>;
}) {
  return (
    <div className="space-y-4">
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

      {/* Stock Shortage Tasks */}
      {(shortageTasksData?.items?.length ?? 0) > 0 && (
        <Card className="border-red-200 bg-red-50/50">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-sm font-semibold text-red-800">Stock Shortage Tasks</span>
            <span className="rounded-full bg-red-200 px-2 py-0.5 text-xs font-medium text-red-800">
              {shortageTasksData!.items.length}
            </span>
          </div>
          <div className="space-y-2">
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {shortageTasksData!.items.map((task: any) => (
              <div
                key={task.id}
                className="flex items-center justify-between rounded-md bg-white px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium text-gray-900">{task.description}</span>
                  {task.related_order_number && (
                    <span className="ml-2 text-gray-400">Order: {task.related_order_number}</span>
                  )}
                </div>
                <Button size="sm" onClick={() => navigate(`/manager/shortage/${task.id}`)}>
                  Resolve
                </Button>
              </div>
            ))}
          </div>
        </Card>
      )}

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

// ===========================================================================
// TAB 2 — Tasks
// ===========================================================================

function TasksTabContent({ factoryId }: { factoryId: string | null }) {
  const [taskFilter, setTaskFilter] = useState<string>('');
  const navigate = useNavigate();

  const params = useMemo(() => {
    const p: Record<string, string> = {};
    if (factoryId) p.factory_id = factoryId;
    if (taskFilter) p.status = taskFilter;
    return p;
  }, [factoryId, taskFilter]);

  const { data: tasksData, isLoading } = useTasks(params);
  const tasks = tasksData?.items || [];

  const pendingCount = tasks.filter((t) => t.status === 'pending').length;
  const inProgressCount = tasks.filter((t) => t.status === 'in_progress').length;
  const blockingCount = tasks.filter((t) => t.blocking).length;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const taskColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    {
      key: 'type',
      header: 'Type',
      render: (item) => (
        <span className="text-sm font-medium">{item.type?.replace(/_/g, ' ')}</span>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      render: (item) => (
        <span className="max-w-xs truncate text-sm text-gray-700">{item.description || '\u2014'}</span>
      ),
    },
    {
      key: 'assigned_to_name',
      header: 'Assigned To',
      render: (item) => item.assigned_to_name || <span className="text-gray-400">Unassigned</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => (
        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${TASK_STATUS_COLORS[item.status] || 'bg-gray-100 text-gray-600'}`}>
          {item.status?.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'blocking',
      header: 'Blocking',
      render: (item) => item.blocking ? (
        <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">Yes</span>
      ) : (
        <span className="text-xs text-gray-400">No</span>
      ),
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (item) => <span className="text-sm">{item.priority ?? '\u2014'}</span>,
    },
    {
      key: 'due_at',
      header: 'Due',
      render: (item) => item.due_at ? new Date(item.due_at).toLocaleDateString() : '\u2014',
    },
  ];

  return (
    <div className="space-y-4">
      {/* Task summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <div className="text-xs text-gray-500">Pending</div>
          <div className="mt-1 text-2xl font-bold text-yellow-600">{pendingCount}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">In Progress</div>
          <div className="mt-1 text-2xl font-bold text-blue-600">{inProgressCount}</div>
        </Card>
        <Card className={blockingCount > 0 ? 'border-red-200 bg-red-50/50' : ''}>
          <div className="text-xs text-gray-500">Blocking</div>
          <div className={`mt-1 text-2xl font-bold ${blockingCount > 0 ? 'text-red-600' : 'text-gray-900'}`}>{blockingCount}</div>
        </Card>
      </div>

      {/* Filter row */}
      <div className="flex items-center gap-3">
        <select
          value={taskFilter}
          onChange={(e) => setTaskFilter(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
        </select>
        <div className="flex-1" />
        <span className="text-sm text-gray-500">{tasks.length} task{tasks.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Tasks table */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : tasks.length === 0 ? (
        <EmptyState title="No tasks found" description="All clear for this factory" />
      ) : (
        <DataTable
          columns={taskColumns}
          data={tasks}
          onRowClick={(item) => navigate(`/manager/tasks/${item.id}`)}
        />
      )}
    </div>
  );
}

// ===========================================================================
// TAB 3 — Materials
// ===========================================================================

function MaterialsTabContent({ factoryId }: { factoryId: string | null }) {
  const navigate = useNavigate();

  const { data: lowStockData, isLoading: lowStockLoading } = useLowStock(factoryId || undefined);
  const { data: purchaseData, isLoading: prLoading } = usePurchaseRequests(
    factoryId ? { factory_id: factoryId, status: 'pending' } : { status: 'pending' },
  );

  const lowStockItems = lowStockData?.items || [];
  const pendingRequests = purchaseData?.items || [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const lowStockColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    { key: 'name', header: 'Material' },
    { key: 'material_type', header: 'Type' },
    {
      key: 'balance',
      header: 'Current Stock',
      render: (item) => (
        <span className={item.balance <= 0 ? 'font-medium text-red-600' : ''}>
          {item.balance} {item.unit}
        </span>
      ),
    },
    {
      key: 'min_balance',
      header: 'Min Balance',
      render: (item) => <span>{item.min_balance} {item.unit}</span>,
    },
    {
      key: 'deficit',
      header: 'Deficit',
      render: (item) => {
        const deficit = item.deficit ?? (item.min_balance - item.balance);
        return deficit > 0 ? (
          <span className="font-medium text-red-600">-{deficit} {item.unit}</span>
        ) : (
          <span className="text-gray-400">{'\u2014'}</span>
        );
      },
    },
    {
      key: 'supplier_name',
      header: 'Supplier',
      render: (item) => item.supplier_name || <span className="text-gray-400">N/A</span>,
    },
  ];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const prColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    {
      key: 'supplier_name',
      header: 'Supplier',
      render: (item) => item.supplier_name || 'Unknown',
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <Badge status={item.status} />,
    },
    {
      key: 'source',
      header: 'Source',
      render: (item) => <span className="text-sm capitalize">{item.source?.replace(/_/g, ' ') || '\u2014'}</span>,
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (item) => item.created_at ? new Date(item.created_at).toLocaleDateString() : '\u2014',
    },
    {
      key: 'expected_delivery_date',
      header: 'Expected Delivery',
      render: (item) => item.expected_delivery_date ? new Date(item.expected_delivery_date).toLocaleDateString() : '\u2014',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Low stock section */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Material Shortages
            {lowStockItems.length > 0 && (
              <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                {lowStockItems.length}
              </span>
            )}
          </h2>
          <Button variant="secondary" size="sm" onClick={() => navigate('/manager/materials')}>
            View All Materials
          </Button>
        </div>

        {lowStockLoading ? (
          <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>
        ) : lowStockItems.length === 0 ? (
          <Card className="border-green-200 bg-green-50/50">
            <p className="text-center text-sm text-green-800">All material levels are within acceptable range.</p>
          </Card>
        ) : (
          <DataTable columns={lowStockColumns} data={lowStockItems} />
        )}
      </div>

      {/* Purchase requests section */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Pending Purchase Requests
            {pendingRequests.length > 0 && (
              <span className="ml-2 rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">
                {pendingRequests.length}
              </span>
            )}
          </h2>
        </div>

        {prLoading ? (
          <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>
        ) : pendingRequests.length === 0 ? (
          <EmptyState title="No pending purchase requests" description="All purchase requests have been processed" />
        ) : (
          <DataTable columns={prColumns} data={pendingRequests} />
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// TAB 4 — Defects
// ===========================================================================

function DefectsTabContent({ factoryId }: { factoryId: string | null }) {
  const navigate = useNavigate();

  const statsParams = useMemo(
    () => (factoryId ? factoryId : undefined),
    [factoryId],
  );
  const { data: qualityStats, isLoading: statsLoading } = useQualityStats(statsParams);

  const defectsParams = useMemo(
    () => (factoryId ? { factory_id: factoryId, result: 'defect' } : { result: 'defect' }),
    [factoryId],
  );
  const { data: inspectionsData, isLoading: inspLoading } = useInspections(defectsParams);

  const { data: problemCardsData, isLoading: pcLoading } = useProblemCards(factoryId || undefined, 'open');

  const defectInspections = inspectionsData?.items || [];
  const problemCards = problemCardsData?.items || [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const defectColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    {
      key: 'order_number',
      header: 'Order',
      render: (item) => item.order_number || '\u2014',
    },
    {
      key: 'stage',
      header: 'Stage',
      render: (item) => <span className="capitalize">{item.stage?.replace(/_/g, ' ')}</span>,
    },
    {
      key: 'defect_cause',
      header: 'Cause',
      render: (item) => item.defect_cause?.description || item.defect_cause?.code || '\u2014',
    },
    {
      key: 'notes',
      header: 'Notes',
      render: (item) => (
        <span className="max-w-xs truncate text-sm text-gray-600">{item.notes || '\u2014'}</span>
      ),
    },
    {
      key: 'checked_by_name',
      header: 'Inspector',
      render: (item) => item.checked_by_name || '\u2014',
    },
    {
      key: 'created_at',
      header: 'Date',
      render: (item) => item.created_at ? new Date(item.created_at).toLocaleDateString() : '\u2014',
    },
  ];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pcColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    { key: 'description', header: 'Description' },
    {
      key: 'location',
      header: 'Location',
      render: (item) => item.location || '\u2014',
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <Badge status={item.status} />,
    },
    {
      key: 'created_at',
      header: 'Opened',
      render: (item) => item.created_at ? new Date(item.created_at).toLocaleDateString() : '\u2014',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Quality stats summary */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <div className="text-xs text-gray-500">Pending QC</div>
          <div className="mt-1 text-2xl font-bold text-yellow-600">
            {statsLoading ? '\u2014' : qualityStats?.pending_qc ?? 0}
          </div>
        </Card>
        <Card className={qualityStats?.blocked ? 'border-red-200 bg-red-50/50' : ''}>
          <div className="text-xs text-gray-500">Blocked</div>
          <div className={`mt-1 text-2xl font-bold ${(qualityStats?.blocked ?? 0) > 0 ? 'text-red-600' : 'text-gray-900'}`}>
            {statsLoading ? '\u2014' : qualityStats?.blocked ?? 0}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Open Problem Cards</div>
          <div className="mt-1 text-2xl font-bold text-orange-600">
            {statsLoading ? '\u2014' : qualityStats?.open_problem_cards ?? 0}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Inspections Today</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {statsLoading ? '\u2014' : qualityStats?.inspections_today ?? 0}
          </div>
        </Card>
      </div>

      {/* Recent defect inspections */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Recent Defects</h2>
          <Button variant="secondary" size="sm" onClick={() => navigate('/manager/quality')}>
            Quality Dashboard
          </Button>
        </div>

        {inspLoading ? (
          <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>
        ) : defectInspections.length === 0 ? (
          <Card className="border-green-200 bg-green-50/50">
            <p className="text-center text-sm text-green-800">No defects recorded recently.</p>
          </Card>
        ) : (
          <DataTable columns={defectColumns} data={defectInspections} />
        )}
      </div>

      {/* Open problem cards (repair queue) */}
      <div>
        <div className="mb-3">
          <h2 className="text-lg font-semibold text-gray-900">
            Open Problem Cards (Repair Queue)
            {problemCards.length > 0 && (
              <span className="ml-2 rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700">
                {problemCards.length}
              </span>
            )}
          </h2>
        </div>

        {pcLoading ? (
          <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>
        ) : problemCards.length === 0 ? (
          <EmptyState title="No open problem cards" description="No items in the repair queue" />
        ) : (
          <DataTable columns={pcColumns} data={problemCards} />
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// TAB 5 — TPS
// ===========================================================================

function TpsTabContent({ factoryId }: { factoryId: string | null }) {
  const params = useMemo(
    () => (factoryId ? { factory_id: factoryId } : undefined),
    [factoryId],
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: tpsData, isLoading } = useQuery<{ items: any[]; total: number }>({
    queryKey: ['tps', params],
    queryFn: () => tpsApi.list(params),
  });

  const { data: dashboardSummary } = useDashboardSummary(params);

  const signals = tpsData?.items || [];

  return (
    <div className="space-y-6">
      {/* TPS overview cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <div className="text-xs text-gray-500">Output (sqm)</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {dashboardSummary?.output_sqm != null ? dashboardSummary.output_sqm.toFixed(1) : '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">OEE</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {dashboardSummary?.oee != null ? `${Math.round(dashboardSummary.oee)}%` : '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Cost per sqm</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {dashboardSummary?.cost_per_sqm != null ? `$${dashboardSummary.cost_per_sqm.toFixed(2)}` : '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">TPS Signals</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{signals.length}</div>
        </Card>
      </div>

      {/* TPS signals list */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">TPS Signal Board</h2>

        {isLoading ? (
          <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>
        ) : signals.length === 0 ? (
          <Card className="border-green-200 bg-green-50/50">
            <p className="text-center text-sm text-green-800">No active TPS signals. Production is flowing normally.</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {signals.map((signal: any) => (
              <Card
                key={signal.id}
                className={
                  signal.severity === 'critical' ? 'border-red-300 bg-red-50/50' :
                  signal.severity === 'warning' ? 'border-yellow-300 bg-yellow-50/50' :
                  ''
                }
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900">
                        {signal.title || signal.type?.replace(/_/g, ' ') || 'TPS Signal'}
                      </span>
                      {signal.severity && (
                        <Badge status={signal.severity} />
                      )}
                    </div>
                    <p className="mt-1 text-sm text-gray-600">{signal.description || signal.message || '\u2014'}</p>
                  </div>
                  <span className="text-xs text-gray-400">
                    {signal.created_at ? new Date(signal.created_at).toLocaleString() : ''}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// TAB 6 — TOC (Bottleneck / Buffer Status)
// ===========================================================================

function TocTabContent({ factoryId }: { factoryId: string | null }) {
  const params = useMemo(
    () => (factoryId ? { factory_id: factoryId } : undefined),
    [factoryId],
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: tocData, isLoading: tocLoading } = useQuery<{ items: any[]; total: number }>({
    queryKey: ['toc', params],
    queryFn: () => tocApi.list(params),
  });

  const { data: bufferHealth, isLoading: bufferLoading } = useBufferHealth(params);

  const tocItems = tocData?.items || [];
  const buffers = bufferHealth?.items || [];

  return (
    <div className="space-y-6">
      {/* Buffer Health Overview */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Buffer Health (Kiln Constraints)</h2>

        {bufferLoading ? (
          <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>
        ) : buffers.length === 0 ? (
          <EmptyState title="No buffer data available" description="Buffer health data will appear once kilns are scheduled" />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {buffers.map((buffer) => {
              const pct = buffer.target > 0 ? Math.round((buffer.hours / buffer.target) * 100) : 0;
              return (
                <Card key={buffer.kiln_id}>
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-900">{buffer.kiln_name}</span>
                    <span
                      className={`inline-block h-3 w-3 rounded-full ${BUFFER_HEALTH_COLORS[buffer.health] || 'bg-gray-300'}`}
                      title={`Health: ${buffer.health}`}
                    />
                  </div>
                  {buffer.factory_name && (
                    <p className="mb-1 text-xs text-gray-400">{buffer.factory_name}</p>
                  )}
                  <div className="mb-2 flex items-baseline gap-1">
                    <span className="text-xl font-bold text-gray-900">{buffer.hours}h</span>
                    <span className="text-sm text-gray-500">/ {buffer.target}h target</span>
                  </div>
                  <ProgressBar value={pct} />
                  <div className="mt-2 flex justify-between text-xs text-gray-500">
                    <span>{buffer.buffered_count} positions buffered</span>
                    <span>{buffer.buffered_sqm.toFixed(1)} sqm</span>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* TOC entries list */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">TOC / Bottleneck Log</h2>

        {tocLoading ? (
          <div className="flex justify-center py-8"><Spinner className="h-8 w-8" /></div>
        ) : tocItems.length === 0 ? (
          <Card className="border-green-200 bg-green-50/50">
            <p className="text-center text-sm text-green-800">No active bottlenecks detected.</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {tocItems.map((item: any) => (
              <Card key={item.id}>
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-sm font-semibold text-gray-900">
                      {item.title || item.constraint_name || item.type?.replace(/_/g, ' ') || 'Bottleneck'}
                    </span>
                    {item.status && (
                      <Badge status={item.status} className="ml-2" />
                    )}
                    <p className="mt-1 text-sm text-gray-600">{item.description || item.notes || '\u2014'}</p>
                  </div>
                  <span className="text-xs text-gray-400">
                    {item.created_at ? new Date(item.created_at).toLocaleString() : ''}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// TAB 7 — Kilns
// ===========================================================================

function KilnsTabContent({
  factoryId,
  navigate,
}: {
  factoryId: string | null;
  navigate: ReturnType<typeof useNavigate>;
}) {
  const params = useMemo(
    () => (factoryId ? { factory_id: factoryId } : undefined),
    [factoryId],
  );

  const { data: kilnsData, isLoading } = useKilns(params);
  const kilns = kilnsData?.items || [];

  const idleCount = kilns.filter((k) => k.status === 'idle').length;
  const firingCount = kilns.filter((k) => k.status === 'firing').length;
  const maintenanceCount = kilns.filter((k) => k.status === 'maintenance').length;
  const activeCount = kilns.filter((k) => k.is_active).length;

  return (
    <div className="space-y-6">
      {/* Kiln summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <div className="text-xs text-gray-500">Total Active</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{activeCount}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Firing</div>
          <div className="mt-1 text-2xl font-bold text-orange-600">{firingCount}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Idle</div>
          <div className="mt-1 text-2xl font-bold text-gray-500">{idleCount}</div>
        </Card>
        <Card className={maintenanceCount > 0 ? 'border-red-200 bg-red-50/50' : ''}>
          <div className="text-xs text-gray-500">Maintenance</div>
          <div className={`mt-1 text-2xl font-bold ${maintenanceCount > 0 ? 'text-red-600' : 'text-gray-900'}`}>{maintenanceCount}</div>
        </Card>
      </div>

      {/* Actions */}
      <div className="flex justify-end">
        <Button onClick={() => navigate('/manager/kilns')}>
          Open Full Kiln Management
        </Button>
      </div>

      {/* Kiln cards grid */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
      ) : kilns.length === 0 ? (
        <EmptyState title="No kilns found" description="No kilns registered for this factory" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {kilns.map((kiln) => (
            <Card
              key={kiln.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => navigate(`/manager/kilns/${kiln.id}`)}
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-900">{kiln.name}</span>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    KILN_STATUS_COLORS[kiln.status] || 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {kiln.status?.replace(/_/g, ' ')}
                </span>
              </div>
              {kiln.factory_name && (
                <p className="mb-1 text-xs text-gray-400">{kiln.factory_name}</p>
              )}
              <div className="space-y-1 text-xs text-gray-600">
                <div className="flex justify-between">
                  <span>Type:</span>
                  <span className="font-medium capitalize">{kiln.kiln_type?.replace(/_/g, ' ')}</span>
                </div>
                {kiln.kiln_dimensions_cm && (
                  <div className="flex justify-between">
                    <span>Dimensions:</span>
                    <span className="font-medium">
                      {kiln.kiln_dimensions_cm.width} x {kiln.kiln_dimensions_cm.depth} x {kiln.kiln_dimensions_cm.height} cm
                    </span>
                  </div>
                )}
                {kiln.capacity_sqm != null && (
                  <div className="flex justify-between">
                    <span>Capacity:</span>
                    <span className="font-medium">{kiln.capacity_sqm} sqm</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Levels:</span>
                  <span className="font-medium">{kiln.num_levels}</span>
                </div>
                {kiln.kiln_coefficient != null && (
                  <div className="flex justify-between">
                    <span>Coefficient:</span>
                    <span className="font-medium">{kiln.kiln_coefficient}</span>
                  </div>
                )}
              </div>
              {!kiln.is_active && (
                <div className="mt-2 rounded bg-gray-100 px-2 py-1 text-center text-xs font-medium text-gray-500">
                  Inactive
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ===========================================================================
// TAB 8 — AI Chat
// ===========================================================================

function AiChatTabContent({ factoryId }: { factoryId: string | null }) {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setSending(true);

    try {
      const payload: Record<string, unknown> = { message: text };
      if (factoryId) payload.factory_id = factoryId;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const response: any = await ai_chatApi.create(payload);
      const reply = response?.reply || response?.message || response?.text || JSON.stringify(response);
      setMessages((prev) => [...prev, { role: 'assistant', text: reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: 'Sorry, something went wrong. Please try again.' },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 380px)', minHeight: 400 }}>
      <Card className="flex flex-1 flex-col overflow-hidden p-0">
        {/* Chat header */}
        <div className="border-b border-gray-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-gray-900">AI Production Assistant</h2>
          <p className="text-xs text-gray-500">Ask questions about production, orders, scheduling, and more</p>
        </div>

        {/* Messages area */}
        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="mb-3 rounded-full bg-primary-50 p-3">
                <svg className="h-6 w-6 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-gray-900">Start a conversation</p>
              <p className="mt-1 text-xs text-gray-500">
                Try: &quot;What orders are behind schedule?&quot; or &quot;Show kiln utilization summary&quot;
              </p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[75%] rounded-lg px-4 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.text}</p>
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="rounded-lg bg-gray-100 px-4 py-2">
                <Spinner className="h-4 w-4" />
              </div>
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 p-3">
          <form
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              disabled={sending}
            />
            <Button type="submit" disabled={sending || !input.trim()}>
              Send
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
