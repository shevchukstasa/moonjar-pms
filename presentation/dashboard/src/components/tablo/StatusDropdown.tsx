import { useState } from 'react';
import { useChangePositionStatus, useAllowedTransitions } from '@/hooks/usePositions';
import { getStatusColor } from '@/lib/statusColors';

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

export function formatStatus(s: string) {
  return STATUS_LABELS[s] || s.replace(/_/g, ' ');
}

interface Props {
  positionId: string;
  currentStatus: string;
  section: string;           // kept for compatibility, but no longer filters options
}

export function StatusDropdown({ positionId, currentStatus }: Props) {
  const changeStatus = useChangePositionStatus();
  const { data: transitions, isLoading } = useAllowedTransitions(positionId);
  const [pending, setPending] = useState(false);

  const handleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value;
    if (newStatus === currentStatus) return;
    setPending(true);
    try {
      await changeStatus.mutateAsync({ id: positionId, status: newStatus });
    } finally {
      setPending(false);
    }
  };

  const colorClass = getStatusColor(currentStatus);

  // Build option list: current status + allowed transitions from backend
  const allowed = transitions?.allowed ?? [];
  // Ensure current status is always present as first option
  const options = [currentStatus, ...allowed.filter((s) => s !== currentStatus)];

  return (
    <select
      value={currentStatus}
      onChange={handleChange}
      disabled={pending || isLoading}
      className={`rounded-md border border-gray-200 px-2 py-1 text-xs font-medium capitalize ${colorClass} ${pending || isLoading ? 'opacity-50' : ''}`}
    >
      {options.map((s) => (
        <option key={s} value={s}>
          {formatStatus(s)}
        </option>
      ))}
    </select>
  );
}
