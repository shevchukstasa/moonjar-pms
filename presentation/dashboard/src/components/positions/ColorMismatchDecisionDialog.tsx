/**
 * ColorMismatchDecisionDialog — PM resolution for color-mismatch sub-positions.
 *
 * After sorting, tiles flagged as color_mismatch wait in PLANNED state.
 * PM splits the batch into up to 3 paths:
 *   • Refire only  — already glazed, just needs another kiln pass (bubbles / wrong tone)
 *   • Reglaze + refire — needs full re-glazing then re-firing
 *   • To stock     — shade acceptable for stock / alternate use
 *
 * The three quantities must sum to the position's total quantity.
 */

import { useState, useEffect } from 'react';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { useResolveColorMismatch } from '@/hooks/usePositions';
import type { PositionItem } from '@/hooks/usePositions';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ColorMismatchDecisionDialogProps {
  open: boolean;
  onClose: () => void;
  position: PositionItem | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ColorMismatchDecisionDialog({
  open,
  onClose,
  position,
}: ColorMismatchDecisionDialogProps) {
  const total = position?.quantity ?? 0;

  const [refireQty, setRefireQty] = useState(0);
  const [reglazeQty, setReglazeQty] = useState(0);
  const [stockQty, setStockQty] = useState(0);
  const [notes, setNotes] = useState('');

  // Reset form whenever the position changes
  useEffect(() => {
    if (position) {
      setRefireQty(0);
      setReglazeQty(0);
      setStockQty(total);
      setNotes('');
    }
  }, [position, total]);

  const allocated = refireQty + reglazeQty + stockQty;
  const remaining = total - allocated;
  const isValid = allocated === total && total > 0;

  const resolve = useResolveColorMismatch();

  function handleSubmit() {
    if (!position || !isValid) return;
    resolve.mutate(
      {
        id: position.id,
        data: {
          refire_qty: refireQty,
          reglaze_qty: reglazeQty,
          stock_qty: stockQty,
          notes: notes.trim() || undefined,
        },
      },
      { onSuccess: onClose },
    );
  }

  // Convenience: auto-fill remaining into a field
  function fillRemaining(field: 'refire' | 'reglaze' | 'stock') {
    if (remaining <= 0) return;
    if (field === 'refire') setRefireQty((v) => v + remaining);
    if (field === 'reglaze') setReglazeQty((v) => v + remaining);
    if (field === 'stock') setStockQty((v) => v + remaining);
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Resolve Color Mismatch"
      className="w-full max-w-lg"
    >
      {position && (
        <div className="space-y-5">
          {/* Position summary */}
          <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm">
            <div className="flex items-center gap-2 text-amber-800 font-medium mb-1">
              <span>🎨</span>
              <span>Color Mismatch — PM Decision Required</span>
            </div>
            <div className="text-gray-600 grid grid-cols-2 gap-x-4 gap-y-0.5 mt-1">
              <span>Order:</span>
              <span className="font-medium">{position.order_number}</span>
              <span>Color / Size:</span>
              <span className="font-medium">{position.color} {position.size}</span>
              {position.application && (
                <>
                  <span>Application:</span>
                  <span className="font-medium">{position.application}</span>
                </>
              )}
              {position.collection && (
                <>
                  <span>Collection:</span>
                  <span className="font-medium">{position.collection}</span>
                </>
              )}
              <span>Total quantity:</span>
              <span className="font-bold text-gray-900">{total} pcs</span>
            </div>
          </div>

          {/* Allocation inputs */}
          <div className="space-y-3">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
              Distribute {total} pcs across paths:
            </p>

            {/* Path 1 — Refire only */}
            <div className="rounded-lg border border-orange-200 bg-orange-50 p-3">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm font-medium text-orange-800">🔥 Refire only</p>
                  <p className="text-xs text-orange-600">Already glazed — another kiln pass only</p>
                </div>
                <button
                  type="button"
                  className="text-xs text-orange-600 underline"
                  onClick={() => fillRemaining('refire')}
                >
                  +{remaining}
                </button>
              </div>
              <input
                type="number"
                min={0}
                max={total}
                value={refireQty}
                onChange={(e) => setRefireQty(Math.max(0, parseInt(e.target.value) || 0))}
                className="w-full rounded border border-orange-300 bg-white px-3 py-1.5 text-sm text-right focus:outline-none focus:ring-2 focus:ring-orange-400"
              />
            </div>

            {/* Path 2 — Reglaze + refire */}
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm font-medium text-blue-800">🖌 Reglaze + Refire</p>
                  <p className="text-xs text-blue-600">Needs full re-glazing before another firing</p>
                </div>
                <button
                  type="button"
                  className="text-xs text-blue-600 underline"
                  onClick={() => fillRemaining('reglaze')}
                >
                  +{remaining}
                </button>
              </div>
              <input
                type="number"
                min={0}
                max={total}
                value={reglazeQty}
                onChange={(e) => setReglazeQty(Math.max(0, parseInt(e.target.value) || 0))}
                className="w-full rounded border border-blue-300 bg-white px-3 py-1.5 text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>

            {/* Path 3 — To stock */}
            <div className="rounded-lg border border-green-200 bg-green-50 p-3">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm font-medium text-green-800">📦 To Stock</p>
                  <p className="text-xs text-green-600">Shade acceptable — pack for stock / alternate use</p>
                </div>
                <button
                  type="button"
                  className="text-xs text-green-600 underline"
                  onClick={() => fillRemaining('stock')}
                >
                  +{remaining}
                </button>
              </div>
              <input
                type="number"
                min={0}
                max={total}
                value={stockQty}
                onChange={(e) => setStockQty(Math.max(0, parseInt(e.target.value) || 0))}
                className="w-full rounded border border-green-300 bg-white px-3 py-1.5 text-sm text-right focus:outline-none focus:ring-2 focus:ring-green-400"
              />
            </div>
          </div>

          {/* Allocation summary bar */}
          <div className={`rounded-lg px-3 py-2 text-sm font-medium flex items-center justify-between ${
            isValid
              ? 'bg-green-50 border border-green-300 text-green-800'
              : 'bg-red-50 border border-red-300 text-red-700'
          }`}>
            <span>Allocated: {allocated} / {total} pcs</span>
            {!isValid && remaining !== 0 && (
              <span className="text-xs">
                {remaining > 0 ? `${remaining} pcs unassigned` : `${Math.abs(remaining)} pcs over total`}
              </span>
            )}
            {isValid && <span className="text-xs">✓ Ready to submit</span>}
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes (optional)</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reason for decision, batch details..."
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-1">
            <Button variant="ghost" onClick={onClose} disabled={resolve.isPending}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSubmit}
              disabled={!isValid || resolve.isPending}
            >
              {resolve.isPending ? 'Submitting…' : 'Confirm Decision'}
            </Button>
          </div>

          {resolve.isError && (
            <p className="text-sm text-red-600 text-center">
              Failed to submit. Check quantities and try again.
            </p>
          )}
        </div>
      )}
    </Dialog>
  );
}
