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
  fields: { key: string; label: string; unit: string }[];
  /** Returns area in cm^2 given numeric dimension values, or null if invalid */
  area: (d: Record<string, number>) => number | null;
  /** Optional extra validation; returns error string or null */
  validate?: (d: Record<string, number>) => string | null;
}

export const SHAPE_DEFINITIONS: ShapeDefinition[] = [
  {
    value: 'rectangle',
    label: 'Rectangle',
    icon: '\u25AC',
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
    icon: '\u2B1C',
    fields: [{ key: 'side', label: 'Side (cm)', unit: 'cm' }],
    area: (d) => {
      const s = d.side;
      if (!s || s <= 0) return null;
      return s * s;
    },
  },
  {
    value: 'triangle',
    label: 'Triangle',
    icon: '\uD83D\uDD3A',
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
    icon: '\u2B55',
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
    icon: '\u2B2D',
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
    icon: '\uD83D\uDED1',
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
    icon: '\u23E2',
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
    icon: '\u23E2',
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
    icon: '\u25C7',
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
    icon: '\u25B1',
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
    icon: '\u25D1',
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
    icon: '\u2B50',
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
      const val = parseFloat(raw);
      const newDims = { ...currentDims };
      if (raw === '' || isNaN(val)) {
        delete newDims[key];
      } else {
        newDims[key] = val;
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
            {shapeDef.fields.map((f) => (
              <Input
                key={f.key}
                label={f.label}
                type="number"
                step="any"
                min="0"
                value={currentDims[f.key] != null ? String(currentDims[f.key]) : ''}
                onChange={(e) => handleDimensionChange(f.key, e.target.value)}
                disabled={disabled}
                placeholder="0"
              />
            ))}
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
