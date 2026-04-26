import { useMemo, useCallback } from 'react';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';

// ---------------------------------------------------------------------------
// Shape definitions: labels, icons, dimension fields, area formulas
// ---------------------------------------------------------------------------

export interface ShapeDefinition {
  value: string;
  label: string;
  icon: string;
  fields: {
    key: string;
    label: string;
    unit: string;
    /** When true, this field is auto-derived from the others and read-only. */
    derived?: boolean;
  }[];
  /** Returns area in cm^2 given numeric dimension values, or null if invalid */
  area: (d: Record<string, number>) => number | null;
  /** Optional extra validation; returns error string or null */
  validate?: (d: Record<string, number>) => string | null;
  /**
   * Optional hook to derive values from user-entered ones. Called after every
   * input change. Used e.g. by right_triangle to compute hypotenuse from legs.
   */
  derive?: (d: Record<string, number>) => Record<string, number>;
}

export const SHAPE_DEFINITIONS: ShapeDefinition[] = [
  {
    value: 'rectangle',
    label: 'Rectangle',
    icon: '▬',
    fields: [
      { key: 'width', label: 'Width (cm)', unit: 'cm' },
      { key: 'height', label: 'Height (cm)', unit: 'cm' },
    ],
    area: (d) => {
      const w = d.width, h = d.height;
      if (!w || !h || w <= 0 || h <= 0) return null;
      return w * h;
    },
  },
  {
    value: 'square',
    label: 'Square',
    icon: '⬜',
    fields: [{ key: 'side', label: 'Side (cm)', unit: 'cm' }],
    area: (d) => {
      const s = d.side;
      if (!s || s <= 0) return null;
      return s * s;
    },
  },
  {
    value: 'right_triangle',
    label: 'Right triangle',
    icon: '📐',
    fields: [
      { key: 'side_a', label: 'Leg A (cm)', unit: 'cm' },
      { key: 'side_b', label: 'Leg B (cm)', unit: 'cm' },
      { key: 'side_c', label: 'Hypotenuse (cm)', unit: 'cm', derived: true },
    ],
    area: (d) => {
      const a = d.side_a, b = d.side_b;
      if (!a || !b || a <= 0 || b <= 0) return null;
      return (a * b) / 2;
    },
    derive: (d) => {
      const a = d.side_a, b = d.side_b;
      if (a && b && a > 0 && b > 0) {
        return { ...d, side_c: Math.sqrt(a * a + b * b) };
      }
      return d;
    },
  },
  {
    value: 'triangle',
    label: 'Triangle (any)',
    icon: '🔺',
    fields: [
      { key: 'side_a', label: 'Side A (cm)', unit: 'cm' },
      { key: 'side_b', label: 'Side B (cm)', unit: 'cm' },
      { key: 'side_c', label: 'Side C (cm)', unit: 'cm' },
    ],
    area: (d) => {
      const a = d.side_a, b = d.side_b, c = d.side_c;
      if (!a || !b || !c || a <= 0 || b <= 0 || c <= 0) return null;
      if (a + b <= c || a + c <= b || b + c <= a) return null;
      const s = (a + b + c) / 2;
      return Math.sqrt(s * (s - a) * (s - b) * (s - c));
    },
    validate: (d) => {
      const a = d.side_a, b = d.side_b, c = d.side_c;
      if (!a || !b || !c) return null;
      if (a + b <= c || a + c <= b || b + c <= a)
        return 'Invalid triangle: sum of any two sides must exceed the third';
      return null;
    },
  },
  {
    value: 'circle',
    label: 'Circle',
    icon: '⭕',
    fields: [{ key: 'diameter', label: 'Diameter (cm)', unit: 'cm' }],
    area: (d) => {
      const dia = d.diameter;
      if (!dia || dia <= 0) return null;
      return Math.PI * (dia / 2) ** 2;
    },
  },
  {
    value: 'oval',
    label: 'Oval',
    icon: '⬭',
    fields: [
      { key: 'diameter_1', label: 'Diameter 1 (cm)', unit: 'cm' },
      { key: 'diameter_2', label: 'Diameter 2 (cm)', unit: 'cm' },
    ],
    area: (d) => {
      const d1 = d.diameter_1, d2 = d.diameter_2;
      if (!d1 || !d2 || d1 <= 0 || d2 <= 0) return null;
      return Math.PI * (d1 / 2) * (d2 / 2);
    },
  },
  {
    value: 'octagon',
    label: 'Octagon',
    icon: '🛑',
    fields: [
      { key: 'width', label: 'Width (cm)', unit: 'cm' },
      { key: 'height', label: 'Height (cm)', unit: 'cm' },
      { key: 'corner_cut', label: 'Corner cut (cm)', unit: 'cm' },
    ],
    area: (d) => {
      const w = d.width, h = d.height, c = d.corner_cut;
      if (!w || !h || !c || w <= 0 || h <= 0 || c <= 0) return null;
      if (c * 2 >= w || c * 2 >= h) return null;
      // Rectangle minus 4 corner triangles (each is right isoceles with legs = corner_cut)
      return w * h - 2 * c * c;
    },
    validate: (d) => {
      const w = d.width, h = d.height, c = d.corner_cut;
      if (!w || !h || !c) return null;
      if (c * 2 >= w || c * 2 >= h) return 'Corner cut is too large for given width/height';
      return null;
    },
  },
  {
    value: 'trapezoid',
    label: 'Trapezoid',
    icon: '⏢',
    fields: [
      { key: 'side_a', label: 'Side A (cm)', unit: 'cm' },
      { key: 'side_b', label: 'Side B (cm)', unit: 'cm' },
      { key: 'height', label: 'Height (cm)', unit: 'cm' },
    ],
    area: (d) => {
      const a = d.side_a, b = d.side_b, h = d.height;
      if (!a || !b || !h || a <= 0 || b <= 0 || h <= 0) return null;
      return ((a + b) / 2) * h;
    },
  },
  {
    value: 'trapezoid_truncated',
    label: 'Truncated Trapezoid',
    icon: '⏢',
    fields: [
      { key: 'side_a', label: 'Side A (cm)', unit: 'cm' },
      { key: 'side_b', label: 'Side B (cm)', unit: 'cm' },
      { key: 'height', label: 'Height (cm)', unit: 'cm' },
    ],
    area: (d) => {
      const a = d.side_a, b = d.side_b, h = d.height;
      if (!a || !b || !h || a <= 0 || b <= 0 || h <= 0) return null;
      return ((a + b) / 2) * h;
    },
  },
  {
    value: 'rhombus',
    label: 'Rhombus',
    icon: '◇',
    fields: [
      { key: 'diagonal_1', label: 'Diagonal 1 (cm)', unit: 'cm' },
      { key: 'diagonal_2', label: 'Diagonal 2 (cm)', unit: 'cm' },
    ],
    area: (d) => {
      const d1 = d.diagonal_1, d2 = d.diagonal_2;
      if (!d1 || !d2 || d1 <= 0 || d2 <= 0) return null;
      return (d1 * d2) / 2;
    },
  },
  {
    value: 'parallelogram',
    label: 'Parallelogram',
    icon: '▱',
    fields: [
      { key: 'base', label: 'Base (cm)', unit: 'cm' },
      { key: 'height', label: 'Height (cm)', unit: 'cm' },
    ],
    area: (d) => {
      const b = d.base, h = d.height;
      if (!b || !h || b <= 0 || h <= 0) return null;
      return b * h;
    },
  },
  {
    value: 'semicircle',
    label: 'Semicircle',
    icon: '◑',
    fields: [{ key: 'diameter', label: 'Diameter (cm)', unit: 'cm' }],
    area: (d) => {
      const dia = d.diameter;
      if (!dia || dia <= 0) return null;
      return (Math.PI * (dia / 2) ** 2) / 2;
    },
  },
  {
    value: 'freeform',
    label: 'Freeform',
    icon: '⭐',
    fields: [{ key: 'area', label: 'Area (cm\u00B2)', unit: 'cm\u00B2' }],
    area: (d) => {
      const a = d.area;
      if (!a || a <= 0) return null;
      return a;
    },
  },
];

