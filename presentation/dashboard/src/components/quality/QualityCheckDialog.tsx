import { useState, useMemo } from 'react';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { useChecklistItems, useCreatePreKilnCheck, useCreateFinalCheck } from '@/hooks/useQuality';
import { cn } from '@/lib/cn';

type CheckValue = 'pass' | 'fail' | 'na';

interface QualityCheckDialogProps {
  open: boolean;
  onClose: () => void;
  checkType: 'pre_kiln' | 'final';
  positionId: string;
  factoryId: string;
  /** Optional context displayed at the top */
  positionLabel?: string;
}

const VALUE_COLORS: Record<CheckValue, string> = {
  pass: 'bg-green-100 text-green-800 border-green-300',
  fail: 'bg-red-100 text-red-800 border-red-300',
  na: 'bg-gray-100 text-gray-500 border-gray-300',
};

const VALUE_ACTIVE: Record<CheckValue, string> = {
  pass: 'bg-green-500 text-white border-green-600',
  fail: 'bg-red-500 text-white border-red-600',
  na: 'bg-gray-400 text-white border-gray-500',
};

export function QualityCheckDialog({
  open,
  onClose,
  checkType,
  positionId,
  factoryId,
  positionLabel,
}: QualityCheckDialogProps) {
  const { data: itemsDef, isLoading } = useChecklistItems(checkType);
  const createPreKiln = useCreatePreKilnCheck();
  const createFinal = useCreateFinalCheck();

  const [results, setResults] = useState<Record<string, CheckValue>>({});
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const items = itemsDef?.items ?? {};
  const itemKeys = Object.keys(items);

  // Determine available values based on check type
  const availableValues: CheckValue[] = checkType === 'pre_kiln'
    ? ['pass', 'fail', 'na']
    : ['pass', 'fail'];

  // Compute overall result from individual items
  const overallResult = useMemo(() => {
    if (itemKeys.length === 0) return null;
    const filled = itemKeys.filter((k) => results[k]);
    if (filled.length < itemKeys.length) return null; // Not all filled

    const hasFail = filled.some((k) => results[k] === 'fail');
    if (hasFail) {
      return checkType === 'pre_kiln' ? 'needs_rework' : 'fail';
    }
    return 'pass';
  }, [results, itemKeys, checkType]);

  const allFilled = itemKeys.length > 0 && itemKeys.every((k) => results[k]);

  const handleToggle = (key: string, value: CheckValue) => {
    setResults((prev) => ({ ...prev, [key]: prev[key] === value ? (undefined as unknown as CheckValue) : value }));
  };

  const handleSubmit = async () => {
    if (!overallResult) return;
    setSubmitting(true);
    try {
      const payload = {
        position_id: positionId,
        factory_id: factoryId,
        checklist_results: results,
        overall_result: overallResult,
        notes: notes.trim() || undefined,
      };
      if (checkType === 'pre_kiln') {
        await createPreKiln.mutateAsync(payload);
      } else {
        await createFinal.mutateAsync(payload);
      }
      // Reset and close
      setResults({});
      setNotes('');
      onClose();
    } catch {
      // Error shown via toast or handled by caller
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setResults({});
    setNotes('');
    onClose();
  };

  const title = checkType === 'pre_kiln' ? 'Pre-Kiln QC Check' : 'Final QC Check';

  return (
    <Dialog open={open} onClose={handleClose} title={title} className="max-w-lg">
      {positionLabel && (
        <p className="mb-3 text-sm text-gray-500">{positionLabel}</p>
      )}

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : (
        <div className="space-y-3">
          {/* Checklist items */}
          {itemKeys.map((key) => (
            <div key={key} className="flex items-center justify-between gap-3 rounded-lg border p-3">
              <span className="text-sm font-medium text-gray-700">{items[key]}</span>
              <div className="flex gap-1.5">
                {availableValues.map((val) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => handleToggle(key, val)}
                    className={cn(
                      'rounded-md border px-3 py-1 text-xs font-semibold uppercase transition-colors',
                      results[key] === val ? VALUE_ACTIVE[val] : VALUE_COLORS[val],
                    )}
                  >
                    {val === 'na' ? 'N/A' : val === 'pass' ? 'Pass' : 'Fail'}
                  </button>
                ))}
              </div>
            </div>
          ))}

          {/* Notes */}
          <textarea
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded-md border border-gray-300 p-2 text-sm focus:border-primary-500 focus:outline-none"
            rows={2}
          />

          {/* Overall result indicator */}
          {allFilled && overallResult && (
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-600">Result:</span>
              <span
                className={cn(
                  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase',
                  overallResult === 'pass'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800',
                )}
              >
                {overallResult === 'pass' ? 'PASS' : overallResult === 'needs_rework' ? 'NEEDS REWORK' : 'FAIL'}
              </span>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={handleClose}>Cancel</Button>
            <Button
              disabled={!allFilled || submitting}
              onClick={handleSubmit}
            >
              {submitting ? 'Saving...' : 'Submit'}
            </Button>
          </div>
        </div>
      )}
    </Dialog>
  );
}
