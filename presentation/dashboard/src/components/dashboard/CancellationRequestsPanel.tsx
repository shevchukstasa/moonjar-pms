import { formatDate } from "@/lib/format";
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, CheckCircle, XCircle, ExternalLink, Clock } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import {
  useCancellationRequests,
  useAcceptCancellation,
  useRejectCancellation,
} from '@/hooks/useOrders';
import type { CancellationRequestItem } from '@/api/orders';

interface Props {
  factoryId?: string | null;
}

function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function statusColor(status: string): string {
  const map: Record<string, string> = {
    new: 'bg-blue-100 text-blue-700',
    in_production: 'bg-yellow-100 text-yellow-700',
    partially_ready: 'bg-orange-100 text-orange-700',
    ready_for_shipment: 'bg-green-100 text-green-700',
    shipped: 'bg-gray-100 text-gray-700',
    cancelled: 'bg-red-100 text-red-700',
  };
  return map[status] ?? 'bg-gray-100 text-gray-600';
}

export function CancellationRequestsPanel({ factoryId }: Props) {
  const params = factoryId ? { factory_id: factoryId, decision: 'pending' } : { decision: 'pending' };
  const { data, isLoading, isError } = useCancellationRequests(params);
  const items: CancellationRequestItem[] = data?.items ?? [];

  const accept = useAcceptCancellation();
  const reject = useRejectCancellation();

  const [confirmAccept, setConfirmAccept] = useState<CancellationRequestItem | null>(null);
  const [confirmReject, setConfirmReject] = useState<CancellationRequestItem | null>(null);

  if (isLoading) {
    return (
      <div className="flex justify-center py-6">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">⚠ Error loading cancellation requests</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-200 p-6 text-center">
        <CheckCircle className="mx-auto mb-2 h-8 w-8 text-gray-300" />
        <p className="text-sm text-gray-400">No pending cancellation requests</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="rounded-lg border border-amber-200 bg-amber-50 p-4"
          >
            {/* Header row */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-500" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-900">{item.order_number}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(item.status)}`}
                    >
                      {item.status.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600">{item.client}</p>
                </div>
              </div>

              {/* Requested time */}
              <div className="flex items-center gap-1 text-xs text-amber-600">
                <Clock className="h-3 w-3" />
                <span>{timeAgo(item.cancellation_requested_at)}</span>
              </div>
            </div>

            {/* Stage info */}
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
              <span>
                <span className="font-medium">Stage:</span> {item.current_stage}
              </span>
              <span>
                <span className="font-medium">Factory:</span> {item.factory_name}
              </span>
              <span>
                <span className="font-medium">Positions:</span>{' '}
                {item.positions_ready}/{item.positions_count} ready
              </span>
              {item.final_deadline && (
                <span>
                  <span className="font-medium">Deadline:</span>{' '}
                  {formatDate(item.final_deadline)}
                </span>
              )}
            </div>

            {/* Actions */}
            <div className="mt-3 flex items-center gap-2">
              <Button
                size="sm"
                className="bg-red-500 hover:bg-red-600 text-white"
                disabled={accept.isPending || reject.isPending}
                onClick={() => setConfirmAccept(item)}
              >
                <CheckCircle className="mr-1 h-3.5 w-3.5" />
                Accept Cancellation
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={accept.isPending || reject.isPending}
                onClick={() => setConfirmReject(item)}
              >
                <XCircle className="mr-1 h-3.5 w-3.5" />
                Reject
              </Button>
              <Link
                to={`/orders/${item.id}`}
                className="ml-auto inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
              >
                View order
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
          </div>
        ))}
      </div>

      {/* Confirm Accept */}
      <ConfirmDialog
        open={!!confirmAccept}
        onClose={() => setConfirmAccept(null)}
        onConfirm={async () => {
          if (confirmAccept) await accept.mutateAsync(confirmAccept.id);
        }}
        title="Accept Cancellation"
        message={`Accept cancellation of order "${confirmAccept?.order_number}"? The order will be marked as CANCELLED and all positions will be cancelled. This cannot be undone.`}
      />

      {/* Confirm Reject */}
      <ConfirmDialog
        open={!!confirmReject}
        onClose={() => setConfirmReject(null)}
        onConfirm={async () => {
          if (confirmReject) await reject.mutateAsync(confirmReject.id);
        }}
        title="Reject Cancellation"
        message={`Reject the cancellation request for order "${confirmReject?.order_number}"? The order will continue in production.`}
      />
    </>
  );
}
