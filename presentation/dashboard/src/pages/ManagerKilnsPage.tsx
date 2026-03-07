import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { useKilns, type KilnItem } from '@/hooks/useKilns';
import { useFactories } from '@/hooks/useFactories';
import { KilnCreateDialog } from '@/components/kilns/KilnCreateDialog';
import { KilnEditDialog } from '@/components/kilns/KilnEditDialog';
import { LoadingRulesDialog } from '@/components/kilns/LoadingRulesDialog';
import { KilnConstantsTable } from '@/components/kilns/KilnConstantsTable';

const KILN_TYPE_LABELS: Record<string, string> = { big: 'Large', small: 'Small', raku: 'Raku' };

function formatDims(d: { width: number; depth: number; height: number } | null) {
  if (!d) return '—';
  return `${d.width} × ${d.depth} × ${d.height} cm`;
}

export default function ManagerKilnsPage() {
  const { data: factoriesData } = useFactories();
  const factories = factoriesData?.items || [];

  // Default to first factory
  const [factoryId, setFactoryId] = useState('');
  const selectedFactory = factoryId || (factories.length > 0 ? factories[0].id : '');

  const { data: kilnsData, isLoading } = useKilns(
    selectedFactory ? { factory_id: selectedFactory } : undefined,
  );
  const kilns = kilnsData?.items || [];

  // Dialogs
  const [createOpen, setCreateOpen] = useState(false);
  const [editKiln, setEditKiln] = useState<KilnItem | null>(null);
  const [rulesKiln, setRulesKiln] = useState<KilnItem | null>(null);

  const factoryOptions = [
    ...(factories.length > 1 ? [{ value: '', label: 'All Factories' }] : []),
    ...factories.map((f) => ({ value: f.id, label: f.name })),
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kilns</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage kilns, loading rules, and constants
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} disabled={!selectedFactory}>
          + Add Kiln
        </Button>
      </div>

      {/* Factory filter */}
      {factories.length > 1 && (
        <div className="max-w-xs">
          <Select
            label="Factory"
            options={factoryOptions}
            value={factoryId}
            onChange={(e) => setFactoryId(e.target.value)}
          />
        </div>
      )}

      {/* Kiln Grid */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : kilns.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-lg font-medium text-gray-400">No kilns configured</p>
          <p className="mt-1 text-sm text-gray-400">
            Click &quot;Add Kiln&quot; to create your first kiln
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {kilns.map((kiln) => (
            <KilnCard
              key={kiln.id}
              kiln={kiln}
              onEdit={() => setEditKiln(kiln)}
              onRules={() => setRulesKiln(kiln)}
            />
          ))}
        </div>
      )}

      {/* Kiln Constants */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Kiln Constants</h2>
        <KilnConstantsTable />
      </div>

      {/* Dialogs */}
      <KilnCreateDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        factoryId={selectedFactory}
      />
      <KilnEditDialog
        open={!!editKiln}
        onClose={() => setEditKiln(null)}
        kiln={editKiln}
      />
      <LoadingRulesDialog
        open={!!rulesKiln}
        onClose={() => setRulesKiln(null)}
        kiln={rulesKiln}
      />
    </div>
  );
}

/* ---------- Kiln Card Component ---------- */

function KilnCard({
  kiln,
  onEdit,
  onRules,
}: {
  kiln: KilnItem;
  onEdit: () => void;
  onRules: () => void;
}) {
  const hasRules = !!kiln.loading_rules;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="mb-3 flex items-start justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900">{kiln.name}</h3>
          <span className="mt-0.5 inline-block rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
            {KILN_TYPE_LABELS[kiln.kiln_type] || kiln.kiln_type}
          </span>
        </div>
        <Badge status={kiln.status} />
      </div>

      {/* Specs */}
      <div className="space-y-1.5 text-sm text-gray-600">
        <div className="flex justify-between">
          <span className="text-gray-400">Working area</span>
          <span className="font-medium">{formatDims(kiln.kiln_working_area_cm)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Outer dims</span>
          <span>{formatDims(kiln.kiln_dimensions_cm)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Coefficient</span>
          <span className="font-medium">{kiln.kiln_coefficient ?? '—'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Levels</span>
          <span>
            {kiln.kiln_multi_level
              ? `${kiln.num_levels} (multi-level)`
              : `${kiln.num_levels} level`}
          </span>
        </div>
        {kiln.capacity_sqm != null && (
          <div className="flex justify-between">
            <span className="text-gray-400">Capacity</span>
            <span>{kiln.capacity_sqm} m²</span>
          </div>
        )}
      </div>

      {/* Loading rules indicator */}
      <div className="mt-3 flex items-center gap-1.5 text-xs">
        <span
          className={`inline-block h-2 w-2 rounded-full ${hasRules ? 'bg-green-400' : 'bg-gray-300'}`}
        />
        <span className="text-gray-500">
          {hasRules ? 'Loading rules configured' : 'No loading rules'}
        </span>
      </div>

      {/* Actions */}
      <div className="mt-4 flex gap-2 border-t pt-3">
        <Button size="sm" variant="ghost" onClick={onEdit}>
          Edit
        </Button>
        <Button size="sm" variant="ghost" onClick={onRules}>
          Rules
        </Button>
      </div>
    </div>
  );
}
