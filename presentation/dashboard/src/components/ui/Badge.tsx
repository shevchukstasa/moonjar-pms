import { cn } from '@/lib/cn';
import { getStatusColor } from '@/lib/statusColors';
import { formatStatus } from '@/components/tablo/StatusDropdown';

export function Badge({ status, label, className }: { status: string; label?: string; className?: string }) {
  return <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize', getStatusColor(status), className)}>{label || formatStatus(status)}</span>;
}
