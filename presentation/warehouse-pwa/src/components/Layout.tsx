import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

const NAV_ITEMS = [
  { to: '/scan', label: 'Pindai', icon: ScanIcon },
  { to: '/receive', label: 'Terima', icon: ReceiveIcon },
  { to: '/inventory', label: 'Stok', icon: InventoryIcon },
] as const;

export function Layout() {
  const { user, logout, selectedFactoryId, setFactory } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const factoryName =
    user?.factories?.find((f) => f.id === selectedFactoryId)?.name ?? 'Gudang';

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-3 bg-primary-600 text-white shadow-md flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          {user?.factories && user.factories.length > 1 ? (
            <select
              className="bg-primary-700 text-white text-sm font-semibold rounded px-2 py-1 border-none outline-none touch-target truncate max-w-[160px]"
              value={selectedFactoryId ?? ''}
              onChange={(e) => setFactory(e.target.value)}
            >
              {user.factories.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-sm font-semibold truncate max-w-[160px]">
              {factoryName}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs opacity-80 truncate max-w-[100px]">
            {user?.name}
          </span>
          <button
            onClick={handleLogout}
            className="touch-target flex items-center justify-center rounded-full bg-primary-700 hover:bg-primary-800 w-9 h-9"
            aria-label="Keluar"
          >
            <LogoutIcon />
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>

      {/* Bottom navigation */}
      <nav className="flex items-center justify-around bg-white border-t border-gray-200 flex-shrink-0 pb-safe">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center py-2 px-4 touch-target transition-colors ${
                isActive
                  ? 'text-primary-600 font-semibold'
                  : 'text-gray-400 hover:text-gray-600'
              }`
            }
          >
            <Icon />
            <span className="text-[11px] mt-0.5">{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

/* ----- Icons (inline SVG for zero dependencies) ----- */

function ScanIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7V5a2 2 0 0 1 2-2h2" />
      <path d="M17 3h2a2 2 0 0 1 2 2v2" />
      <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
      <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
      <line x1="7" y1="12" x2="17" y2="12" />
    </svg>
  );
}

function ReceiveIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 16V8a2 2 0 0 0-1-1.73L13 2.27a2 2 0 0 0-2 0L4 6.27A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  );
}

function InventoryIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}