export function getShapeDefinition(shape: string): ShapeDefinition | undefined {
  return SHAPE_DEFINITIONS.find((s) => s.value === shape);
}

// ---------------------------------------------------------------------------
// Compact helpers for external consumers
// ---------------------------------------------------------------------------

/** Calculate area for a given shape + dimensions. Returns null if invalid. */
export function calculateShapeArea(
  shape: string,
  dimensions: Record<string, number> | null | undefined,
): number | null {
  if (!dimensions) return null;
  const def = getShapeDefinition(shape);
  if (!def) return null;
  return def.area(dimensions);
}

/** Format a shape badge string like "Triangle (10x10x14.14 cm) = 50 cm2" */
export function formatShapeBadge(
  shape: string | null | undefined,
  dimensions: Record<string, number> | null | undefined,
): string {
  if (!shape) return '';
  const def = getShapeDefinition(shape);
  if (!def) return shape;

  const icon = def.icon;
  if (!dimensions || Object.keys(dimensions).length === 0) return `${icon} ${def.label}`;

  // Build dimension string
  const dimValues = def.fields
    .map((f) => {
      const v = dimensions[f.key];
      return v != null ? String(Number(v.toFixed(2))) : '?';
    })
    .join('\u00D7');
  const unit = def.fields[0]?.unit || 'cm';

  const area = def.area(dimensions);
  const areaStr = area != null ? ` = ${area.toFixed(2)} cm\u00B2` : '';

  return `${icon} ${def.label} (${dimValues} ${unit})${areaStr}`;
}

