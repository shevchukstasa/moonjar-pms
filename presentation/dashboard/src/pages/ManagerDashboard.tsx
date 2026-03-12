import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import apiClient from '@/api/client';
import { useOrders, useCancellationRequests, useChangeRequests } from '@/hooks/useOrders';
import { usePositions, type PositionItem } from '@/hooks/usePositions';
import { useShortageTasksForManager, useTasks } from '@/hooks/useTasks';
import { useLowStock } from '@/hooks/useMaterials';
import { usePurchaseRequests } from '@/hooks/usePurchaseRequests';
import { useKilns } from '@/hooks/useKilns';
import { useQualityStats, useInspections } from '@/hooks/useQuality';
import { useProblemCards } from '@/hooks/useProblemCards';
import { useBufferHealth, useDashboardSummary } from '@/hooks/useAnalytics';
import { useUiStore } from '@/stores/uiStore';
import { useCurrentUser } from '@/hooks/useCurrentUser';
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
import { aiChatApi } from '@/api/ai_chat';
import type { OrderListParams } from '@/api/orders';
import { CancellationRequestsPanel } from '@/components/dashboard/CancellationRequestsPanel';
import { ChangeRequestsPanel } from '@/components/dashboard/ChangeRequestsPanel';
import { NotificationsBell } from '@/components/dashboard/NotificationsBell';
import { ColorMismatchDecisionDialog } from '@/components/positions/ColorMismatchDecisionDialog';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

type DashboardTab = 'orders' | 'tasks' | 'materials' | 'defects' | 'tps' | 'toc' | 'kilns' | 'ai_chat' | 'cancellations' | 'change_requests' | 'mismatch';

