import { useState } from 'react';
import { toast } from 'sonner';
import { useChangePositionStatus } from '@/hooks/usePositions';
import { useAuthStore } from '@/stores/authStore';
import { getStatusColor } from '@/lib/statusColors';
import { CelebrationPulse } from '@/components/ui/Celebration';
import { getAllowedTransitions } from '@/lib/statusMachine';

const STATUS_LABELS: Record<string, string> = {
  planned: 'Planned',
  insufficient_materials: 'Insufficient Materials',
  awaiting_recipe: 'Awaiting Recipe',
  awaiting_stencil_silkscreen: 'Awaiting Stencil / Silkscreen',
  awaiting_color_matching: 'Awaiting Color Matching',
  engobe_applied: 'Engobe Applied',
  engobe_check: 'Engobe Check',
  glazed: 'Glazed',
  pre_kiln_check: 'Pre-Kiln Check',
  sent_to_glazing: 'Sent to Glazing',
  loaded_in_kiln: 'Loaded in Kiln',
  fired: 'Fired',
  refire: 'Refire',
  awaiting_reglaze: 'Awaiting Reglaze',
  transferred_to_sorting: 'Transferred to Sorting',
  packed: 'Packed',
  sent_to_quality_check: 'Sent to QC',
  quality_check_done: 'QC Done',
  ready_for_shipment: 'Ready for Shipment',
  blocked_by_qm: 'Blocked by QM',
  shipped: 'Shipped',
  cancelled: 'Cancelled',
};

/** Milestone statuses that trigger celebration animation + toast. */
const CELEBRATION_STATUSES: Record<string, string> = {
  fired: '\uD83D\uDD25 Position fired successfully',
  quality_check_done: '\u2705 Quality check passed',
  ready_for_shipment: '\uD83D\uDCE6 Position ready for shipment',
  shipped: '\uD83D\uDE80 Position shipped — great work!',
};

export function formatStatus(s: string | undefined | null) {
  if (!s) return '\u2014';
  return STATUS_LABELS[s] || s.replace(/_/g, ' ');
}

interface Props {
  positionId: string;
  currentStatus: string;
  section: string;           // kept for compatibility, but no longer filters options
}

export function StatusDropdown({ positionId, currentStatus }: Props) {
  const changeStatus = useChangePositionStatus();
  const user = useAuthStore((s) => s.user);
  const [pending, setPending] = useState(false);
  const [celebrate, setCelebrate] = useState(false);

  const handleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value;
    if (newStatus === currentStatus) return;
    setPending(true);
    try {
      await changeStatus.mutateAsync({ id: positionId, status: newStatus });

      // Celebration for milestone statuses
      const msg = CELEBRATION_STATUSES[newStatus];
      if (msg) {
        setCelebrate(true);
        toast.success(msg);
        setTimeout(() => setCelebrate(false), 1500);
      }
    } finally {
      setPending(false);
    }
  };

  const colorClass = getStatusColor(currentStatus);

  // Compute allowed transitions client-side (no API call needed)
  const allowed = getAllowedTransitions(currentStatus, user?.role);
  const options = [currentStatus, ...allowed.filter((s) => s !== currentStatus)];

  return (
    <div className="relative inline-block">
      <CelebrationPulse show={celebrate} />
      <select
        value={currentStatus}
        onChange={handleChange}
        disabled={pending}
        className={`rounded-md border border-gray-200 px-2 py-1 text-xs font-medium capitalize ${colorClass} ${pending ? 'opacity-50' : ''}`}
      >
        {options.map((s) => (
          <option key={s} value={s}>
            {formatStatus(s)}
          </option>
        ))}
      </select>
    </div>
  );
}
