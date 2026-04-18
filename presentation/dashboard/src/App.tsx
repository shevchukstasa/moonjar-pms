import { useState, useEffect, lazy, Suspense } from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { roleRoutes } from '@/lib/roleRoutes';
import apiClient from '@/api/client';
import LoginPage from '@/pages/LoginPage';
import NotFoundPage from '@/pages/NotFoundPage';
import AppLayout from '@/components/layout/AppLayout';
import { Spinner } from '@/components/ui/Spinner';
import { ErrorBoundary, PageErrorFallback } from '@/components/ErrorBoundary';

// ── Lazy-loaded pages ─────────────────────────────────────────
// Each page becomes a separate JS chunk, loaded only when navigated to.

// Role dashboards
const OwnerDashboard = lazy(() => import('@/pages/OwnerDashboard'));
const CeoDashboard = lazy(() => import('@/pages/CeoDashboard'));
const ManagerDashboard = lazy(() => import('@/pages/ManagerDashboard'));
const QualityManagerDashboard = lazy(() => import('@/pages/QualityManagerDashboard'));
const WarehouseDashboard = lazy(() => import('@/pages/WarehouseDashboard'));
const SorterPackerDashboard = lazy(() => import('@/pages/SorterPackerDashboard'));
const PurchaserDashboard = lazy(() => import('@/pages/PurchaserDashboard'));
const TabloDashboard = lazy(() => import('@/pages/TabloDashboard'));

// Manager pages
const OrderDetailPage = lazy(() => import('@/pages/OrderDetailPage'));
const ManagerSchedulePage = lazy(() => import('@/pages/ManagerSchedulePage'));
const ManagerKilnsPage = lazy(() => import('@/pages/ManagerKilnsPage'));
const ManagerMaterialsPage = lazy(() => import('@/pages/ManagerMaterialsPage'));
const ShortageDecisionPage = lazy(() => import('@/pages/ShortageDecisionPage'));
const SizeResolutionPage = lazy(() => import('@/pages/SizeResolutionPage'));
const ShipmentPage = lazy(() => import('@/pages/ShipmentPage'));
const WorkforceAssignmentPage = lazy(() => import('@/pages/WorkforceAssignmentPage'));
const GamificationPage = lazy(() => import('@/pages/GamificationPage'));

// Admin pages
const AdminPanelPage = lazy(() => import('@/pages/AdminPanelPage'));
const AdminRecipesPage = lazy(() => import('@/pages/AdminRecipesPage'));
const AdminSuppliersPage = lazy(() => import('@/pages/AdminSuppliersPage'));
const AdminCollectionsPage = lazy(() => import('@/pages/AdminCollectionsPage'));
const AdminColorCollectionsPage = lazy(() => import('@/pages/AdminColorCollectionsPage'));
const AdminColorsPage = lazy(() => import('@/pages/AdminColorsPage'));
const AdminAppTypesPage = lazy(() => import('@/pages/AdminAppTypesPage'));
const AdminPoaPage = lazy(() => import('@/pages/AdminPoaPage'));
const AdminFinishingPage = lazy(() => import('@/pages/AdminFinishingPage'));
const AdminTemperatureGroupsPage = lazy(() => import('@/pages/AdminTemperatureGroupsPage'));
const AdminMaterialsPage = lazy(() => import('@/pages/AdminMaterialsPage'));
const AdminWarehousesPage = lazy(() => import('@/pages/AdminWarehousesPage'));
const AdminPackagingPage = lazy(() => import('@/pages/AdminPackagingPage'));
const AdminSizesPage = lazy(() => import('@/pages/AdminSizesPage'));
const AdminDesignsPage = lazy(() => import('@/pages/AdminDesignsPage'));
const AdminFiringProfilesPage = lazy(() => import('@/pages/AdminFiringProfilesPage'));
const AdminStagesPage = lazy(() => import('@/pages/AdminStagesPage'));
const AdminSettingsPage = lazy(() => import('@/pages/AdminSettingsPage'));
const DashboardAccessPage = lazy(() => import('@/pages/DashboardAccessPage'));

// CEO pages
const CeoEmployeesPage = lazy(() => import('@/pages/CeoEmployeesPage'));

// Shared pages
const UsersPage = lazy(() => import('@/pages/UsersPage'));
const SettingsPage = lazy(() => import('@/pages/SettingsPage'));
const EmployeesPage = lazy(() => import('@/pages/EmployeesPage'));
const ReportsPage = lazy(() => import('@/pages/ReportsPage'));
const PMGuidePage = lazy(() => import('@/pages/PMGuidePage'));
const OnboardingPage = lazy(() => import('@/pages/OnboardingPage'));

// Production-specific pages
const TpsDashboardPage = lazy(() => import('@/pages/TpsDashboardPage'));
const KilnFiringSchedulesPage = lazy(() => import('@/pages/KilnFiringSchedulesPage'));
const FactoryCalendarPage = lazy(() => import('@/pages/FactoryCalendarPage'));
const ConsumptionRulesPage = lazy(() => import('@/pages/ConsumptionRulesPage'));
const KilnInspectionsPage = lazy(() => import('@/pages/KilnInspectionsPage'));
const KilnMaintenancePage = lazy(() => import('@/pages/KilnMaintenancePage'));
const GrindingDecisionsPage = lazy(() => import('@/pages/GrindingDecisionsPage'));

// Warehouse pages
const FinishedGoodsPage = lazy(() => import('@/pages/FinishedGoodsPage'));
const ReconciliationsPage = lazy(() => import('@/pages/ReconciliationsPage'));
const ManaShipmentsPage = lazy(() => import('@/pages/ManaShipmentsPage'));

