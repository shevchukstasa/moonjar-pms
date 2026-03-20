import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useBlockingSummary } from '@/hooks/usePositions';
import { positionsApi } from '@/api/positions';
import { recipesApi, type RecipeItem } from '@/api/recipes';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { ForceUnblockDialog } from './ForceUnblockDialog';
import { MaterialReservationsPanel } from './MaterialReservationsPanel';
import type { BlockedPositionInfo } from '@/api/positions';

interface BlockingTasksTabProps {
  factoryId?: string;
}

const STATUS_LABELS: Record<string, string> = {
  insufficient_materials: 'Insufficient Materials',
  awaiting_recipe: 'Awaiting Recipe',
  awaiting_stencil_silkscreen: 'Stencil / Silkscreen',
  awaiting_color_matching: 'Color Matching',
  awaiting_size_confirmation: 'Awaiting Size',
  blocked_by_qm: 'QM Block',
};

const STATUS_BADGE_COLORS: Record<string, string> = {
  insufficient_materials: 'bg-red-100 text-red-800 border-red-200',
  awaiting_recipe: 'bg-purple-100 text-purple-800 border-purple-200',
  awaiting_stencil_silkscreen: 'bg-amber-100 text-amber-800 border-amber-200',
  awaiting_color_matching: 'bg-orange-100 text-orange-800 border-orange-200',
  awaiting_size_confirmation: 'bg-cyan-100 text-cyan-800 border-cyan-200',
  blocked_by_qm: 'bg-pink-100 text-pink-800 border-pink-200',
};

const KPI_ICONS: Record<string, string> = {
  insufficient_materials: '📦',
  awaiting_recipe: '📋',
  awaiting_stencil_silkscreen: '🖼',
  awaiting_color_matching: '🎨',
  awaiting_size_confirmation: '📏',
  blocked_by_qm: '🔍',
};