// ---------------------------------------------------------------------------
// Compact size label used in dropdowns / table cells.
// Source of truth for "350×350 × 12mm round" type strings — shape-aware so a
// circle shows "Ø350mm" rather than "350×350" and a right triangle shows the
// two legs rather than a square bounding box.
// ---------------------------------------------------------------------------

export interface SizeForLabel {
  width_mm?: number | null;
  height_mm?: number | null;
  diameter_mm?: number | null;
  thickness_mm?: number | null;
  shape?: string | null;
  shape_dimensions?: Record<string, number> | null;
}

/** Render a size as a one-line label, e.g. "Ø350 × 12mm round". */
export function formatSizeLabel(s: SizeForLabel): string {
  const shape = (s.shape || 'rectangle').toLowerCase();
  const dims = s.shape_dimensions ?? null;
  const t = s.thickness_mm;
  const fmt = (n: number) => String(Number(n.toFixed(2)));
  const cmToMm = (cm: number) => fmt(cm * 10);
  const thicknessPart = t ? ` × ${t}mm` : 'mm';
  const shapeLabel = shape === 'rectangle' ? '' : ` ${shape.replace(/_/g, '-')}`;

  // Prefer shape_dimensions (authoritative — entered by user), fall back to
  // bounding-box width_mm/height_mm/diameter_mm for legacy rows.
  if ((shape === 'round' || shape === 'circle') && (dims?.diameter || s.diameter_mm)) {
    const dMm = dims?.diameter ? cmToMm(dims.diameter) : String(s.diameter_mm ?? s.width_mm);
    return `Ø${dMm}${thicknessPart}${shapeLabel}`;
  }
  if (shape === 'semicircle' && (dims?.diameter || s.width_mm)) {
    const dMm = dims?.diameter ? cmToMm(dims.diameter) : String(s.width_mm);
    return `Ø${dMm}/2${thicknessPart}${shapeLabel}`;
  }
  if (shape === 'oval' && dims?.diameter_1 && dims?.diameter_2) {
    return `${cmToMm(dims.diameter_1)}×${cmToMm(dims.diameter_2)}${thicknessPart}${shapeLabel}`;
  }
  if (shape === 'right_triangle' && dims?.side_a && dims?.side_b) {
    return `${cmToMm(dims.side_a)}×${cmToMm(dims.side_b)}${thicknessPart}${shapeLabel}`;
  }
  if (shape === 'triangle' && dims?.side_a && dims?.side_b && dims?.side_c) {
    return `${cmToMm(dims.side_a)}×${cmToMm(dims.side_b)}×${cmToMm(dims.side_c)}${thicknessPart}${shapeLabel}`;
  }
  if (shape === 'rhombus' && dims?.diagonal_1 && dims?.diagonal_2) {
    return `◇${cmToMm(dims.diagonal_1)}×${cmToMm(dims.diagonal_2)}${thicknessPart}${shapeLabel}`;
  }
  // Square: collapse to one value when bbox is square.
  const w = s.width_mm ?? 0;
  const h = s.height_mm ?? 0;
  if (shape === 'square' && w && h && w === h) {
    return `${w}×${w}${thicknessPart}${shapeLabel}`;
  }
  // Default: bounding-box width × height.
  if (w || h) {
    return `${w}×${h}${thicknessPart}${shapeLabel}`;
  }
  return shapeLabel.trim() || 'unknown';
}

