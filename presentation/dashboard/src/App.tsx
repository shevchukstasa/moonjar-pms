import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { roleRoutes } from '@/lib/roleRoutes';
import LoginPage from '@/pages/LoginPage';
import NotFoundPage from '@/pages/NotFoundPage';
import OwnerDashboard from '@/pages/OwnerDashboard';
import CeoDashboard from '@/pages/CeoDashboard';
import ManagerDashboard from '@/pages/ManagerDashboard';
import OrderDetailPage from '@/pages/OrderDetailPage';
import ManagerSchedulePage from '@/pages/ManagerSchedulePage';
import ManagerKilnsPage from '@/pages/ManagerKilnsPage';
import TabloDashboard from '@/pages/TabloDashboard';
import QualityManagerDashboard from '@/pages/QualityManagerDashboard';
import WarehouseDashboard from '@/pages/WarehouseDashboard';
import SorterPackerDashboard from '@/pages/SorterPackerDashboard';
import PurchaserDashboard from '@/pages/PurchaserDashboard';
import UsersPage from '@/pages/UsersPage';
import AdminPanelPage from '@/pages/AdminPanelPage';
import AppLayout from '@/components/layout/AppLayout';

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
        </Route>
        <Route element={<RequireRole roles={['owner', 'administrator', 'ceo']} />}>
          <Route path="/users" element={<UsersPage />} />
        </Route>
        <Route element={<RequireRole roles={['production_manager', 'owner', 'administrator']} />}>
          <Route path="/manager" element={<ManagerDashboard />} />
          <Route path="/manager/orders/:orderId" element={<OrderDetailPage />} />
          <Route path="/manager/schedule" element={<ManagerSchedulePage />} />
          <Route path="/manager/kilns" element={<ManagerKilnsPage />} />
        </Route>
        <Route path="/tablo" element={<TabloDashboard />} />
        <Route element={<RequireRole roles={['quality_manager', 'owner', 'administrator']} />}>
          <Route path="/quality" element={<QualityManagerDashboard />} />
        </Route>
        <Route path="/warehouse" element={<WarehouseDashboard />} />
        <Route path="/packing" element={<SorterPackerDashboard />} />
        <Route path="/purchaser" element={<PurchaserDashboard />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
