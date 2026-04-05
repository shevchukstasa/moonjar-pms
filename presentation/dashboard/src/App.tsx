import { useState, useEffect } from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { roleRoutes } from '@/lib/roleRoutes';
import apiClient from '@/api/client';
import LoginPage from '@/pages/LoginPage';
import NotFoundPage from '@/pages/NotFoundPage';
import OwnerDashboard from '@/pages/OwnerDashboard';
import CeoDashboard from '@/pages/CeoDashboard';
import ManagerDashboard from '@/pages/ManagerDashboard';
import OrderDetailPage from '@/pages/OrderDetailPage';
import ManagerSchedulePage from '@/pages/ManagerSchedulePage';
import ManagerKilnsPage from '@/pages/ManagerKilnsPage';
import ManagerMaterialsPage from '@/pages/ManagerMaterialsPage';
import ShortageDecisionPage from '@/pages/ShortageDecisionPage';
import SizeResolutionPage from '@/pages/SizeResolutionPage';
import TabloDashboard from '@/pages/TabloDashboard';
import QualityManagerDashboard from '@/pages/QualityManagerDashboard';
import WarehouseDashboard from '@/pages/WarehouseDashboard';
import SorterPackerDashboard from '@/pages/SorterPackerDashboard';
import PurchaserDashboard from '@/pages/PurchaserDashboard';
import UsersPage from '@/pages/UsersPage';
import AdminPanelPage from '@/pages/AdminPanelPage';
import AdminRecipesPage from '@/pages/AdminRecipesPage';
import AdminSuppliersPage from '@/pages/AdminSuppliersPage';
import AdminCollectionsPage from '@/pages/AdminCollectionsPage';
import AdminColorCollectionsPage from '@/pages/AdminColorCollectionsPage';
import AdminColorsPage from '@/pages/AdminColorsPage';
import AdminAppTypesPage from '@/pages/AdminAppTypesPage';
import AdminPoaPage from '@/pages/AdminPoaPage';
import AdminFinishingPage from '@/pages/AdminFinishingPage';
import AdminTemperatureGroupsPage from '@/pages/AdminTemperatureGroupsPage';
import AdminMaterialsPage from '@/pages/AdminMaterialsPage';
import AdminWarehousesPage from '@/pages/AdminWarehousesPage';
import AdminPackagingPage from '@/pages/AdminPackagingPage';
import AdminSizesPage from '@/pages/AdminSizesPage';
import AdminFiringProfilesPage from '@/pages/AdminFiringProfilesPage';
import AdminStagesPage from '@/pages/AdminStagesPage';
import TpsDashboardPage from '@/pages/TpsDashboardPage';
import KilnFiringSchedulesPage from '@/pages/KilnFiringSchedulesPage';
import FactoryCalendarPage from '@/pages/FactoryCalendarPage';
import ConsumptionRulesPage from '@/pages/ConsumptionRulesPage';
import PMGuidePage from '@/pages/PMGuidePage';
import KilnInspectionsPage from '@/pages/KilnInspectionsPage';
import KilnMaintenancePage from '@/pages/KilnMaintenancePage';
import GrindingDecisionsPage from '@/pages/GrindingDecisionsPage';
import ReconciliationsPage from '@/pages/ReconciliationsPage';
import FinishedGoodsPage from '@/pages/FinishedGoodsPage';
import ManaShipmentsPage from '@/pages/ManaShipmentsPage';
import ReportsPage from '@/pages/ReportsPage';
import DashboardAccessPage from '@/pages/DashboardAccessPage';
import SettingsPage from '@/pages/SettingsPage';
import AdminSettingsPage from '@/pages/AdminSettingsPage';
import EmployeesPage from '@/pages/EmployeesPage';
import CeoEmployeesPage from '@/pages/CeoEmployeesPage';
import ShipmentPage from '@/pages/ShipmentPage';
import WorkforceAssignmentPage from '@/pages/WorkforceAssignmentPage';
import AppLayout from '@/components/layout/AppLayout';
import { Spinner } from '@/components/ui/Spinner';
import { ErrorBoundary, PageErrorFallback } from '@/components/ErrorBoundary';