function timeSince(dateStr: string | null): string {
  if (!dateStr) return '—';
  const ms = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(ms / 3_600_000);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function BlockingTasksTab({ factoryId }: BlockingTasksTabProps) {
  const navigate = useNavigate();
  const { data, isLoading, error } = useBlockingSummary(factoryId);
  const [unblockTarget, setUnblockTarget] = useState<BlockedPositionInfo | null>(null);
  const [materialsTarget, setMaterialsTarget] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);
  const [recipeAssignTarget, setRecipeAssignTarget] = useState<BlockedPositionInfo | null>(null);

  if (isLoading) {
    return <div className="flex justify-center py-12"><Spinner /></div>;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-800">Error loading blocking summary</p>
      </div>
    );
  }

  if (!data || data.total_blocked === 0) {
    return (
      <EmptyState
        title="No blocked positions"
        description="All positions are clear — no blocking tasks at this time."
      />
    );
  }

  const filteredPositions = filterStatus
    ? data.positions.filter((p) => p.status === filterStatus)
    : data.positions;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Total */}
        <Card className={`p-4 cursor-pointer transition-all ${filterStatus === null ? 'ring-2 ring-blue-400' : 'hover:shadow-md'}`}
          onClick={() => setFilterStatus(null)}
        >
          <div className="text-2xl font-bold text-gray-900">{data.total_blocked}</div>
          <div className="text-xs text-gray-500 mt-1">Total Blocked</div>
        </Card>
        {/* Per-type */}
        {Object.entries(data.by_type).map(([status, count]) => count > 0 && (
          <Card
            key={status}
            className={`p-4 cursor-pointer transition-all ${filterStatus === status ? 'ring-2 ring-blue-400' : 'hover:shadow-md'}`}
            onClick={() => setFilterStatus(filterStatus === status ? null : status)}
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">{KPI_ICONS[status] || '🚫'}</span>
              <span className="text-xl font-bold text-gray-900">{count}</span>
            </div>
            <div className="text-xs text-gray-500 mt-1">{STATUS_LABELS[status] || status}</div>
          </Card>
        ))}
      </div>

      {/* Positions Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-4 py-3">Order / Position</th>
              <th className="px-4 py-3">Color & Size</th>
              <th className="px-4 py-3">Qty</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Blocked Since</th>
              <th className="px-4 py-3">Details</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredPositions.map((p) => (
              <tr key={p.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{p.order_number}</div>
                  <div className="text-xs text-gray-400">{p.position_label}</div>
                </td>
                <td className="px-4 py-3">
                  <div className="text-gray-800">{p.color}</div>
                  <div className="text-xs text-gray-400">{p.size}{p.collection ? ` · ${p.collection}` : ''}</div>
                </td>
                <td className="px-4 py-3 text-gray-700">{p.quantity}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE_COLORS[p.status] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>
                    {STATUS_LABELS[p.status] || p.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {timeSince(p.blocking_since)}
                </td>
                <td className="px-4 py-3">
                  {/* Material shortages */}
                  {p.material_shortages.length > 0 && (
                    <div className="space-y-0.5">
                      {p.material_shortages.slice(0, 3).map((s, i) => (
                        <div key={i} className="text-xs text-red-600">
                          {s.name}: <span className="font-mono">−{s.deficit.toFixed(1)}</span>
                        </div>
                      ))}
                      {p.material_shortages.length > 3 && (
                        <div className="text-xs text-gray-400">+{p.material_shortages.length - 3} more…</div>
                      )}
                    </div>
                  )}
                  {/* Related tasks */}
                  {p.related_tasks.length > 0 && p.material_shortages.length === 0 && (
                    <div className="space-y-0.5">
                      {p.related_tasks.map((t) => (
                        <div key={t.task_id} className="text-xs text-gray-500">
                          {t.type}: {t.status}
                        </div>
                      ))}
                    </div>
                  )}
                  {p.material_shortages.length === 0 && p.related_tasks.length === 0 && (
                    <span className="text-xs text-gray-400">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {p.recipe_id && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setMaterialsTarget(p.id)}
                      >
                        Materials
                      </Button>
                    )}
                    {p.status === 'awaiting_recipe' && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setRecipeAssignTarget(p)}
                      >
                        Assign Recipe
                      </Button>
                    )}
                    {p.status === 'awaiting_size_confirmation' && p.related_tasks.length > 0 && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          const sizeTask = p.related_tasks.find((t) => t.type === 'size_resolution');
                          if (sizeTask) navigate(`/manager/size-resolution/${sizeTask.task_id}`);
                        }}
                      >
                        Resolve Size
                      </Button>
                    )}
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setUnblockTarget(p)}
                    >
                      Force Unblock
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredPositions.length === 0 && (
          <div className="py-8 text-center text-sm text-gray-400">
            No positions matching this filter
          </div>
        )}
      </div>

      {/* Force Unblock Dialog */}
      {unblockTarget && (
        <ForceUnblockDialog
          positionId={unblockTarget.id}
          positionLabel={`${unblockTarget.order_number} ${unblockTarget.position_label}`}
          currentStatus={unblockTarget.status}
          onClose={() => setUnblockTarget(null)}
        />
      )}

      {/* Material Reservations Panel */}
      {materialsTarget && (
        <MaterialReservationsPanel
          positionId={materialsTarget}
          onClose={() => setMaterialsTarget(null)}
        />
      )}

      {/* Recipe Assign Dialog */}
      {recipeAssignTarget && (
        <RecipeAssignDialog
          position={recipeAssignTarget}
          onClose={() => setRecipeAssignTarget(null)}
        />
      )}
    </div>
  );
}

/* ── RecipeAssignDialog ────────────────────────────────────────────── */

