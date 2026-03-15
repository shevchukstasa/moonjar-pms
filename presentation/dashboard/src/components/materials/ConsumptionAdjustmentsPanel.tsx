import { useState } from 'react';
import { CheckCircle, XCircle, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import {
  useConsumptionAdjustments,
  useApproveAdjustment,
  useRejectAdjustment,
} from '@/hooks/useMaterials';
import type { ConsumptionAdjustmentItem } from '@/api/materials';

interface Props {
  factoryId?: string | null;
}

function formatShape(shape: string | null): string {
  if (!shape) return '-';
  return shape.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function varianceColor(pct: number | null): string {
  if (pct === null) return 'text-gray-500';
  if (Math.abs(pct) <= 5) return 'text-green-600';
  if (Math.abs(pct) <= 15) return 'text-yellow-600';
  return 'text-red-600';
}

function VarianceIcon({ pct }: { pct: number | null }) {
  if (pct === null) return null;
  if (pct > 0) return <TrendingUp className="h-4 w-4 text-red-500 inline" />;
  if (pct < 0) return <TrendingDown className="h-4 w-4 text-blue-500 inline" />;
  return null;
}

export function ConsumptionAdjustmentsPanel({ factoryId }: Props) {
  const params = factoryId
    ? { factory_id: factoryId, status: 'pending' }
    : { status: 'pending' };
  const { data, isLoading, isError } = useConsumptionAdjustments(params);
  const items: ConsumptionAdjustmentItem[] = data?.items ?? [];

  const approve = useApproveAdjustment();
  const reject = useRejectAdjustment();

  const [confirmApprove, setConfirmApprove] = useState<ConsumptionAdjustmentItem | null>(null);
  const [confirmReject, setConfirmReject] = useState<ConsumptionAdjustmentItem | null>(null);

  if (isLoading) {
    return (
      <div className="flex justify-center py-6">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 text-red-600 py-4">
        <AlertTriangle className="h-5 w-5" />
        <span>Failed to load consumption adjustments</span>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-gray-400 text-sm py-4 text-center">
        No pending consumption adjustments
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle className="h-5 w-5 text-amber-500" />
        <h3 className="font-medium text-sm text-gray-700">
          Consumption Adjustments ({items.length} pending)
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-100">
              <th className="pb-2 font-medium">Order / Position</th>
              <th className="pb-2 font-medium">Material</th>
              <th className="pb-2 font-medium">Shape</th>
              <th className="pb-2 font-medium text-right">Expected</th>
              <th className="pb-2 font-medium text-right">Actual</th>
              <th className="pb-2 font-medium text-right">Variance</th>
              <th className="pb-2 font-medium text-right">Suggested Coeff.</th>
              <th className="pb-2 font-medium text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((adj) => (
              <tr key={adj.id} className="border-b border-gray-50 hover:bg-gray-25">
                <td className="py-2">
                  <div className="font-medium text-gray-900">
                    {adj.order_number || '-'}
                  </div>
                  <div className="text-xs text-gray-400">
                    Pos. #{adj.position_number || '-'}
                  </div>
                </td>
                <td className="py-2 text-gray-700">
                  {adj.material_name || '-'}
                </td>
                <td className="py-2">
                  <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                    {formatShape(adj.shape)}
                  </span>
                  {adj.product_type && (
                    <span className="text-xs text-gray-400 ml-1">
                      / {formatShape(adj.product_type)}
                    </span>
                  )}
                </td>
                <td className="py-2 text-right font-mono text-gray-600">
                  {adj.expected_qty.toFixed(2)}
                </td>
                <td className="py-2 text-right font-mono text-gray-900 font-medium">
                  {adj.actual_qty.toFixed(2)}
                </td>
                <td className={`py-2 text-right font-mono font-medium ${varianceColor(adj.variance_pct)}`}>
                  <VarianceIcon pct={adj.variance_pct} />{' '}
                  {adj.variance_pct !== null ? `${adj.variance_pct > 0 ? '+' : ''}${adj.variance_pct.toFixed(1)}%` : '-'}
                </td>
                <td className="py-2 text-right font-mono text-blue-600">
                  {adj.suggested_coefficient !== null ? adj.suggested_coefficient.toFixed(3) : '-'}
                </td>
                <td className="py-2">
                  <div className="flex items-center justify-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-green-600 hover:bg-green-50 h-7 px-2"
                      onClick={() => setConfirmApprove(adj)}
                      disabled={approve.isPending || reject.isPending}
                    >
                      <CheckCircle className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-600 hover:bg-red-50 h-7 px-2"
                      onClick={() => setConfirmReject(adj)}
                      disabled={approve.isPending || reject.isPending}
                    >
                      <XCircle className="h-4 w-4" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Approve Confirm Dialog */}
      {confirmApprove && (
        <ConfirmDialog
          open
          title="Approve Consumption Adjustment"
          message={
            `Approve adjustment for ${confirmApprove.material_name}? ` +
            (confirmApprove.suggested_coefficient
              ? `Shape coefficient for ${formatShape(confirmApprove.shape)}/${formatShape(confirmApprove.product_type)} will be updated to ${confirmApprove.suggested_coefficient.toFixed(3)}.`
              : 'No coefficient change will be applied.')
          }
          onConfirm={() => {
            approve.mutate(
              { id: confirmApprove.id },
              { onSettled: () => setConfirmApprove(null) },
            );
          }}
          onClose={() => setConfirmApprove(null)}
        />
      )}

      {/* Reject Confirm Dialog */}
      {confirmReject && (
        <ConfirmDialog
          open
          title="Reject Consumption Adjustment"
          message={`Reject adjustment for ${confirmReject.material_name}? The current coefficient will remain unchanged.`}
          onConfirm={() => {
            reject.mutate(
              { id: confirmReject.id },
              { onSettled: () => setConfirmReject(null) },
            );
          }}
          onClose={() => setConfirmReject(null)}
        />
      )}
    </div>
  );
}
