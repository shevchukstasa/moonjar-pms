import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { StatusDropdown } from './StatusDropdown';
import { useTabloStore } from '@/stores/tabloStore';
import { Tooltip } from '@/components/ui/Tooltip';
import { formatShapeBadge, getShapeDefinition } from '@/components/shared/ShapeDimensionEditor';

export interface PositionItem {
  id: string;
  order_id: string;
  order_number: string;
  status: string;
  color: string;
  size: string;
  application?: string | null;
  application_method?: string | null;
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
  shape?: string | null;
  shape_dimensions?: Record<string, number> | null;
  calculated_area_cm2?: number | null;
  thickness_mm?: number | null;
  place_of_application?: string | null;
  edge_profile?: string | null;
  edge_profile_sides?: number | null;
  edge_profile_notes?: string | null;
  width_cm?: number | null;
  length_cm?: number | null;
  material_status?: string | null;
}

/** Human-readable labels for place_of_application enum */
const POA_LABELS: Record<string, string> = {
  face_only: 'Face',
  edges_1: 'Face + 1 edge',
  edges_2: 'Face + 2 edges',
  all_edges: 'Face + all edges',
  with_back: 'All surfaces',
};

export function formatPlaceOfApplication(value?: string | null): string {
  if (!value) return POA_LABELS['face_only'];  // default: Face (top only)
  return POA_LABELS[value] ?? value;
}

/** Human-readable labels for edge profile types */
const EDGE_PROFILE_LABELS: Record<string, string> = {
  straight: 'Straight',
  beveled_45: 'Bevel 45\u00B0',
  beveled_30: 'Bevel 30\u00B0',
  rounded: 'Rounded',
  bullnose: 'Bullnose',
  pencil: 'Pencil',
  ogee: 'Ogee',
  waterfall: 'Waterfall',
  stepped: 'Stepped',
  custom: 'Custom',
};

/** Format edge profile for display. Returns 'Straight' as default when not set. */
export function formatEdgeProfile(profile?: string | null, sides?: number | null): string {
  if (!profile || profile === 'straight') return EDGE_PROFILE_LABELS['straight'];
  const label = EDGE_PROFILE_LABELS[profile] ?? profile;
  if (sides && sides > 0) return `${label} \u00D7${sides}`;
  return label;
}

/** Format shape with smart default: square if width==length, rectangle otherwise */
export function formatShape(shape?: string | null, widthCm?: number | null, lengthCm?: number | null): string {
  if (shape) return shape.charAt(0).toUpperCase() + shape.slice(1);
  // Default based on dimensions
  if (widthCm && lengthCm && widthCm === lengthCm) return 'Square';
  return 'Rectangle';
}

/** Material status badge configuration */
const MATERIAL_STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  reserved: { label: 'Reserved', color: 'bg-green-100 text-green-700' },
  ordered: { label: 'Ordered', color: 'bg-yellow-100 text-yellow-700' },
  insufficient: { label: 'Insufficient', color: 'bg-red-100 text-red-700' },
  not_reserved: { label: 'Not Reserved', color: 'bg-gray-100 text-gray-600' },
  consumed: { label: 'Consumed', color: 'bg-blue-100 text-blue-700' },
  awaiting_data: { label: 'Awaiting Data', color: 'bg-orange-100 text-orange-700' },
};