// ---------------------------------------------------------------------------
// Shape SVG preview
// ---------------------------------------------------------------------------

function ShapePreview({ shape }: { shape: string }) {
  const size = 64;
  const pad = 6;
  const inner = size - pad * 2;

  const svgContent = (() => {
    switch (shape) {
      case 'rectangle':
        return <rect x={pad} y={pad + 8} width={inner} height={inner - 16} rx={2} />;
      case 'square':
        return <rect x={pad} y={pad} width={inner} height={inner} rx={2} />;
      case 'triangle':
        return (
          <polygon
            points={`${size / 2},${pad} ${pad},${size - pad} ${size - pad},${size - pad}`}
          />
        );
      case 'right_triangle':
        // Right angle at bottom-left; hypotenuse goes top-right to bottom-right
        return (
          <polygon
            points={`${pad},${pad} ${pad},${size - pad} ${size - pad},${size - pad}`}
          />
        );
      case 'circle':
        return <circle cx={size / 2} cy={size / 2} r={inner / 2} />;
      case 'oval':
        return <ellipse cx={size / 2} cy={size / 2} rx={inner / 2} ry={inner / 3} />;
      case 'octagon': {
        const c = inner * 0.3;
        const x0 = pad, x1 = pad + c, x2 = size - pad - c, x3 = size - pad;
        const y0 = pad, y1 = pad + c, y2 = size - pad - c, y3 = size - pad;
        return (
          <polygon
            points={`${x1},${y0} ${x2},${y0} ${x3},${y1} ${x3},${y2} ${x2},${y3} ${x1},${y3} ${x0},${y2} ${x0},${y1}`}
          />
        );
      }
      case 'trapezoid': {
        const offset = inner * 0.2;
        return (
          <polygon
            points={`${pad + offset},${pad} ${size - pad - offset},${pad} ${size - pad},${size - pad} ${pad},${size - pad}`}
          />
        );
      }
      case 'trapezoid_truncated': {
        const offset = inner * 0.15;
        return (
          <polygon
            points={`${pad + offset},${pad} ${size - pad - offset},${pad} ${size - pad},${size - pad} ${pad},${size - pad}`}
          />
        );
      }
      case 'rhombus':
        return (
          <polygon
            points={`${size / 2},${pad} ${size - pad},${size / 2} ${size / 2},${size - pad} ${pad},${size / 2}`}
          />
        );
      case 'parallelogram': {
        const skew = inner * 0.2;
        return (
          <polygon
            points={`${pad + skew},${pad} ${size - pad},${pad} ${size - pad - skew},${size - pad} ${pad},${size - pad}`}
          />
        );
      }
      case 'semicircle':
        return (
          <path
            d={`M ${pad},${size / 2} A ${inner / 2},${inner / 2} 0 0 1 ${size - pad},${size / 2} L ${pad},${size / 2} Z`}
          />
        );
      case 'freeform':
        return (
          <path
            d={`M ${pad + 5},${pad + 10} Q ${size / 2},${pad - 4} ${size - pad - 5},${pad + 10} Q ${size - pad + 2},${size / 2} ${size - pad - 5},${size - pad - 8} Q ${size / 2},${size - pad + 2} ${pad + 5},${size - pad - 8} Q ${pad - 2},${size / 2} ${pad + 5},${pad + 10} Z`}
          />
        );
      default:
        return null;
    }
  })();

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="flex-shrink-0"
    >
      <g fill="rgb(219 234 254)" stroke="rgb(59 130 246)" strokeWidth={1.5}>
        {svgContent}
      </g>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface ShapeDimensionEditorProps {
  shape: string;
  dimensions: Record<string, number> | null;
  onChange: (shape: string, dimensions: Record<string, number>, areaCm2: number) => void;
  disabled?: boolean;
}

export function ShapeDimensionEditor({
  shape,
  dimensions,
  onChange,
  disabled = false,
}: ShapeDimensionEditorProps) {
  const shapeDef = useMemo(() => getShapeDefinition(shape), [shape]);
  const currentDims = dimensions ?? {};

  const area = useMemo(() => {
    if (!shapeDef) return null;
    return shapeDef.area(currentDims);
  }, [shapeDef, currentDims]);

  const validationError = useMemo(() => {
    if (!shapeDef?.validate) return null;
    return shapeDef.validate(currentDims);
  }, [shapeDef, currentDims]);

  const handleShapeChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const newShape = e.target.value;
      const newDef = getShapeDefinition(newShape);
      const newDims: Record<string, number> = {};
      if (newDef) {
        // Preserve any overlapping keys
        for (const f of newDef.fields) {
          if (currentDims[f.key] != null) {
            newDims[f.key] = currentDims[f.key];
          }
        }
      }
      const newArea = newDef?.area(newDims);
      onChange(newShape, newDims, newArea ?? 0);
    },
    [currentDims, onChange],
  );

  const handleDimensionChange = useCallback(
    (key: string, raw: string) => {
      // Accept Russian decimal comma "14,14" as "14.14".
      const normalized = raw.replace(',', '.');
      const val = parseFloat(normalized);
      let newDims = { ...currentDims };
      if (normalized === '' || isNaN(val)) {
        delete newDims[key];
      } else {
        newDims[key] = val;
      }
      // Derive auto-computed fields (e.g. hypotenuse on right triangle).
      if (shapeDef?.derive) {
        newDims = shapeDef.derive(newDims);
      }
      const newArea = shapeDef?.area(newDims);
      onChange(shape, newDims, newArea ?? 0);
    },
    [shape, currentDims, shapeDef, onChange],
  );

  const shapeOptions = SHAPE_DEFINITIONS.map((s) => ({
    value: s.value,
    label: `${s.icon} ${s.label}`,
  }));

  return (
    <div className="space-y-3">
      {/* Shape selector */}
      <Select
        label="Shape"
        value={shape}
        onChange={handleShapeChange}
        options={shapeOptions}
        disabled={disabled}
      />

      {/* SVG preview + dimension inputs */}
      {shapeDef && (
        <div className="flex gap-4 items-start">
          <ShapePreview shape={shape} />
          <div className="flex-1 grid grid-cols-2 gap-2">
            {shapeDef.fields.map((f) => {
              const isDerived = f.derived === true;
              const val = currentDims[f.key];
              const displayVal =
                val != null
                  ? isDerived
                    ? Number(val.toFixed(2)).toString()
                    : String(val)
                  : '';
              return (
                <Input
                  key={f.key}
                  label={isDerived ? `${f.label} (auto)` : f.label}
                  type="number"
                  step="any"
                  min="0"
                  inputMode="decimal"
                  value={displayVal}
                  onChange={(e) => handleDimensionChange(f.key, e.target.value)}
                  disabled={disabled || isDerived}
                  placeholder="0"
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Validation error */}
      {validationError && (
        <p className="text-sm text-red-500 flex items-center gap-1">
          <span className="text-red-400">&#9888;</span>
          {validationError}
        </p>
      )}

      {/* Area display */}
      {area != null && area > 0 && (
        <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-sm text-gray-700">
          <span className="font-medium">Area:</span>{' '}
          <span className="font-mono">{area.toFixed(2)} cm&sup2;</span>
          <span className="text-gray-400 ml-2">
            ({(area / 10000).toFixed(4)} m&sup2;)
          </span>
        </div>
      )}
    </div>
  );
}
