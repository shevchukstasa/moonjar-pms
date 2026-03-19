import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { StatusDropdown } from './StatusDropdown';
import { useTabloStore } from '@/stores/tabloStore';

export interface PositionItem {
  id: string;
  order_id: string;
  order_number: string;
  status: string;
  color: string;
  size: string;
  application?: string | null;
  collection?: string | null;
  quantity: number;
  product_type: string;
  delay_hours: number;
  priority_order: number;
  batch_id: string | null;
  position_number?: number | null;
  split_index?: number | null;
  position_label?: string | null;
  parent_position_id?: string | null;
  is_merged?: boolean;
}

const NON_SPLITTABLE_STATUSES = ['in_kiln', 'fired'];
const MERGEABLE_STATUSES = ['packed', 'quality_check_done', 'ready_for_shipment'];

interface Props {
  position: PositionItem;
  index: number;
  section: string;
  onSplit?: (position: PositionItem) => void;
  onMerge?: (position: PositionItem) => void;
}

export function PositionRow({ position, index, section, onSplit, onMerge }: Props) {
  const delayUnit = useTabloStore((s) => s.delayUnit);
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: position.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const delay = position.delay_hours || 0;
  const delayDisplay =
    delayUnit === 'days'
      ? `${(delay / 24).toFixed(1)}d`
      : `${delay.toFixed(0)}h`;

  // Color-code rows based on delay
  let rowBg = '';
  if (delay > 72) rowBg = 'bg-red-50';
  else if (delay > 24) rowBg = 'bg-yellow-50';

  return (
    <tr ref={setNodeRef} style={style} className={`border-b ${rowBg}`}>
      {/* drag handle */}
      <td className="w-8 px-2 py-2 text-center">
        <button
          {...attributes}
          {...listeners}
          className="cursor-grab touch-none text-gray-400 hover:text-gray-600"
          title="Drag to reorder"
        >
          ⠿
        </button>
      </td>
      <td className="px-3 py-2 text-sm font-medium text-gray-900">{position.order_number}</td>
      <td className="px-3 py-2 text-xs font-mono font-semibold text-gray-700">
        {position.position_label
          ?? (position.position_number != null
            ? (position.split_index != null
              ? `#${position.position_number}.${position.split_index}`
              : `#${position.position_number}`)
            : `#${index + 1}`)}
      </td>
      <td className="px-3 py-2 text-sm">{position.color}</td>
      <td className="px-3 py-2 text-sm">{position.size}</td>
      <td className="px-3 py-2 text-sm">{position.application ?? '\u2014'}</td>
      <td className="px-3 py-2 text-sm">{position.collection ?? '\u2014'}</td>
      <td className="px-3 py-2 text-sm text-right">{position.quantity}</td>
      <td className="px-3 py-2">
        <StatusDropdown
          positionId={position.id}
          currentStatus={position.status}
          section={section}
        />
      </td>
      <td className="px-3 py-2 text-sm">{position.product_type}</td>
      <td className={`px-3 py-2 text-xs text-right ${delay > 72 ? 'font-semibold text-red-600' : delay > 24 ? 'text-yellow-600' : 'text-gray-500'}`}>
        {delay > 0 ? delayDisplay : '\u2014'}
      </td>
      {onSplit && (
        <td className="w-10 px-2 py-2 text-center">
          {NON_SPLITTABLE_STATUSES.includes(position.status) ? (
            <span className="text-gray-300 cursor-not-allowed" title="Cannot split during firing">
              &#9986;
            </span>
          ) : (
            <button
              onClick={() => onSplit(position)}
              className="rounded p-1 text-gray-400 hover:bg-blue-50 hover:text-blue-600"
              title="Split production"
            >
              &#9986;
            </button>
          )}
        </td>
      )}
      {onMerge && position.parent_position_id && !position.is_merged && MERGEABLE_STATUSES.includes(position.status) && (
        <td className="w-10 px-2 py-2 text-center">
          <button
            onClick={() => onMerge(position)}
            className="rounded p-1 text-gray-400 hover:bg-green-50 hover:text-green-600"
            title="Merge back into parent"
          >
            &#x2934;
          </button>
        </td>
      )}
    </tr>
  );
}