const DASHBOARD_TABS_BASE: { id: DashboardTab; label: string }[] = [
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
  const queryClient = useQueryClient();
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);
  const currentUser = useCurrentUser();

  // --- Top-level tab ---
  const [activeTab, setActiveTab] = useState<DashboardTab>('orders');

  // --- Orders tab state ---
  const [orderTab, setOrderTab] = useState<'current' | 'archive'>('current');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const debouncedSearch = useDebounce(search, 400);

  // --- Order delete permissions ---
  const [canDeleteOrders, setCanDeleteOrders] = useState(false);
  const [deletingOrderId, setDeletingOrderId] = useState<string | null>(null);

  useEffect(() => {
    if (activeFactoryId) {
      apiClient.get('/cleanup/permissions', { params: { factory_id: activeFactoryId } })
        .then((r) => setCanDeleteOrders(r.data.pm_can_delete_orders))
        .catch(() => setCanDeleteOrders(false));
    } else {
      const userFactories = currentUser?.factories ?? [];
      if (userFactories.length === 0) { setCanDeleteOrders(false); return; }
      Promise.all(
        userFactories.map((f) =>
          apiClient.get('/cleanup/permissions', { params: { factory_id: f.id } })
            .then((r) => ({ allowed: r.data.pm_can_delete_orders as boolean }))
            .catch(() => ({ allowed: false }))
        )
      ).then((results) => setCanDeleteOrders(results.some((r) => r.allowed)));
    }
  }, [activeFactoryId, currentUser]);

  const handleDeleteOrder = useCallback(async (orderId: string, orderFactoryId?: string) => {
    const fid = activeFactoryId || orderFactoryId;
    if (!fid) { alert('Select a specific factory to delete orders.'); return; }
    if (!window.confirm('Delete this order and ALL its positions and tasks? This cannot be undone.')) return;
    setDeletingOrderId(orderId);
    try {
      await apiClient.delete(`/cleanup/orders/${orderId}`, { params: { factory_id: fid } });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Delete failed';
      alert(msg);
    } finally {
      setDeletingOrderId(null);
    }
  }, [activeFactoryId, queryClient]);

  const ordersParams = useMemo<OrderListParams>(() => {
    const p: OrderListParams = { page, per_page: 20, tab: orderTab };
    if (activeFactoryId) p.factory_id = activeFactoryId;
    if (debouncedSearch) p.search = debouncedSearch;
    if (statusFilter) p.status = statusFilter;
    return p;
  }, [page, orderTab, activeFactoryId, debouncedSearch, statusFilter]);

  const { data: ordersData, isLoading: ordersLoading, isError: ordersError } = useOrders(ordersParams);
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

  // --- Cancellation requests (poll every 30s) ---
  const cancelParams = useMemo(
    () => ({ ...(activeFactoryId ? { factory_id: activeFactoryId } : {}), decision: 'pending' }),
    [activeFactoryId],
  );
  const { data: cancellationData } = useCancellationRequests(cancelParams);
  const pendingCancellations: number = cancellationData?.total ?? 0;

  // --- Change requests (poll every 60s) ---
  const changeReqParams = useMemo(
    () => (activeFactoryId ? { factory_id: activeFactoryId } : undefined),
    [activeFactoryId],
  );
  const { data: changeReqData } = useChangeRequests(changeReqParams);
  const pendingChangeRequests: number = changeReqData?.total ?? 0;

  // --- Color mismatch positions awaiting PM decision ---
  const mismatchParams = useMemo(
    () => ({
      ...(activeFactoryId ? { factory_id: activeFactoryId } : {}),
      split_category: 'color_mismatch',
      status: 'planned',
      per_page: 100,
    }),
    [activeFactoryId],
  );
  const { data: mismatchData } = usePositions(mismatchParams);
  const pendingMismatches: number = mismatchData?.total ?? 0;

  // Build tabs dynamically — show badge counts on action-required tabs
  const DASHBOARD_TABS = useMemo(
    () => [
      ...DASHBOARD_TABS_BASE,
      {
        id: 'mismatch' as DashboardTab,
        label: pendingMismatches > 0 ? `Color Mismatch (${pendingMismatches})` : 'Color Mismatch',
      },
      {
        id: 'cancellations' as DashboardTab,
        label: pendingCancellations > 0 ? `Cancellations (${pendingCancellations})` : 'Cancellations',
      },
      {
        id: 'change_requests' as DashboardTab,
        label: pendingChangeRequests > 0 ? `Changes (${pendingChangeRequests})` : 'Changes',
      },
    ],
    [pendingMismatches, pendingCancellations, pendingChangeRequests],
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const orderColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    { key: 'order_number', header: 'Order #' },
    { key: 'client', header: 'Client' },
    {
      key: 'sales_manager_name',
      header: 'Manager',
      render: (item) => item.sales_manager_name
        ? <span className="text-sm text-gray-700">{item.sales_manager_name}</span>
        : <span className="text-gray-400">&mdash;</span>,
    },
    {
      key: 'created_at',
      header: 'Received',
      render: (item) => item.created_at
        ? (
          <span className="text-sm text-gray-600">
            {new Date(item.created_at).toLocaleDateString()}{' '}
            <span className="text-gray-400 text-xs">
              {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </span>
        )
        : <span className="text-gray-400">&mdash;</span>,
    },
    {
      key: 'final_deadline',
      header: 'Deadline',
      render: (item) => {
        if (!item.final_deadline) return <span className="text-gray-400">&mdash;</span>;
        const daysLeft = item.days_remaining;
        const color = daysLeft == null ? 'text-gray-600'
          : daysLeft < 0 ? 'text-red-600 font-semibold'
          : daysLeft <= 3 ? 'text-orange-500 font-medium'
          : 'text-gray-700';
        return (
          <span className={`text-sm ${color}`}>
            {new Date(item.final_deadline).toLocaleDateString()}
            {daysLeft != null && (
              <span className="ml-1 text-xs font-normal text-gray-400">
                ({daysLeft < 0 ? `${Math.abs(daysLeft)}d late` : `${daysLeft}d`})
              </span>
            )}
          </span>
        );
      },
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
    // Delete column — only shown when PM cleanup for orders is enabled
    ...(canDeleteOrders ? [{
      key: '_delete',
      header: '',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      render: (item: any) => (
        <button
          onClick={(e) => { e.stopPropagation(); handleDeleteOrder(item.id, item.factory_id); }}
          disabled={deletingOrderId === item.id}
          className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
          title="Delete order"
        >
          {deletingOrderId === item.id
            ? <span className="text-xs">...</span>
            : <Trash2 className="h-4 w-4" />}
        </button>
      ),
    }] : []),
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Production Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">Manage orders, positions, and production schedule</p>
        </div>
        <div className="flex items-center gap-3">
          <NotificationsBell />
          <FactorySelector />
        </div>
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

      {/* API Error banner */}
      {ordersError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">⚠ Error loading orders. Try refreshing.</p>
        </div>
      )}

      {/* Color mismatch alert banner — shown when PM decisions are pending */}
      {pendingMismatches > 0 && activeTab !== 'mismatch' && (
        <div
          className="cursor-pointer rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 flex items-center justify-between gap-3 hover:bg-amber-100 transition-colors"
          onClick={() => setActiveTab('mismatch')}
        >
          <div className="flex items-center gap-2">
            <span className="text-amber-600 text-lg">🎨</span>
            <span className="text-sm font-medium text-amber-800">
              {pendingMismatches} color mismatch position{pendingMismatches > 1 ? 's' : ''} awaiting your decision
            </span>
          </div>
          <span className="text-xs text-amber-600 underline">Resolve →</span>
        </div>
      )}

      {/* Cancellation request alert banner — shown above tabs when requests are pending */}
      {pendingCancellations > 0 && activeTab !== 'cancellations' && (
        <div
          className="cursor-pointer rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 flex items-center justify-between gap-3 hover:bg-amber-100 transition-colors"
          onClick={() => setActiveTab('cancellations')}
        >
          <div className="flex items-center gap-2">
            <span className="text-amber-600 text-lg">⚠</span>
            <span className="text-sm font-medium text-amber-800">
              {pendingCancellations} pending cancellation request{pendingCancellations > 1 ? 's' : ''} from Sales — requires your decision
            </span>
          </div>
          <span className="text-xs text-amber-600 underline">View →</span>
        </div>
      )}

      {/* Change request alert banner — shown when requests are pending */}
      {pendingChangeRequests > 0 && activeTab !== 'change_requests' && (
        <div
          className="cursor-pointer rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 flex items-center justify-between gap-3 hover:bg-blue-100 transition-colors"
          onClick={() => setActiveTab('change_requests')}
        >
          <div className="flex items-center gap-2">
            <span className="text-blue-600 text-lg">i</span>
            <span className="text-sm font-medium text-blue-800">
              {pendingChangeRequests} pending change request{pendingChangeRequests > 1 ? 's' : ''} from Sales — review and apply or discard
            </span>
          </div>
          <span className="text-xs text-blue-600 underline">View →</span>
        </div>
      )}

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
      {activeTab === 'mismatch' && (
        <ColorMismatchTabContent factoryId={activeFactoryId} />
      )}
      {activeTab === 'cancellations' && (
        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Cancellation Requests</h2>
            <p className="mt-0.5 text-sm text-gray-500">
              Sales app requested order cancellations. Review each request and accept or reject.
            </p>
          </div>
          <CancellationRequestsPanel factoryId={activeFactoryId} />
        </div>
      )}
      {activeTab === 'change_requests' && (
        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Change Requests from Sales</h2>
            <p className="mt-0.5 text-sm text-gray-500">
              Sales app sent updated order data. Apply changes to update the order, or discard to keep current data.
            </p>
          </div>
          <ChangeRequestsPanel factoryId={activeFactoryId} />
        </div>
      )}
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
  const [canDeleteTasks, setCanDeleteTasks] = useState(false);
  const [deleteFactoryMap, setDeleteFactoryMap] = useState<Record<string, boolean>>({});
  const [deletingTaskId, setDeletingTaskId] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const currentUser = useCurrentUser();

  // Fetch PM cleanup permissions — single factory or all user factories
  useEffect(() => {
    if (factoryId) {
      apiClient.get('/cleanup/permissions', { params: { factory_id: factoryId } })
        .then((r) => {
          const allowed = r.data.pm_can_delete_tasks;
          setCanDeleteTasks(allowed);
          setDeleteFactoryMap({ [factoryId]: allowed });
        })
        .catch(() => { setCanDeleteTasks(false); setDeleteFactoryMap({}); });
    } else {
      const userFactories = currentUser?.factories ?? [];
      if (userFactories.length === 0) { setCanDeleteTasks(false); setDeleteFactoryMap({}); return; }
      Promise.all(
        userFactories.map((f) =>
          apiClient.get('/cleanup/permissions', { params: { factory_id: f.id } })
            .then((r) => ({ id: f.id, allowed: r.data.pm_can_delete_tasks as boolean }))
            .catch(() => ({ id: f.id, allowed: false }))
        )
      ).then((results) => {
        const map: Record<string, boolean> = {};
        let anyAllowed = false;
        for (const r of results) { map[r.id] = r.allowed; if (r.allowed) anyAllowed = true; }
        setCanDeleteTasks(anyAllowed);
        setDeleteFactoryMap(map);
      });
    }
  }, [factoryId, currentUser]);

  const handleDeleteTask = useCallback(async (taskId: string, taskFactoryId?: string) => {
    const fid = factoryId || taskFactoryId;
    if (!fid) { alert('Cannot determine factory for this task. Select a specific factory.'); return; }
    if (!window.confirm('Delete this task permanently? This cannot be undone.')) return;
    setDeletingTaskId(taskId);
    try {
      await apiClient.delete(`/cleanup/tasks/${taskId}`, {
        params: { factory_id: fid },
      });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Delete failed';
      alert(msg);
    } finally {
      setDeletingTaskId(null);
    }
  }, [factoryId, queryClient]);

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
      key: 'created_at',
      header: 'Created',
      render: (item) => item.created_at ? (
        <span className="text-xs text-gray-500">
          {new Date(item.created_at).toLocaleDateString()}{' '}
          {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      ) : <span className="text-gray-400">&mdash;</span>,
    },
    {
      key: 'due_at',
      header: 'Due',
      render: (item) => item.due_at ? new Date(item.due_at).toLocaleDateString() : '\u2014',
    },
    // Delete column — only shown when PM cleanup is enabled
    ...(canDeleteTasks ? [{
      key: '_delete',
      header: '',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      render: (item: any) => {
        // When "All Factories" mode, check per-factory permission
        if (!factoryId && item.factory_id && !deleteFactoryMap[item.factory_id]) return null;
        return (
        <button
          onClick={(e) => { e.stopPropagation(); handleDeleteTask(item.id, item.factory_id); }}
          disabled={deletingTaskId === item.id}
          className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
          title="Delete task"
        >
          {deletingTaskId === item.id
            ? <span className="text-xs">...</span>
            : <Trash2 className="h-4 w-4" />}
        </button>
        );
      },
    }] : []),
  ];

  return (
    <div className="space-y-4">
      {/* Cleanup mode banner */}
      {canDeleteTasks && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          🗑 Cleanup mode: delete buttons are visible on each task row.
        </div>
      )}

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
    queryFn: () => tocApi.listConstraints(params),
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
      const response: any = await aiChatApi.chat(payload as any);
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

// ===========================================================================
// TAB — Color Mismatch (PM Decision Queue)
// ===========================================================================

function ColorMismatchTabContent({ factoryId }: { factoryId: string | null }) {
  const params = useMemo(
    () => ({
      ...(factoryId ? { factory_id: factoryId } : {}),
      split_category: 'color_mismatch',
      status: 'planned',
      per_page: 100,
    }),
    [factoryId],
  );
  const { data, isLoading } = usePositions(params);
  const positions = data?.items ?? [];

  const [selectedPosition, setSelectedPosition] = useState<PositionItem | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  function openDialog(pos: PositionItem) {
    setSelectedPosition(pos);
    setDialogOpen(true);
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Color Mismatch — PM Decision Queue</h2>
        <p className="mt-0.5 text-sm text-gray-500">
          These positions have color mismatches identified by the sorter.
          Decide how to handle each batch: refire only, reglaze + refire, or pack for stock.
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : positions.length === 0 ? (
        <EmptyState
          title="No color mismatch positions"
          description="All color mismatch batches have been resolved."
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {['Order #', 'Color', 'Size', 'Application', 'Collection', 'Qty (pcs)', 'Product Type', 'Action'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {positions.map((pos) => (
                <tr key={pos.id} className="hover:bg-amber-50 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{pos.order_number}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{pos.color}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{pos.size}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{pos.application ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{pos.collection ?? '—'}</td>
                  <td className="px-4 py-3 text-sm font-semibold text-gray-900">{pos.quantity}</td>
                  <td className="px-4 py-3 text-sm text-gray-500 capitalize">{pos.product_type.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-3">
                    <Button variant="primary" onClick={() => openDialog(pos)}>
                      Decide
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ColorMismatchDecisionDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        position={selectedPosition}
      />
    </div>
  );
}
