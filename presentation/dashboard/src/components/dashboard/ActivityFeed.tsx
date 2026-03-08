import type { ActivityFeedItem } from '@/api/analytics';
import { Bell, AlertTriangle, Package, Truck, Settings, Clock } from 'lucide-react';
import { cn } from '@/lib/cn';

interface ActivityFeedProps {
  items: ActivityFeedItem[];
  className?: string;
}

const typeIcons: Record<string, React.ReactNode> = {
  alert: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
  status_change: <Settings className="h-4 w-4 text-blue-500" />,
  material_received: <Package className="h-4 w-4 text-green-500" />,
  ready_for_shipment: <Truck className="h-4 w-4 text-purple-500" />,
  stock_shortage: <AlertTriangle className="h-4 w-4 text-red-500" />,
  reconciliation_discrepancy: <AlertTriangle className="h-4 w-4 text-orange-500" />,
};

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function ActivityFeed({ items, className }: ActivityFeedProps) {
  if (!items.length) {
    return <p className="py-8 text-center text-sm text-gray-500">No recent activity</p>;
  }

  return (
    <div className={cn('space-y-1 overflow-y-auto', className)} style={{ maxHeight: 400 }}>
      {items.map((item) => (
        <div
          key={item.id}
          className={cn(
            'flex items-start gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-gray-50',
            !item.is_read && 'bg-blue-50/50',
          )}
        >
          <div className="mt-0.5">{typeIcons[item.type] || <Bell className="h-4 w-4 text-gray-400" />}</div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-900 truncate">{item.title}</p>
            {item.message && <p className="text-xs text-gray-500 truncate">{item.message}</p>}
          </div>
          <span className="flex-shrink-0 text-xs text-gray-400 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatTimeAgo(item.created_at)}
          </span>
        </div>
      ))}
    </div>
  );
}
