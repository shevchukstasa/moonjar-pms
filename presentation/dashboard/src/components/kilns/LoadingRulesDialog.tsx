import { useState, useEffect } from 'react';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useUpdateLoadingRules, useCreateLoadingRules, type KilnItem } from '@/hooks/useKilns';

const PRODUCT_TYPES = ['tile', 'countertop', 'sink', '3d'];

interface Props {
  open: boolean;
  onClose: () => void;
  kiln: KilnItem | null;
}

export function LoadingRulesDialog({ open, onClose, kiln }: Props) {
  const updateRules = useUpdateLoadingRules();
  const createRules = useCreateLoadingRules();
  const [submitError, setSubmitError] = useState('');

  // Form state
  const [allowedTypes, setAllowedTypes] = useState<string[]>([]);
  const [maxTemp, setMaxTemp] = useState(1200);
  const [edgeAllowed, setEdgeAllowed] = useState(true);
  const [coefficient, setCoefficient] = useState(0.8);
  const [levels, setLevels] = useState(1);
  const [maxTempDelta, setMaxTempDelta] = useState(50);

  useEffect(() => {
    if (kiln?.loading_rules) {
      const r = kiln.loading_rules as Record<string, unknown>;
      setAllowedTypes((r.allowed_product_types as string[]) || PRODUCT_TYPES);
      setMaxTemp((r.max_temperature as number) || 1200);
      setEdgeAllowed((r.edge_loading_allowed as boolean) ?? true);
      setCoefficient((r.coefficient as number) || kiln.kiln_coefficient || 0.8);
      setLevels((r.levels as number) || kiln.num_levels || 1);
      const cofiring = r.co_firing_restrictions as Record<string, unknown> | undefined;
      setMaxTempDelta((cofiring?.max_temp_delta as number) || 50);
    } else if (kiln) {
      setAllowedTypes(PRODUCT_TYPES);
      setMaxTemp(1200);
      setEdgeAllowed(true);
      setCoefficient(kiln.kiln_coefficient || 0.8);
      setLevels(kiln.num_levels || 1);
      setMaxTempDelta(50);
    }
  }, [kiln]);

  const toggleType = (t: string) => {
    setAllowedTypes((prev) => prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]);
  };

  const handleSave = async () => {
    if (!kiln) return;
    setSubmitError('');

    const rules = {
      allowed_product_types: allowedTypes,
      max_temperature: maxTemp,
      edge_loading_allowed: edgeAllowed,
      coefficient,
      levels,
      co_firing_restrictions: {
        max_temp_delta: maxTempDelta,
        excluded_glaze_combos: [],
      },
    };

    try {
      if (kiln.loading_rules_id) {
        await updateRules.mutateAsync({ id: kiln.loading_rules_id, rules });
      } else {
        await createRules.mutateAsync({ kiln_id: kiln.id, rules });
      }
      onClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setSubmitError(resp?.detail || 'Failed to save loading rules');
    }
  };

  if (!kiln) return null;

  return (
    <Dialog open={open} onClose={onClose} title={`Loading Rules — ${kiln.name}`} className="w-full max-w-md">
      <div className="space-y-4">
        {/* Allowed product types */}
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">Allowed Product Types</label>
          <div className="space-y-1.5">
            {PRODUCT_TYPES.map((t) => (
              <label key={t} className="flex items-center gap-2 text-sm capitalize">
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

        <Input
          label="Max Firing Temperature (°C)"
          type="number"
          value={maxTemp}
          onChange={(e) => setMaxTemp(Number(e.target.value))}
        />

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={edgeAllowed}
            onChange={(e) => setEdgeAllowed(e.target.checked)}
            className="rounded border-gray-300"
          />
          Edge loading allowed
        </label>

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Coefficient"
            type="number"
            step="0.01"
            value={coefficient}
            onChange={(e) => setCoefficient(Number(e.target.value))}
          />
          <Input
            label="Levels"
            type="number"
            value={levels}
            onChange={(e) => setLevels(Number(e.target.value))}
          />
        </div>

        <Input
          label="Co-firing: Max Temp Delta (°C)"
          type="number"
          value={maxTempDelta}
          onChange={(e) => setMaxTempDelta(Number(e.target.value))}
        />

        {submitError && <p className="text-sm text-red-500">{submitError}</p>}

        <div className="flex justify-end gap-3 border-t pt-4">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={updateRules.isPending || createRules.isPending}>
            {updateRules.isPending || createRules.isPending ? 'Saving...' : 'Save Rules'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
