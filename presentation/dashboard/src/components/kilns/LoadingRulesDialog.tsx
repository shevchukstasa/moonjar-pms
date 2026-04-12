import { useState, useEffect } from 'react';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  useUpdateLoadingRules,
  useCreateLoadingRules,
  useCollections,
  type KilnItem,
} from '@/hooks/useKilns';

const PRODUCT_TYPES = ['tile', 'countertop', 'sink', '3d', 'custom'];

// Default constants (match business/kiln/constants.py + kiln_constants table)
const DEFAULTS = {
  gap_x_cm: 1.2,
  gap_y_cm: 1.2,
  air_gap_cm: 2.0,
  shelf_thickness_cm: 3.0,
  max_edge_height_cm: 15,
  flat_on_edge_coefficient: 0.30,
  filler_coefficient: 0.50,
  min_space_to_fill_cm: 21,
};

interface Props {
  open: boolean;
  onClose: () => void;
  kiln: KilnItem | null;
}

export function LoadingRulesDialog({ open, onClose, kiln }: Props) {
  const updateRules = useUpdateLoadingRules();
  const createRules = useCreateLoadingRules();
  const { data: collectionsData } = useCollections();
  const collections = collectionsData?.items || [];
  const [submitError, setSubmitError] = useState('');

  // Product types
  const [allowedTypes, setAllowedTypes] = useState<string[]>([]);

  // Per-kiln gap overrides
  const [gapX, setGapX] = useState(DEFAULTS.gap_x_cm);
  const [gapY, setGapY] = useState(DEFAULTS.gap_y_cm);
  const [airGap, setAirGap] = useState(DEFAULTS.air_gap_cm);
  const [shelfThickness, setShelfThickness] = useState(DEFAULTS.shelf_thickness_cm);

  // Max product dimensions
  const [maxProductWidth, setMaxProductWidth] = useState<number | ''>('');
  const [maxProductHeight, setMaxProductHeight] = useState<number | ''>('');

  // Edge loading
  const [edgeAllowed, setEdgeAllowed] = useState(true);
  const [maxEdgeHeight, setMaxEdgeHeight] = useState(DEFAULTS.max_edge_height_cm);

  // Configurable loading coefficients
  const [flatOnEdgeCoeff, setFlatOnEdgeCoeff] = useState(DEFAULTS.flat_on_edge_coefficient);
  const [fillerEnabled, setFillerEnabled] = useState(true);
  const [fillerCoeff, setFillerCoeff] = useState(DEFAULTS.filler_coefficient);
  const [minSpaceToFill, setMinSpaceToFill] = useState(DEFAULTS.min_space_to_fill_cm);

  // Allowed collections
  const [allowedCollections, setAllowedCollections] = useState<string[]>([]);

  useEffect(() => {
    if (kiln?.loading_rules) {
      const r = kiln.loading_rules as Record<string, unknown>;
      setAllowedTypes((r.allowed_product_types as string[]) || PRODUCT_TYPES);
      setGapX((r.gap_x_cm as number) ?? DEFAULTS.gap_x_cm);
      setGapY((r.gap_y_cm as number) ?? DEFAULTS.gap_y_cm);
      setAirGap((r.air_gap_cm as number) ?? DEFAULTS.air_gap_cm);
      setShelfThickness((r.shelf_thickness_cm as number) ?? DEFAULTS.shelf_thickness_cm);
      setMaxProductWidth((r.max_product_width_cm as number) || '');
      setMaxProductHeight((r.max_product_height_cm as number) || '');
      setEdgeAllowed((r.edge_loading_allowed as boolean) ?? true);
      setMaxEdgeHeight((r.max_edge_height_cm as number) ?? DEFAULTS.max_edge_height_cm);
      setFlatOnEdgeCoeff((r.flat_on_edge_coefficient as number) ?? DEFAULTS.flat_on_edge_coefficient);
      setFillerEnabled((r.filler_enabled as boolean) ?? true);
      setFillerCoeff((r.filler_coefficient as number) ?? DEFAULTS.filler_coefficient);
      setMinSpaceToFill((r.min_space_to_fill_cm as number) ?? DEFAULTS.min_space_to_fill_cm);
      setAllowedCollections((r.allowed_collections as string[]) || []);
    } else if (kiln) {
      setAllowedTypes(PRODUCT_TYPES);
      setGapX(DEFAULTS.gap_x_cm);
      setGapY(DEFAULTS.gap_y_cm);
      setAirGap(DEFAULTS.air_gap_cm);
      setShelfThickness(DEFAULTS.shelf_thickness_cm);
      setMaxProductWidth('');
      setMaxProductHeight('');
      setEdgeAllowed(true);
      setMaxEdgeHeight(DEFAULTS.max_edge_height_cm);
      setFlatOnEdgeCoeff(DEFAULTS.flat_on_edge_coefficient);
      setFillerEnabled(true);
      setFillerCoeff(DEFAULTS.filler_coefficient);
      setMinSpaceToFill(DEFAULTS.min_space_to_fill_cm);
      setAllowedCollections([]);
    }
  }, [kiln]);

  const toggleType = (t: string) => {
    setAllowedTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
    );
  };

  const toggleCollection = (name: string) => {
    setAllowedCollections((prev) =>
      prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name],
    );
  };

  const handleSave = async () => {
    if (!kiln) return;
    setSubmitError('');

    const rules: Record<string, unknown> = {
      allowed_product_types: allowedTypes,
      gap_x_cm: gapX,
      gap_y_cm: gapY,
      air_gap_cm: airGap,
      shelf_thickness_cm: shelfThickness,
      edge_loading_allowed: edgeAllowed,
      max_edge_height_cm: maxEdgeHeight,
      flat_on_edge_coefficient: flatOnEdgeCoeff,
      filler_enabled: fillerEnabled,
      filler_coefficient: fillerCoeff,
      min_space_to_fill_cm: minSpaceToFill,
      allowed_collections: allowedCollections,
    };

    // Only include max dims if set
    if (maxProductWidth !== '' && maxProductWidth > 0) {
      rules.max_product_width_cm = maxProductWidth;
    }
    if (maxProductHeight !== '' && maxProductHeight > 0) {
      rules.max_product_height_cm = maxProductHeight;
    }

    try {
      if (kiln.loading_rules_id) {
        await updateRules.mutateAsync({ id: kiln.loading_rules_id, rules });
      } else {
        await createRules.mutateAsync({ kiln_id: kiln.id, rules });
      }
      onClose();
    } catch (err: unknown) {
      const data = (err as { response?: { data?: unknown } })?.response?.data;
      let msg = 'Failed to save loading rules';
      if (data && typeof data === 'object') {
        const detail = (data as { detail?: unknown }).detail;
        if (typeof detail === 'string') {
          msg = detail;
        } else if (Array.isArray(detail)) {
          msg = detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ') || msg;
        }
      } else if (typeof data === 'string' && data.length < 200) {
        msg = data;
      }
      setSubmitError(msg);
    }
  };

  if (!kiln) return null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`Loading Rules — ${kiln.name}`}
      className="w-full max-w-lg"
    >
      <div className="max-h-[70vh] space-y-5 overflow-y-auto pr-1">
        {/* Allowed product types */}
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Allowed Product Types
          </label>
          <div className="flex flex-wrap gap-3">
            {PRODUCT_TYPES.map((t) => (
              <label key={t} className="flex items-center gap-1.5 text-sm capitalize">
                <input
                  type="checkbox"
                  checked={allowedTypes.includes(t)}
                  onChange={() => toggleType(t)}
                  className="rounded border-gray-300"
                />
                {t}
              </label>
            ))}
          </div>
        </div>

        {/* Per-kiln gap parameters */}
        <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
          <label className="mb-2 block text-sm font-semibold text-gray-700">
            Loading Parameters (overrides defaults)
          </label>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Tile Gap X (cm)"
              type="number"
              step="0.1"
              value={gapX}
              onChange={(e) => setGapX(Number(e.target.value))}
            />
            <Input
              label="Tile Gap Y (cm)"
              type="number"
              step="0.1"
              value={gapY}
              onChange={(e) => setGapY(Number(e.target.value))}
            />
            <Input
              label="Air Gap (cm)"
              type="number"
              step="0.1"
              value={airGap}
              onChange={(e) => setAirGap(Number(e.target.value))}
            />
            <Input
              label="Shelf Thickness (cm)"
              type="number"
              step="0.1"
              value={shelfThickness}
              onChange={(e) => setShelfThickness(Number(e.target.value))}
            />
          </div>
        </div>

        {/* Max product dimensions */}
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Max Product Dimensions (cm)
          </label>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Max Width"
              type="number"
              step="1"
              placeholder="No limit"
              value={maxProductWidth}
              onChange={(e) =>
                setMaxProductWidth(e.target.value ? Number(e.target.value) : '')
              }
            />
            <Input
              label="Max Height"
              type="number"
              step="1"
              placeholder="No limit"
              value={maxProductHeight}
              onChange={(e) =>
                setMaxProductHeight(e.target.value ? Number(e.target.value) : '')
              }
            />
          </div>
        </div>

        {/* Edge loading */}
        <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
          <label className="mb-2 block text-sm font-semibold text-gray-700">
            Edge Loading
          </label>
          <label className="mb-3 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={edgeAllowed}
              onChange={(e) => setEdgeAllowed(e.target.checked)}
              className="rounded border-gray-300"
            />
            Edge loading allowed for this kiln
          </label>
          {edgeAllowed && (
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Max Edge Height (cm)"
                type="number"
                step="1"
                value={maxEdgeHeight}
                onChange={(e) => setMaxEdgeHeight(Number(e.target.value))}
              />
              <Input
                label="Flat-on-top fraction"
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={flatOnEdgeCoeff}
                onChange={(e) => setFlatOnEdgeCoeff(Number(e.target.value))}
              />
            </div>
          )}
        </div>

        {/* Filler (small-kiln leftover space) */}
        <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
          <label className="mb-2 block text-sm font-semibold text-gray-700">
            Filler Tiles (leftover space)
          </label>
          <label className="mb-3 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={fillerEnabled}
              onChange={(e) => setFillerEnabled(e.target.checked)}
              className="rounded border-gray-300"
            />
            Fill leftover shelf space with 10×10 tiles on edge
          </label>
          {fillerEnabled && (
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Min space to fill (cm)"
                type="number"
                step="1"
                value={minSpaceToFill}
                onChange={(e) => setMinSpaceToFill(Number(e.target.value))}
              />
              <Input
                label="Filler load factor"
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={fillerCoeff}
                onChange={(e) => setFillerCoeff(Number(e.target.value))}
              />
            </div>
          )}
        </div>

        {/* Allowed collections */}
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Allowed Collections
            {allowedCollections.length === 0 && (
              <span className="ml-2 text-xs font-normal text-gray-400">(all allowed)</span>
            )}
          </label>
          <div className="flex flex-wrap gap-2">
            {collections.map((c) => (
              <label
                key={c.id}
                className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors ${
                  allowedCollections.includes(c.name)
                    ? 'border-blue-300 bg-blue-50 text-blue-700'
                    : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={allowedCollections.includes(c.name)}
                  onChange={() => toggleCollection(c.name)}
                  className="sr-only"
                />
                {c.name}
              </label>
            ))}
            {collections.length === 0 && (
              <p className="text-xs text-gray-400">
                No collections in database. Add them via reference data.
              </p>
            )}
          </div>
        </div>

        {submitError && <p className="text-sm text-red-500">{submitError}</p>}

        <div className="flex justify-end gap-3 border-t pt-4">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={updateRules.isPending || createRules.isPending}
          >
            {updateRules.isPending || createRules.isPending ? 'Saving...' : 'Save Rules'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