/** Try to restore session from JWT cookie on app mount */
function useSessionRestore() {
  const [checking, setChecking] = useState(true);
  const login = useAuthStore((s) => s.login);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (isAuthenticated) { setChecking(false); return; }
    apiClient.get('/auth/me')
      .then(({ data }) => { login(data); })
      .catch(() => { /* no valid session — stay logged out */ })
      .finally(() => setChecking(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return checking;
}

function RequireAuth() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return (
    <AppLayout>
      <ErrorBoundary
        fallback={(error, reset) => (
          <PageErrorFallback error={error} onReset={reset} />
        )}
      >
        <Outlet />
      </ErrorBoundary>
    </AppLayout>
  );
}

function RequireRole({ roles }: { roles: string[] }) {
  const user = useAuthStore((s) => s.user);
  if (!user || !roles.includes(user.role)) return <Navigate to="/" replace />;
  return <Outlet />;
}

function RoleRedirect() {
  const user = useAuthStore((s) => s.user);
  const target = user ? roleRoutes[user.role] || '/login' : '/login';
  return <Navigate to={target} replace />;
}

export default function App() {
  const checking = useSessionRestore();

  if (checking) {
    return <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-stone-950"><Spinner className="h-10 w-10" /></div>;
  }

  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<RoleRedirect />} />
          <Route element={<RequireRole roles={['owner']} />}>
            <Route path="/owner" element={<OwnerDashboard />} />
          </Route>
          <Route element={<RequireRole roles={['ceo', 'owner', 'administrator']} />}>
            <Route path="/ceo" element={<CeoDashboard />} />
            <Route path="/ceo/employees" element={<CeoEmployeesPage />} />
          </Route>
          <Route element={<RequireRole roles={['owner', 'administrator']} />}>
            <Route path="/admin" element={<AdminPanelPage />} />
            <Route path="/admin/suppliers" element={<AdminSuppliersPage />} />
            <Route path="/admin/collections" element={<AdminCollectionsPage />} />
            <Route path="/admin/color-collections" element={<AdminColorCollectionsPage />} />
            <Route path="/admin/colors" element={<AdminColorsPage />} />
            <Route path="/admin/application-types" element={<AdminAppTypesPage />} />
            <Route path="/admin/places-of-application" element={<AdminPoaPage />} />
            <Route path="/admin/finishing-types" element={<AdminFinishingPage />} />
            <Route path="/admin/materials" element={<AdminMaterialsPage />} />
            <Route path="/admin/size-resolution/:taskId" element={<SizeResolutionPage />} />
            <Route path="/admin/dashboard-access" element={<DashboardAccessPage />} />
            <Route path="/admin/settings" element={<AdminSettingsPage />} />
            <Route path="/admin/employees" element={<EmployeesPage />} />
          </Route>
          <Route element={<RequireRole roles={['owner', 'administrator', 'production_manager']} />}>
            <Route path="/admin/recipes" element={<AdminRecipesPage />} />
            <Route path="/admin/temperature-groups" element={<AdminTemperatureGroupsPage />} />
            <Route path="/admin/warehouses" element={<AdminWarehousesPage />} />
            <Route path="/admin/packaging" element={<AdminPackagingPage />} />
            <Route path="/admin/sizes" element={<AdminSizesPage />} />
            <Route path="/admin/consumption-rules" element={<ConsumptionRulesPage />} />
            <Route path="/admin/firing-profiles" element={<AdminFiringProfilesPage />} />
            <Route path="/admin/stages" element={<AdminStagesPage />} />
            <Route path="/admin/tps-dashboard" element={<TpsDashboardPage />} />
            <Route path="/admin/firing-schedules" element={<KilnFiringSchedulesPage />} />
            <Route path="/admin/factory-calendar" element={<FactoryCalendarPage />} />
          </Route>
          <Route element={<RequireRole roles={['owner', 'administrator', 'ceo']} />}>
            <Route path="/users" element={<UsersPage />} />
          </Route>
          <Route element={<RequireRole roles={['production_manager', 'owner', 'administrator']} />}>
            <Route path="/manager" element={<ManagerDashboard />} />
            <Route path="/manager/orders/:orderId" element={<OrderDetailPage />} />
            <Route path="/manager/orders/:orderId/shipment" element={<ShipmentPage />} />
            <Route path="/manager/schedule" element={<ManagerSchedulePage />} />
            <Route path="/manager/kilns" element={<ManagerKilnsPage />} />
            <Route path="/manager/materials" element={<ManagerMaterialsPage />} />
            <Route path="/manager/kiln-inspections" element={<KilnInspectionsPage />} />
            <Route path="/manager/kiln-maintenance" element={<KilnMaintenancePage />} />
            <Route path="/manager/grinding" element={<GrindingDecisionsPage />} />
            <Route path="/manager/shortage/:taskId" element={<ShortageDecisionPage />} />
            <Route path="/manager/size-resolution/:taskId" element={<SizeResolutionPage />} />
            <Route path="/manager/guide" element={<PMGuidePage />} />
            <Route path="/manager/staff" element={<EmployeesPage />} />
            <Route path="/manager/workforce" element={<WorkforceAssignmentPage />} />
          </Route>
          <Route element={<RequireRole roles={['owner', 'ceo', 'production_manager']} />}>
            <Route path="/reports" element={<ReportsPage />} />
          </Route>
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/tablo" element={<TabloDashboard />} />
          <Route element={<RequireRole roles={['quality_manager', 'owner', 'administrator']} />}>
            <Route path="/quality" element={<QualityManagerDashboard />} />
          </Route>
          <Route element={<RequireRole roles={['warehouse', 'owner', 'administrator', 'production_manager']} />}>
            <Route path="/warehouse" element={<WarehouseDashboard />} />
            <Route path="/warehouse/finished-goods" element={<FinishedGoodsPage />} />
            <Route path="/warehouse/reconciliations" element={<ReconciliationsPage />} />
            <Route path="/warehouse/mana-shipments" element={<ManaShipmentsPage />} />
          </Route>
          <Route element={<RequireRole roles={['sorter_packer', 'owner', 'administrator', 'production_manager']} />}>
            <Route path="/packing" element={<SorterPackerDashboard />} />
          </Route>
          <Route element={<RequireRole roles={['purchaser', 'owner', 'administrator', 'production_manager']} />}>
            <Route path="/purchaser" element={<PurchaserDashboard />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ErrorBoundary>
  );
}
