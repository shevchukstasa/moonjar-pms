import { useState, useMemo } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { positionsApi } from '@/api/positions';
import { Button } from '@/components/ui/Button';
import type { PositionItem } from './PositionRow';

interface SplitPart {
  quantity: number | '';
  reason: string;
}

interface ProductionSplitModalProps {
  position: PositionItem | null;
  onClose: () => void;
}

export function ProductionSplitModal({ position, onClose }: ProductionSplitModalProps) {
  const queryClient = useQueryClient();
  const [parts, setParts] = useState<SplitPart[]>([
    { quantity: '', reason: '' },
    { quantity: '', reason: '' },
  ]);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const splitMutation = useMutation({
    mutationFn: (data: { parts: { quantity: number; reason: string }[] }) =>
      positionsApi.splitProduction(position!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule'] });
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      setSuccessMsg('Split completed successfully');
      setTimeout(() => {
        onClose();
      }, 1200);
    },
  });

  const totalAssigned = useMemo(
    () => parts.reduce((sum, p) => sum + (typeof p.quantity === 'number' ? p.quantity : 0), 0),
    [parts],
  );

  if (!position) return null;

  const originalQty = position.quantity;
  const remaining = originalQty - totalAssigned;
  const isValid = totalAssigned === originalQty && parts.every((p) => typeof p.quantity === 'number' && p.quantity > 0);

  const updatePart = (index: number, field: keyof SplitPart, value: string | number) => {
    setParts((prev) => prev.map((p, i) => (i === index ? { ...p, [field]: value } : p)));
  };

  const addPart = () => {
    setParts((prev) => [...prev, { quantity: '', reason: '' }]);
  };

  const removePart = (index: number) => {
    if (parts.length <= 2) return;
    setParts((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = () => {
    if (!isValid) return;
    const payload = {
      parts: parts.map((p) => ({
        quantity: typeof p.quantity === 'number' ? p.quantity : 0,
        reason: p.reason,
      })),
    };
    splitMutation.mutate(payload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Split Production</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>

        {/* Position info */}
        <div className="mb-4 rounded-md bg-gray-50 p-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-gray-900">{position.order_number}</span>
            <span className="text-gray-500">{position.size}</span>
          </div>
          <div className="mt-1 flex items-center justify-between text-sm text-gray-600">
            <span>{position.color}</span>
            <span className="font-semibold">Qty: {originalQty}</span>
          </div>
          <div className="mt-1 text-xs text-gray-400">Status: {position.status}</div>
        </div>

        {/* Success message */}
        {successMsg && (
          <div className="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
            {successMsg}
          </div>
        )}

        {/* Parts list */}
        <div className="space-y-3 mb-4">
          {parts.map((part, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <div className="flex-shrink-0 w-8 pt-2 text-xs font-medium text-gray-500">
                #{idx + 1}
              </div>
              <div className="flex-1 space-y-1">
                <input
                  type="number"
                  min={1}
                  max={originalQty}
                  value={part.quantity}
                  onChange={(e) => {
                    const val = e.target.value === '' ? '' : parseInt(e.target.value, 10);
                    updatePart(idx, 'quantity', val as number);
                  }}
                  placeholder="Quantity"
                  className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <input
                  type="text"
                  value={part.reason}
                  onChange={(e) => updatePart(idx, 'reason', e.target.value)}
                  placeholder="Reason (optional)"
                  className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              {parts.length > 2 && (
                <button
                  onClick={() => removePart(idx)}
                  className="mt-1 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
                  title="Remove part"
                >
                  &times;
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Add part button */}
        <button
          onClick={addPart}
          className="mb-4 text-sm text-blue-600 hover:text-blue-800"
        >
          + Add another part
        </button>

        {/* Remaining quantity indicator */}
        <div className={`mb-4 rounded-md p-2 text-sm text-center font-medium ${remaining === 0 ? 'bg-green-50 text-green-700' : remaining > 0 ? 'bg-yellow-50 text-yellow-700' : 'bg-red-50 text-red-700'}`}>
          {remaining === 0
            ? 'All quantity assigned'
            : remaining > 0
              ? `${remaining} remaining to assign`
              : `${Math.abs(remaining)} over-assigned`}
        </div>

        {/* Error */}
        {splitMutation.isError && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {(splitMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Split failed. Please try again.'}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            disabled={!isValid || splitMutation.isPending}
          >
            {splitMutation.isPending ? 'Splitting...' : 'Split'}
          </Button>
        </div>
      </div>
    </div>
  );
}
