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
  mobileCard?: boolean;
}

export function PositionRow({ position, index, section, onSplit, onMerge, mobileCard }: Props) {
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

  const posLabel = position.position_label
    ?? (position.position_number != null
      ? (position.split_index != null
        ? `#${position.position_number}.${position.split_index}`
        : `#${position.position_number}`)
      : `#${index + 1}`);

  /* ---- Mobile card layout ---- */
  if (mobileCard) {
    return (
      <div
        ref={setNodeRef}
        style={style}
        className={`rounded-lg border border-gray-200 p-3 ${rowBg || 'bg-white'}`}
      >
        {/* Row 1: drag handle, order, status */}
        <div className="flex items-center gap-2">
          <button
            {...attributes}
            {...listeners}
            className="cursor-grab touch-none text-gray-400 hover:text-gray-600 min-h-[44px] min-w-[44px] flex items-center justify-center"
            title="Drag to reorder"
          >
            ⠿
          </button>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-900 truncate">{position.order_number}</span>
              <span className="text-xs font-mono font-semibold text-gray-500">{posLabel}</span>
            </div>
            <p className="text-sm text-gray-600 truncate">
              {position.color} · {position.size} · {position.quantity} pcs
            </p>
          </div>
          {delay > 0 && (
            <span className={`text-xs font-medium whitespace-nowrap ${delay > 72 ? 'text-red-600' : delay > 24 ? 'text-yellow-600' : 'text-gray-500'}`}>
              {delayDisplay}
            </span>
          )}
        </div>
        {/* Row 2: status + actions */}
        <div className="mt-2 flex items-center gap-2 pl-11">
          <StatusDropdown
            positionId={position.id}
            currentStatus={position.status}
            section={section}
          />
          <span className="text-xs text-gray-500">{position.product_type}</span>
          <div className="ml-auto flex items-center gap-1">
            {onSplit && !NON_SPLITTABLE_STATUSES.includes(position.status) && (
              <button
                onClick={() => onSplit(position)}
                className="rounded p-2 min-h-[44px] min-w-[44px] flex items-center justify-center text-gray-400 hover:bg-blue-50 hover:text-blue-600"
                title="Split production"
              >
                &#9986;
              </button>
            )}
            {onMerge && position.parent_position_id && !position.is_merged && MERGEABLE_STATUSES.includes(position.status) && (
              <button
                onClick={() => onMerge(position)}
                className="rounded p-2 min-h-[44px] min-w-[44px] flex items-center justify-center text-gray-400 hover:bg-green-50 hover:text-green-600"
                title="Merge back into parent"
              >
                &#x2934;
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ---- Desktop table row ---- */
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
        {posLabel}
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