function RecipeAssignDialog({ position, onClose }: { position: BlockedPositionInfo; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [selectedRecipeId, setSelectedRecipeId] = useState<string | null>(null);
  const [error, setError] = useState('');

  const { data: recipesData, isLoading: recipesLoading } = useQuery<{ items: RecipeItem[]; total: number }>({
    queryKey: ['recipes-for-assign'],
    queryFn: () => recipesApi.list({ per_page: 500 }),
  });

  const recipes = recipesData?.items ?? [];

  const filtered = useMemo(() => {
    if (!search.trim()) return recipes.filter((r) => r.is_active);
    const q = search.toLowerCase();
    return recipes
      .filter((r) => r.is_active)
      .filter(
        (r) =>
          r.name.toLowerCase().includes(q) ||
          (r.color_collection && r.color_collection.toLowerCase().includes(q)) ||
          (r.client_name && r.client_name.toLowerCase().includes(q)),
      );
  }, [recipes, search]);

  const assignMutation = useMutation({
    mutationFn: async () => {
      if (!selectedRecipeId) throw new Error('No recipe selected');
      // 1. PATCH position with recipe_id
      await positionsApi.update(position.id, { recipe_id: selectedRecipeId });
      // 2. Force-unblock to move past awaiting_recipe now that recipe is assigned
      await positionsApi.forceUnblock(position.id, `Recipe assigned: ${recipes.find((r) => r.id === selectedRecipeId)?.name ?? selectedRecipeId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['blocking-summary'] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      onClose();
    },
    onError: (err: unknown) => {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setError(resp?.detail || (err instanceof Error ? err.message : String(err)));
    },
  });

  const selectedRecipe = recipes.find((r) => r.id === selectedRecipeId);

  return (
    <Dialog open onClose={onClose} title="Assign Recipe" className="w-full max-w-lg">
      <div className="space-y-4">
        {/* Position info */}
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
          <div className="text-sm">
            <span className="font-medium text-gray-900">{position.order_number}</span>
            <span className="mx-1 text-gray-400">/</span>
            <span className="text-gray-600">{position.position_label}</span>
          </div>
          <div className="mt-0.5 text-sm text-gray-600">
            Color: <span className="font-medium">{position.color}</span>
            {position.collection && (
              <span className="ml-2 text-gray-400">({position.collection})</span>
            )}
          </div>
        </div>

        {/* Search */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Search recipes</label>
          <input
            type="text"
            placeholder="Type to search by name, collection, or client..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            autoFocus
          />
        </div>

        {/* Recipe list */}
        <div className="max-h-60 overflow-y-auto rounded-lg border border-gray-200">
          {recipesLoading ? (
            <div className="flex justify-center py-6"><Spinner /></div>
          ) : filtered.length === 0 ? (
            <div className="py-6 text-center text-sm text-gray-400">
              {search ? 'No recipes match your search' : 'No active recipes found'}
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filtered.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setSelectedRecipeId(r.id)}
                  className={`w-full px-3 py-2 text-left text-sm transition-colors hover:bg-blue-50 ${
                    selectedRecipeId === r.id ? 'bg-blue-50 ring-1 ring-inset ring-blue-300' : ''
                  }`}
                >
                  <div className="font-medium text-gray-900">{r.name}</div>
                  <div className="mt-0.5 flex items-center gap-3 text-xs text-gray-500">
                    {r.color_collection && <span>Collection: {r.color_collection}</span>}
                    {r.recipe_type && <span>Type: {r.recipe_type}</span>}
                    {r.client_name && <span>Client: {r.client_name}</span>}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Selected recipe summary */}
        {selectedRecipe && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800">
            Selected: <span className="font-medium">{selectedRecipe.name}</span>
            {selectedRecipe.color_collection && (
              <span className="ml-1 text-blue-600">({selectedRecipe.color_collection})</span>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => assignMutation.mutate()}
            disabled={!selectedRecipeId || assignMutation.isPending}
          >
            {assignMutation.isPending ? 'Assigning...' : 'Assign'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
