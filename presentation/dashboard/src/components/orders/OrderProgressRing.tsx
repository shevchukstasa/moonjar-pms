/**
 * Order progress ring — SVG circle that fills based on position status breakdown.
 * Gold gradient stroke, animated fill, percentage in center.
 *
 * Two modes:
 * 1. Full: pass `positions` array — calculates weighted progress from statuses.
 * 2. Simple: pass `readyCount` + `totalCount` — calculates progress as ready/total %.
 */

interface FullProps {
  positions: Array<{ status: string }>;
  readyCount?: never;
  totalCount?: never;
  size?: number;
}

interface SimpleProps {
  positions?: never;
  readyCount: number;
  totalCount: number;
  size?: number;
}

type Props = FullProps | SimpleProps;

const STATUS_WEIGHT: Record<string, number> = {
  // 0-20%: planned / awaiting
  planned: 10,
  insufficient_materials: 5,
  awaiting_recipe: 8,
  awaiting_stencil_silkscreen: 10,
  awaiting_color_matching: 10,
  // 20-40%: glazing / engobe
  engobe_applied: 25,
  engobe_check: 28,
  sent_to_glazing: 30,
  glazed: 35,
  pre_kiln_check: 38,
  // 40-60%: kiln / firing
  loaded_in_kiln: 45,
  fired: 55,
  refire: 42,
  awaiting_reglaze: 35,
  // 60-80%: sorting / QC
  transferred_to_sorting: 65,
  packed: 70,
  sent_to_quality_check: 72,
  quality_check_done: 78,
  blocked_by_qm: 60,
  // 80-100%: ready / shipped
  ready_for_shipment: 90,
  shipped: 100,
  cancelled: 0,
};

function calculateProgress(positions: Array<{ status: string }>): number {
  if (positions.length === 0) return 0;
  const total = positions.reduce((sum, p) => {
    return sum + (STATUS_WEIGHT[p.status] ?? 10);
  }, 0);
  return Math.min(100, total / positions.length);
}

export function OrderProgressRing(props: Props) {
  const { size = 64 } = props;

  const progress = props.positions
    ? calculateProgress(props.positions)
    : props.totalCount > 0
      ? Math.round((props.readyCount / props.totalCount) * 100)
      : 0;

  const circumference = 2 * Math.PI * 16; // r=16
  const dashArray = `${(progress / 100) * circumference} ${circumference}`;

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 36 36" className="h-full w-full -rotate-90">
        <defs>
          <linearGradient id="gold-ring" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#e5993a" />
            <stop offset="100%" stopColor="#d4a574" />
          </linearGradient>
        </defs>
        {/* Background circle */}
        <circle
          cx="18" cy="18" r="16"
          fill="none"
          className="stroke-stone-200 dark:stroke-stone-700"
          strokeWidth="2.5"
        />
        {/* Progress circle */}
        <circle
          cx="18" cy="18" r="16"
          fill="none"
          stroke="url(#gold-ring)"
          strokeWidth="2.5"
          strokeDasharray={dashArray}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center font-semibold text-stone-700 dark:text-stone-200"
        style={{ fontSize: size < 80 ? '0.65rem' : '0.875rem' }}
      >
        {Math.round(progress)}%
      </span>
    </div>
  );
}