export function MaterialStatusBadge({ status }: { status?: string | null }) {
  const cfg = MATERIAL_STATUS_CONFIG[status ?? 'not_reserved'] ?? MATERIAL_STATUS_CONFIG['not_reserved'];
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

const NON_SPLITTABLE_STATUSES = ['in_kiln', 'fired'];
const MERGEABLE_STATUSES = ['packed', 'quality_check_done', 'ready_for_shipment'];

/** Color map for application method badges */
const METHOD_BADGE_COLORS: Record<string, string> = {
  ss: 'bg-purple-100 text-purple-700',
  s:  'bg-blue-100 text-blue-700',
  bs: 'bg-green-100 text-green-700',
  sb: 'bg-teal-100 text-teal-700',
  b:  'bg-amber-100 text-amber-700',
  sp: 'bg-pink-100 text-pink-700',
};

interface Props {
  position: PositionItem;
  index: number;
  section: string;
  onSplit?: (position: PositionItem) => void;
  onMerge?: (position: PositionItem) => void;
  onViewSplitTree?: (positionId: string) => void;
  mobileCard?: boolean;
}

export function PositionRow({ position, index, section, onSplit, onMerge, onViewSplitTree, mobileCard }: Props) {
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

  // Shape badge with dimensions tooltip
  const shapeDef = position.shape ? getShapeDefinition(position.shape) : null;
  const shapeBadgeText = formatShapeBadge(position.shape, position.shape_dimensions);
  const shapeIcon = shapeDef?.icon ?? '';

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
              {position.color} · {position.size}
              {shapeIcon && (
                <Tooltip text={shapeBadgeText}>
                  <span className="ml-1 inline-flex items-center rounded bg-indigo-50 px-1 py-0.5 text-[10px] font-medium text-indigo-700 cursor-default">
                    {shapeIcon}
                  </span>
                </Tooltip>
              )}
              {' '} · {position.quantity} pcs
              {position.application_method && (
                <span className={`ml-1.5 inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${METHOD_BADGE_COLORS[position.application_method.toLowerCase()] || 'bg-gray-100 text-gray-600'}`}>
                  {position.application_method}
                </span>
              )}
              {(() => {
                const edgeBadge = formatEdgeProfile(position.edge_profile, position.edge_profile_sides);
                return edgeBadge ? (
                  <span className="ml-1.5 inline-flex items-center rounded bg-orange-50 px-1.5 py-0.5 text-[10px] font-medium text-orange-700">
                    {edgeBadge}
                  </span>
                ) : null;
              })()}
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
          <MaterialStatusBadge status={position.material_status} />
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
            {onViewSplitTree && (position.parent_position_id || position.split_index != null) && (
              <button
                onClick={() => onViewSplitTree(position.id)}
                className="rounded p-2 min-h-[44px] min-w-[44px] flex items-center justify-center text-gray-400 hover:bg-indigo-50 hover:text-indigo-600"
                title="View split tree"
              >
                &#x1F333;
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
      <td className="px-3 py-2 text-sm">
        {position.size}
        {shapeIcon && (
          <Tooltip text={shapeBadgeText}>
            <span className="ml-1.5 inline-flex items-center rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 cursor-default">
              {shapeIcon}
            </span>
          </Tooltip>
        )}
      </td>
      <td className="px-3 py-2 text-sm">{position.thickness_mm ? `${position.thickness_mm} mm` : '10 mm'}</td>
      <td className="px-3 py-2 text-sm">{formatShape(position.shape, position.width_cm, position.length_cm)}</td>
      <td className="px-3 py-2 text-sm">{formatPlaceOfApplication(position.place_of_application)}</td>
      <td className="px-3 py-2 text-sm">
        {(() => {
          const edge = formatEdgeProfile(position.edge_profile, position.edge_profile_sides);
          const isNonDefault = position.edge_profile && position.edge_profile !== 'straight';
          return isNonDefault ? (
            <span className="inline-flex items-center rounded bg-orange-50 px-1.5 py-0.5 text-[10px] font-medium text-orange-700">
              {edge}
            </span>
          ) : edge;
        })()}
      </td>
      <td className="px-3 py-2 text-sm">
        {position.application ?? '\u2014'}
        {position.application_method && (
          <span className={`ml-1.5 inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${METHOD_BADGE_COLORS[position.application_method.toLowerCase()] || 'bg-gray-100 text-gray-600'}`}>
            {position.application_method}
          </span>
        )}
      </td>
      <td className="px-3 py-2 text-sm">{position.collection ?? '\u2014'}</td>
      <td className="px-3 py-2 text-sm text-right">{position.quantity}</td>
      <td className="px-3 py-2">
        <StatusDropdown
          positionId={position.id}
          currentStatus={position.status}
          section={section}
        />
      </td>
      <td className="px-3 py-2">
        <MaterialStatusBadge status={position.material_status} />
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
      {onViewSplitTree && (position.parent_position_id || position.split_index != null) && (
        <td className="w-10 px-2 py-2 text-center">
          <button
            onClick={() => onViewSplitTree(position.id)}
            className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600"
            title="View split tree"
          >
            &#x1F333;
          </button>
        </td>
      )}
    </tr>
  );
}
