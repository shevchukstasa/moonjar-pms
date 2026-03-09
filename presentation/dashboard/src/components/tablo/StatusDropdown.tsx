import { useState } from 'react';
import { useChangePositionStatus } from '@/hooks/usePositions';
import { getStatusColor } from '@/lib/statusColors';

// Allowed transitions per section
const SECTION_STATUSES: Record<string, string[]> = {
  glazing: [
    'planned', 'insufficient_materials', 'awaiting_recipe',
    'awaiting_stencil_silkscreen', 'awaiting_color_matching',
    'engobe_applied', 'engobe_check', 'glazed', 'pre_kiln_check', 'sent_to_glazing',
  ],
  firing: ['loaded_in_kiln', 'fired', 'refire', 'awaiting_reglaze'],
  sorting: [
    'transferred_to_sorting', 'packed', 'sent_to_quality_check',
    'quality_check_done', 'ready_for_shipment', 'blocked_by_qm',
  ],
};

const STATUS_LABELS: Record<string, string> = {
  awaiting_stencil_silkscreen: 'Awaiting Stencil / Silkscreen',
  awaiting_color_matching: 'Awaiting Color Matching',
  awaiting_recipe: 'Awaiting Recipe',
  awaiting_reglaze: 'Awaiting Reglaze',
  insufficient_materials: 'Insufficient Materials',
  pre_kiln_check: 'Pre-Kiln Check',
  sent_to_glazing: 'Sent to Glazing',
  loaded_in_kiln: 'Loaded in Kiln',
  transferred_to_sorting: 'Transferred to Sorting',
  sent_to_quality_check: 'Sent to QC',
  quality_check_done: 'QC Done',
  ready_for_shipment: 'Ready for Shipment',
  blocked_by_qm: 'Blocked by QM',
};

export function formatStatus(s: string) {
  return STATUS_LABELS[s] || s.replace(/_/g, ' ');
}

interface Props {
  positionId: string;
  currentStatus: string;
  section: string;
}

export function StatusDropdown({ positionId, currentStatus, section }: Props) {
  const changeStatus = useChangePositionStatus();
  const [pending, setPending] = useState(false);

  const options = SECTION_STATUSES[section] || [];

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

  return (
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
  );
}
