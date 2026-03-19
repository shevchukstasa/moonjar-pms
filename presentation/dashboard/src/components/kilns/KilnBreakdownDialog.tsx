import { useState } from 'react';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useReportBreakdown, useRestoreKiln, type KilnItem } from '@/hooks/useKilns';

interface BreakdownProps {
  open: boolean;
  onClose: () => void;
  kiln: KilnItem | null;
}

export function KilnBreakdownDialog({ open, onClose, kiln }: BreakdownProps) {
  const [reason, setReason] = useState('');
  const [estimatedHours, setEstimatedHours] = useState('');
  const breakdown = useReportBreakdown();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!kiln || !reason.trim()) return;

    breakdown.mutate(
      {
        id: kiln.id,
        data: {
          reason: reason.trim(),
          estimated_repair_hours: estimatedHours ? parseInt(estimatedHours, 10) : null,
        },
      },
      {
        onSuccess: (result) => {
          setReason('');
          setEstimatedHours('');
          onClose();
          alert(
            `Kiln "${kiln.name}" marked as broken.\n` +
            `Batches affected: ${result.affected_batches}\n` +
            `Auto-reassigned: ${result.reassigned_batches}\n` +
            `Need manual action: ${result.failed_batches}`
          );
        },
        onError: (error: unknown) => {
          const msg = error instanceof Error ? error.message : 'Unknown error';
          alert(`Failed to report breakdown: ${msg}`);
        },
      },
    );
  };

  if (!kiln) return null;

  return (
    <Dialog open={open} onClose={onClose} title={`Report Breakdown: ${kiln.name}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="text-sm font-medium text-red-800">
            This will mark the kiln as emergency maintenance and attempt to reassign
            all active batches to other available kilns.
          </p>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Reason for breakdown <span className="text-red-500">*</span>
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Describe what happened..."
            rows={3}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            required
          />
        </div>

        <Input
          label="Estimated repair time (hours)"
          type="number"
          value={estimatedHours}
          onChange={(e) => setEstimatedHours(e.target.value)}
          placeholder="e.g. 24"
          min={1}
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={!reason.trim() || breakdown.isPending}
            className="bg-red-600 text-white hover:bg-red-700"
          >
            {breakdown.isPending ? 'Reporting...' : 'Report Breakdown'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}


interface RestoreProps {
  open: boolean;
  onClose: () => void;
  kiln: KilnItem | null;
}

export function KilnRestoreDialog({ open, onClose, kiln }: RestoreProps) {
  const [notes, setNotes] = useState('');
  const restore = useRestoreKiln();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!kiln) return;

    restore.mutate(
      {
        id: kiln.id,
        data: { notes: notes.trim() || null },
      },
      {
        onSuccess: () => {
          setNotes('');
          onClose();
          alert(`Kiln "${kiln.name}" has been restored to active status.`);
        },
        onError: (error: unknown) => {
          const msg = error instanceof Error ? error.message : 'Unknown error';
          alert(`Failed to restore kiln: ${msg}`);
        },
      },
    );
  };

  if (!kiln) return null;

  return (
    <Dialog open={open} onClose={onClose} title={`Restore Kiln: ${kiln.name}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="rounded-lg border border-green-200 bg-green-50 p-3">
          <p className="text-sm font-medium text-green-800">
            This will set the kiln back to active status and complete any open
            maintenance records.
          </p>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Repair notes (optional)
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="What was repaired..."
            rows={3}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={restore.isPending}
            className="bg-green-600 text-white hover:bg-green-700"
          >
            {restore.isPending ? 'Restoring...' : 'Restore Kiln'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
