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
import AdminColorsPage from '@/pages/AdminColorsPage';
import AdminAppTypesPage from '@/pages/AdminAppTypesPage';
import AdminPoaPage from '@/pages/AdminPoaPage';
import AdminFinishingPage from '@/pages/AdminFinishingPage';
import AdminTemperatureGroupsPage from '@/pages/AdminTemperatureGroupsPage';
import AdminMaterialsPage from '@/pages/AdminMaterialsPage';
import AdminWarehousesPage from '@/pages/AdminWarehousesPage';
import SettingsPage from '@/pages/SettingsPage';
import AppLayout from '@/components/layout/AppLayout';
import { Spinner } from '@/components/ui/Spinner';

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
  return <AppLayout><Outlet /></AppLayout>;
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
    return <div className="flex min-h-screen items-center justify-center"><Spinner className="h-10 w-10" /></div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<RoleRedirect />} />
        <Route element={<RequireRole roles={['owner']} />}>
          <Route path="/owner" element={<OwnerDashboard />} />
        </Route>
        <Route element={<RequireRole roles={['ceo', 'owner', 'administrator']} />}>
          <Route path="/ceo" element={<CeoDashboard />} />
        </Route>
        <Route element={<RequireRole roles={['owner', 'administrator']} />}>
          <Route path="/admin" element={<AdminPanelPage />} />
          <Route path="/admin/recipes" element={<AdminRecipesPage />} />
          <Route path="/admin/suppliers" element={<AdminSuppliersPage />} />
          <Route path="/admin/collections" element={<AdminCollectionsPage />} />
          <Route path="/admin/colors" element={<AdminColorsPage />} />
          <Route path="/admin/application-types" element={<AdminAppTypesPage />} />
          <Route path="/admin/places-of-application" element={<AdminPoaPage />} />
          <Route path="/admin/finishing-types" element={<AdminFinishingPage />} />
          <Route path="/admin/temperature-groups" element={<AdminTemperatureGroupsPage />} />
          <Route path="/admin/materials" element={<AdminMaterialsPage />} />
          <Route path="/admin/warehouses" element={<AdminWarehousesPage />} />
        </Route>
        <Route element={<RequireRole roles={['owner', 'administrator', 'ceo']} />}>
          <Route path="/users" element={<UsersPage />} />
        </Route>
        <Route element={<RequireRole roles={['production_manager', 'owner', 'administrator']} />}>
          <Route path="/manager" element={<ManagerDashboard />} />
          <Route path="/manager/orders/:orderId" element={<OrderDetailPage />} />
          <Route path="/manager/schedule" element={<ManagerSchedulePage />} />
          <Route path="/manager/kilns" element={<ManagerKilnsPage />} />
          <Route path="/manager/materials" element={<ManagerMaterialsPage />} />
          <Route path="/manager/shortage/:taskId" element={<ShortageDecisionPage />} />
        </Route>
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/tablo" element={<TabloDashboard />} />
        <Route element={<RequireRole roles={['quality_manager', 'owner', 'administrator']} />}>
          <Route path="/quality" element={<QualityManagerDashboard />} />
        </Route>
        <Route element={<RequireRole roles={['warehouse', 'owner', 'administrator', 'production_manager']} />}>
          <Route path="/warehouse" element={<WarehouseDashboard />} />
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
  );
}
