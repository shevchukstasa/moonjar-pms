import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { useForceUnblock } from '@/hooks/usePositions';

interface ForceUnblockDialogProps {
  positionId: string;
  positionLabel: string;
  currentStatus: string;
  onClose: () => void;
}

const STATUS_LABELS: Record<string, string> = {
  insufficient_materials: 'Insufficient Materials',
  awaiting_recipe: 'Awaiting Recipe',
  awaiting_stencil_silkscreen: 'Awaiting Stencil/Silkscreen',
  awaiting_color_matching: 'Awaiting Color Matching',
  blocked_by_qm: 'Blocked by QM',
};

export function ForceUnblockDialog({ positionId, positionLabel, currentStatus, onClose }: ForceUnblockDialogProps) {
  const [notes, setNotes] = useState('');
  const forceUnblock = useForceUnblock();

  const handleSubmit = () => {
    if (!notes.trim()) return;
    forceUnblock.mutate(
      { id: positionId, notes: notes.trim() },
      {
        onSuccess: (data) => {
          if (data.negative_balances && data.negative_balances.length > 0) {
            alert(
              `⚠ Force-unblocked! ${data.negative_balances.length} material(s) went to negative balance.\n\n` +
              data.negative_balances.map(
                (nb: { material_name: string; resulting_effective: number }) =>
                  `• ${nb.material_name}: effective balance = ${nb.resulting_effective.toFixed(2)}`
              ).join('\n') +
              '\n\nAdjust during next inventory count.'
            );
          }
          onClose();
        },
      }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-gray-900">Force Unblock Position</h3>
        <p className="mt-1 text-sm text-gray-500">
          Position <strong>{positionLabel}</strong> is blocked:{' '}
          <span className="font-medium text-orange-600">{STATUS_LABELS[currentStatus] || currentStatus}</span>
        </p>

        {currentStatus === 'insufficient_materials' && (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            ⚠ Materials will be force-reserved even if stock is insufficient.
            Balance may go negative — correct during inventory.
          </div>
        )}

        {currentStatus === 'awaiting_recipe' && (
          <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800">
            Position will proceed to production without a recipe. PM takes responsibility.
          </div>
        )}

        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Reason (required for audit) <span className="text-red-500">*</span>
          </label>
          <textarea
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            rows={3}
            placeholder="Why are you unblocking this position?..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            autoFocus
          />
        </div>

        <div className="mt-5 flex justify-end gap-3">
          <Button variant="secondary" size="sm" onClick={onClose} disabled={forceUnblock.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSubmit}
            disabled={!notes.trim() || forceUnblock.isPending}
          >
            {forceUnblock.isPending ? 'Unblocking…' : 'Force Unblock →'}
          </Button>
        </div>

        {forceUnblock.isError && (
          <p className="mt-3 text-sm text-red-600">
            Error: {(forceUnblock.error as Error)?.message || 'Failed to unblock'}
          </p>
        )}
      </div>
    </div>
  );
}
