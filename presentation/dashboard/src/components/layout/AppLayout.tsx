import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useUiStore } from '@/stores/uiStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { cn } from '@/lib/cn';

export default function AppLayout({ children }: { children: ReactNode }) {
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  useWebSocket();
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-stone-950">
      <Sidebar />
      <div className={cn('flex flex-1 flex-col overflow-hidden transition-all', sidebarOpen ? 'ml-56' : 'ml-14')}>
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