// ── Page loading fallback ─────────────────────────────────────
function PageLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Spinner className="h-8 w-8" />
    </div>
  );
}

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
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
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
            <Route path="/ceo/guide" element={<PMGuidePage role="ceo" />} />
            <Route path="/ceo/onboarding" element={<OnboardingPage role="ceo" />} />
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
            {/* moved below — purchaser needs access */}
            <Route path="/admin/size-resolution/:taskId" element={<SizeResolutionPage />} />
            <Route path="/admin/dashboard-access" element={<DashboardAccessPage />} />
            <Route path="/admin/settings" element={<AdminSettingsPage />} />
            <Route path="/admin/employees" element={<EmployeesPage />} />
            <Route path="/admin/guide" element={<PMGuidePage role="administrator" />} />
            <Route path="/admin/onboarding" element={<OnboardingPage role="administrator" />} />
          </Route>
          <Route element={<RequireRole roles={['owner', 'administrator', 'production_manager']} />}>
            <Route path="/admin/recipes" element={<AdminRecipesPage />} />
            <Route path="/admin/temperature-groups" element={<AdminTemperatureGroupsPage />} />
            <Route path="/admin/warehouses" element={<AdminWarehousesPage />} />
            <Route path="/admin/packaging" element={<AdminPackagingPage />} />
            <Route path="/admin/sizes" element={<AdminSizesPage />} />
            <Route path="/admin/designs" element={<AdminDesignsPage />} />
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
          {/* Materials pages — shared by owner, admin, PM, and purchaser.
              Purchaser owns incoming stock per §29 and needs the catalog +
              scan dialog to create/match stone materials on delivery. */}
          <Route element={<RequireRole roles={['owner', 'administrator', 'production_manager', 'purchaser']} />}>
            <Route path="/admin/materials" element={<AdminMaterialsPage />} />
            <Route path="/manager/materials" element={<ManagerMaterialsPage />} />
          </Route>
          <Route element={<RequireRole roles={['production_manager', 'owner', 'administrator']} />}>
            <Route path="/manager" element={<ManagerDashboard />} />
            <Route path="/manager/orders/:orderId" element={<OrderDetailPage />} />
            <Route path="/manager/orders/:orderId/shipment" element={<ShipmentPage />} />
            <Route path="/manager/schedule" element={<ManagerSchedulePage />} />
            <Route path="/manager/kilns" element={<ManagerKilnsPage />} />
            {/* moved below — purchaser needs access */}
            <Route path="/manager/kiln-inspections" element={<KilnInspectionsPage />} />
            <Route path="/manager/kiln-maintenance" element={<KilnMaintenancePage />} />
            <Route path="/manager/grinding" element={<GrindingDecisionsPage />} />
            <Route path="/manager/shortage/:taskId" element={<ShortageDecisionPage />} />
            <Route path="/manager/size-resolution/:taskId" element={<SizeResolutionPage />} />
            <Route path="/manager/guide" element={<PMGuidePage role="production_manager" />} />
            <Route path="/manager/onboarding" element={<OnboardingPage role="production_manager" />} />
            <Route path="/manager/staff" element={<EmployeesPage />} />
            <Route path="/manager/workforce" element={<WorkforceAssignmentPage />} />
          </Route>
          <Route element={<RequireRole roles={['owner', 'ceo', 'production_manager', 'administrator']} />}>
            <Route path="/manager/gamification" element={<GamificationPage />} />
          </Route>
          <Route element={<RequireRole roles={['owner', 'ceo', 'production_manager']} />}>
            <Route path="/reports" element={<ReportsPage />} />
          </Route>
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/tablo" element={<TabloDashboard />} />
          <Route element={<RequireRole roles={['quality_manager', 'owner', 'administrator', 'production_manager']} />}>
            <Route path="/quality" element={<QualityManagerDashboard />} />
            <Route path="/quality/guide" element={<PMGuidePage role="quality_manager" />} />
            <Route path="/quality/onboarding" element={<OnboardingPage role="quality_manager" />} />
          </Route>
          <Route element={<RequireRole roles={['warehouse', 'owner', 'administrator', 'production_manager']} />}>
            <Route path="/warehouse" element={<WarehouseDashboard />} />
            <Route path="/warehouse/finished-goods" element={<FinishedGoodsPage />} />
            <Route path="/warehouse/reconciliations" element={<ReconciliationsPage />} />
            <Route path="/warehouse/mana-shipments" element={<ManaShipmentsPage />} />
            <Route path="/warehouse/guide" element={<PMGuidePage role="warehouse" />} />
            <Route path="/warehouse/onboarding" element={<OnboardingPage role="warehouse" />} />
          </Route>
          <Route element={<RequireRole roles={['sorter_packer', 'owner', 'administrator', 'production_manager']} />}>
            <Route path="/packing" element={<SorterPackerDashboard />} />
            <Route path="/packing/guide" element={<PMGuidePage role="sorter_packer" />} />
            <Route path="/packing/onboarding" element={<OnboardingPage role="sorter_packer" />} />
          </Route>
          <Route element={<RequireRole roles={['purchaser', 'owner', 'administrator', 'production_manager']} />}>
            <Route path="/purchaser" element={<PurchaserDashboard />} />
            <Route path="/purchaser/guide" element={<PMGuidePage role="purchaser" />} />
            <Route path="/purchaser/onboarding" element={<OnboardingPage role="purchaser" />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ErrorBoundary>
  );
}
