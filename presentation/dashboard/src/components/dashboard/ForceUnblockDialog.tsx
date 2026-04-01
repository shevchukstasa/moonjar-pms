import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Spinner } from '@/components/ui/Spinner';
import { useForceUnblock, useUpdatePosition } from '@/hooks/usePositions';
import { recipesApi, type RecipeItem } from '@/api/recipes';
import { positionsApi } from '@/api/positions';
import { ClipboardList, Plus, Zap, ArrowLeft, AlertTriangle, Package, CheckCircle } from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────
interface ForceUnblockDialogProps {
  positionId: string;
  positionLabel: string;
  currentStatus: string;
  color: string;
  collection: string | null;
  onClose: () => void;
}

type DialogMode = 'choose' | 'select_recipe' | 'create_recipe' | 'force_override';

const STATUS_LABELS: Record<string, string> = {
  insufficient_materials: 'Insufficient Materials',
  awaiting_recipe: 'Awaiting Recipe',
  awaiting_stencil_silkscreen: 'Awaiting Stencil/Silkscreen',
  awaiting_color_matching: 'Awaiting Color Matching',
  blocked_by_qm: 'Blocked by QM',
};

// ─── Option Card ────────────────────────────────────────────────
function OptionCard({
  icon,
  title,
  description,
  onClick,
  variant = 'primary',
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
}) {
  const variantClasses = {
    primary:
      'border-amber-200 bg-amber-50 hover:bg-amber-100 hover:border-amber-300 dark:border-amber-700/50 dark:bg-amber-900/20 dark:hover:bg-amber-900/30',
    secondary:
      'border-gray-200 bg-gray-50 hover:bg-gray-100 hover:border-gray-300 dark:border-stone-600 dark:bg-stone-800 dark:hover:bg-stone-700',
    danger:
      'border-red-200 bg-red-50 hover:bg-red-100 hover:border-red-300 dark:border-red-700/50 dark:bg-red-900/20 dark:hover:bg-red-900/30',
  };
  const iconClasses = {
    primary: 'text-amber-600 dark:text-amber-400',
    secondary: 'text-gray-500 dark:text-stone-400',
    danger: 'text-red-500 dark:text-red-400',
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-col items-center gap-2 rounded-xl border p-4 text-center transition-all ${variantClasses[variant]}`}
    >
      <div className={`${iconClasses[variant]}`}>{icon}</div>
      <div className="text-sm font-semibold text-gray-900 dark:text-stone-100">{title}</div>
      <div className="text-xs text-gray-500 dark:text-stone-400 leading-tight">{description}</div>
    </button>
  );
}

// ─── Main Dialog ────────────────────────────────────────────────
export function ForceUnblockDialog({
  positionId,
  positionLabel,
  currentStatus,
  color,
  collection,
  onClose,
}: ForceUnblockDialogProps) {
  const queryClient = useQueryClient();
  const forceUnblock = useForceUnblock();
  const updatePosition = useUpdatePosition();

  // Dialog mode
  const [mode, setMode] = useState<DialogMode>('choose');

  // Force override state
  const [overrideNotes, setOverrideNotes] = useState('');

  // Select recipe state
  const [search, setSearch] = useState('');
  const [selectedRecipeId, setSelectedRecipeId] = useState<string | null>(null);

  // Create recipe state
  const [newRecipeName, setNewRecipeName] = useState(color || '');
  const [newRecipeType, setNewRecipeType] = useState<'glaze' | 'engobe'>('glaze');
  const [newRecipeCollection, setNewRecipeCollection] = useState(collection || '');

  const [error, setError] = useState('');

  // Fetch recipes for select mode
  const { data: recipesData, isLoading: recipesLoading } = useQuery<{ items: RecipeItem[]; total: number }>({
    queryKey: ['recipes-for-assign'],
    queryFn: () => recipesApi.list({ per_page: 500 }),
    enabled: mode === 'select_recipe',
  });
  const recipes = recipesData?.items ?? [];
  const filtered = useMemo(() => {
    const active = recipes.filter((r) => r.is_active);
    if (!search.trim()) return active;
    const q = search.toLowerCase();
    return active.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        (r.color_collection && r.color_collection.toLowerCase().includes(q)) ||
        (r.client_name && r.client_name.toLowerCase().includes(q)),
    );
  }, [recipes, search]);
  const selectedRecipe = recipes.find((r) => r.id === selectedRecipeId);

  // Assign recipe mutation (select existing)
  const assignMutation = useMutation({
    mutationFn: async () => {
      if (!selectedRecipeId) throw new Error('No recipe selected');
      await positionsApi.update(positionId, { recipe_id: selectedRecipeId });
      const recipeName = recipes.find((r) => r.id === selectedRecipeId)?.name ?? selectedRecipeId;
      await positionsApi.forceUnblock(positionId, `Recipe assigned: ${recipeName}`);
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

  // Create recipe + assign mutation
  const createAssignMutation = useMutation({
    mutationFn: async () => {
      if (!newRecipeName.trim()) throw new Error('Recipe name is required');
      const created = await recipesApi.create({
        name: newRecipeName.trim(),
        recipe_type: newRecipeType,
        color_collection: newRecipeCollection.trim() || null,
        is_active: true,
      });
      const recipeId = created.id;
      await positionsApi.update(positionId, { recipe_id: recipeId });
      await positionsApi.forceUnblock(positionId, `New recipe created & assigned: ${newRecipeName.trim()}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['blocking-summary'] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      onClose();
    },
    onError: (err: unknown) => {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setError(resp?.detail || (err instanceof Error ? err.message : String(err)));
    },
  });

  // Force override submit
  const handleForceOverride = () => {
    if (!overrideNotes.trim()) return;
    setError('');
    forceUnblock.mutate(
      { id: positionId, notes: overrideNotes.trim(), notify_override: true },
      {
        onSuccess: (data) => {
          if (data.negative_balances && data.negative_balances.length > 0) {
            alert(
              `Force-unblocked! ${data.negative_balances.length} material(s) went to negative balance.\n\n` +
                data.negative_balances
                  .map(
                    (nb: { material_name: string; resulting_effective: number }) =>
                      `- ${nb.material_name}: effective balance = ${nb.resulting_effective.toFixed(2)}`,
                  )
                  .join('\n') +
                '\n\nAdjust during next inventory count.',
            );
          }
          onClose();
        },
        onError: (err: unknown) => {
          const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
          setError(resp?.detail || (err instanceof Error ? err.message : String(err)));
        },
      },
    );
  };

  // Mark ready (for stencil/silkscreen)
  const handleMarkReady = () => {
    setError('');
    forceUnblock.mutate(
      { id: positionId, notes: 'Stencil/silkscreen marked as ready by PM' },
      {
        onSuccess: () => onClose(),
        onError: (err: unknown) => {
          const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
          setError(resp?.detail || (err instanceof Error ? err.message : String(err)));
        },
      },
    );
  };

  const isPending =
    forceUnblock.isPending || assignMutation.isPending || createAssignMutation.isPending;

  // Determine which options to show based on status
  const getChooseOptions = () => {
    if (currentStatus === 'awaiting_recipe') {
      return (
        <div className="grid grid-cols-3 gap-3">
          <OptionCard
            icon={<ClipboardList className="h-6 w-6" />}
            title="Select Recipe"
            description="Choose from existing recipes"
            onClick={() => { setMode('select_recipe'); setError(''); }}
            variant="primary"
          />
          <OptionCard
            icon={<Plus className="h-6 w-6" />}
            title="Create Recipe"
            description="Create a new recipe for this color"
            onClick={() => { setMode('create_recipe'); setError(''); }}
            variant="secondary"
          />
          <OptionCard
            icon={<Zap className="h-6 w-6" />}
            title="Force Override"
            description="Proceed without recipe. CEO will be notified via Telegram."
            onClick={() => { setMode('force_override'); setError(''); }}
            variant="danger"
          />
        </div>
      );
    }

    if (currentStatus === 'insufficient_materials') {
      return (
        <div className="grid grid-cols-3 gap-3">
          <OptionCard
            icon={<Package className="h-6 w-6" />}
            title="Order Materials"
            description="Create purchase request for missing materials"
            onClick={() => {
              // For now, go to force override with pre-filled note
              setOverrideNotes('Materials ordered, production can proceed');
              setMode('force_override');
              setError('');
            }}
            variant="primary"
          />
          <OptionCard
            icon={<CheckCircle className="h-6 w-6" />}
            title="Receive Stock"
            description="Stock has arrived, re-check reservations"
            onClick={() => {
              setOverrideNotes('Stock received, materials now available');
              setMode('force_override');
              setError('');
            }}
            variant="secondary"
          />
          <OptionCard
            icon={<Zap className="h-6 w-6" />}
            title="Force Override"
            description="Force-reserve even if stock is insufficient. CEO notified."
            onClick={() => { setMode('force_override'); setError(''); }}
            variant="danger"
          />
        </div>
      );
    }

    if (currentStatus === 'awaiting_stencil_silkscreen') {
      return (
        <div className="grid grid-cols-2 gap-3 max-w-sm mx-auto">
          <OptionCard
            icon={<CheckCircle className="h-6 w-6" />}
            title="Mark Ready"
            description="Stencil/silkscreen is ready, proceed"
            onClick={handleMarkReady}
            variant="primary"
          />
          <OptionCard
            icon={<Zap className="h-6 w-6" />}
            title="Force Override"
            description="Proceed without confirmation. CEO notified."
            onClick={() => { setMode('force_override'); setError(''); }}
            variant="danger"
          />
        </div>
      );
    }

    // Default: only force override
    return (
      <div className="max-w-xs mx-auto">
        <OptionCard
          icon={<Zap className="h-6 w-6" />}
          title="Force Override"
          description="Override this blocking status. CEO will be notified."
          onClick={() => { setMode('force_override'); setError(''); }}
          variant="danger"
        />
      </div>
    );
  };

  const dialogTitle =
    mode === 'choose'
      ? 'Resolve Blocking'
      : mode === 'select_recipe'
        ? 'Select Recipe'
        : mode === 'create_recipe'
          ? 'Create Recipe'
          : 'Force Override';

  return (
    <Dialog open onClose={onClose} title={dialogTitle} className="w-full max-w-lg">
      <div className="space-y-4">
        {/* Position info */}
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 dark:border-stone-700 dark:bg-stone-800">
          <div className="text-sm">
            <span className="font-medium text-gray-900 dark:text-stone-100">{positionLabel}</span>
          </div>
          <div className="mt-0.5 flex items-center gap-3 text-sm text-gray-600 dark:text-stone-400">
            <span>
              Status:{' '}
              <span className="font-medium text-orange-600 dark:text-orange-400">
                {STATUS_LABELS[currentStatus] || currentStatus}
              </span>
            </span>
            {color && <span>Color: <span className="font-medium">{color}</span></span>}
          </div>
        </div>

        {/* Step 1: Choose mode */}
        {mode === 'choose' && getChooseOptions()}

        {/* Step 2a: Select Recipe */}
        {mode === 'select_recipe' && (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => { setMode('choose'); setError(''); }}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-stone-400 dark:hover:text-stone-200"
            >
              <ArrowLeft className="h-4 w-4" /> Back
            </button>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">
                Search recipes
              </label>
              <input
                type="text"
                placeholder="Type to search by name, collection, or client..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-100"
                autoFocus
              />
            </div>

            <div className="max-h-60 overflow-y-auto rounded-lg border border-gray-200 dark:border-stone-600">
              {recipesLoading ? (
                <div className="flex justify-center py-6">
                  <Spinner />
                </div>
              ) : filtered.length === 0 ? (
                <div className="py-6 text-center text-sm text-gray-400 dark:text-stone-500">
                  {search ? 'No recipes match your search' : 'No active recipes found'}
                </div>
              ) : (
                <div className="divide-y divide-gray-100 dark:divide-stone-700">
                  {filtered.map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => setSelectedRecipeId(r.id)}
                      className={`w-full px-3 py-2 text-left text-sm transition-colors hover:bg-blue-50 dark:hover:bg-stone-700 ${
                        selectedRecipeId === r.id
                          ? 'bg-blue-50 ring-1 ring-inset ring-blue-300 dark:bg-stone-700 dark:ring-amber-500'
                          : ''
                      }`}
                    >
                      <div className="font-medium text-gray-900 dark:text-stone-100">{r.name}</div>
                      <div className="mt-0.5 flex items-center gap-3 text-xs text-gray-500 dark:text-stone-400">
                        {r.color_collection && <span>Collection: {r.color_collection}</span>}
                        {r.recipe_type && <span>Type: {r.recipe_type}</span>}
                        {r.client_name && <span>Client: {r.client_name}</span>}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {selectedRecipe && (
              <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800 dark:border-blue-700/50 dark:bg-blue-900/20 dark:text-blue-300">
                Selected: <span className="font-medium">{selectedRecipe.name}</span>
                {selectedRecipe.color_collection && (
                  <span className="ml-1 text-blue-600 dark:text-blue-400">
                    ({selectedRecipe.color_collection})
                  </span>
                )}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <Button variant="secondary" onClick={onClose} disabled={isPending}>
                Cancel
              </Button>
              <Button
                onClick={() => { setError(''); assignMutation.mutate(); }}
                disabled={!selectedRecipeId || isPending}
              >
                {assignMutation.isPending ? 'Assigning...' : 'Assign & Unblock'}
              </Button>
            </div>
          </div>
        )}

        {/* Step 2b: Create Recipe */}
        {mode === 'create_recipe' && (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => { setMode('choose'); setError(''); }}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-stone-400 dark:hover:text-stone-200"
            >
              <ArrowLeft className="h-4 w-4" /> Back
            </button>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">
                Recipe name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={newRecipeName}
                onChange={(e) => setNewRecipeName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-100"
                autoFocus
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">
                Recipe type
              </label>
              <select
                value={newRecipeType}
                onChange={(e) => setNewRecipeType(e.target.value as 'glaze' | 'engobe')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-100"
              >
                <option value="glaze">Glaze</option>
                <option value="engobe">Engobe</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">
                Collection (optional)
              </label>
              <input
                type="text"
                value={newRecipeCollection}
                onChange={(e) => setNewRecipeCollection(e.target.value)}
                placeholder="e.g. Authentic, Creative, Stencil..."
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-100"
              />
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <Button variant="secondary" onClick={onClose} disabled={isPending}>
                Cancel
              </Button>
              <Button
                onClick={() => { setError(''); createAssignMutation.mutate(); }}
                disabled={!newRecipeName.trim() || isPending}
              >
                {createAssignMutation.isPending ? 'Creating...' : 'Create & Assign'}
              </Button>
            </div>
          </div>
        )}

        {/* Step 2c: Force Override */}
        {mode === 'force_override' && (
          <div className="space-y-3">
            {/* Back button only if there were multiple options */}
            {(currentStatus === 'awaiting_recipe' ||
              currentStatus === 'insufficient_materials' ||
              currentStatus === 'awaiting_stencil_silkscreen') && (
              <button
                type="button"
                onClick={() => { setMode('choose'); setError(''); }}
                className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-stone-400 dark:hover:text-stone-200"
              >
                <ArrowLeft className="h-4 w-4" /> Back
              </button>
            )}

            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 dark:border-red-700/50 dark:bg-red-900/20">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500 dark:text-red-400" />
              <div className="text-sm text-red-700 dark:text-red-300">
                This position will proceed to production bypassing the current block.
                CEO/Owner will be notified via Telegram.
              </div>
            </div>

            {currentStatus === 'insufficient_materials' && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-700/50 dark:bg-amber-900/20 dark:text-amber-300">
                Materials will be force-reserved even if stock is insufficient. Balance may go
                negative -- correct during inventory.
              </div>
            )}

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">
                Reason (required for audit) <span className="text-red-500">*</span>
              </label>
              <textarea
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-100"
                rows={3}
                placeholder="Why are you force-overriding this position?..."
                value={overrideNotes}
                onChange={(e) => setOverrideNotes(e.target.value)}
                autoFocus
              />
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <Button variant="secondary" onClick={onClose} disabled={isPending}>
                Cancel
              </Button>
              <button
                type="button"
                onClick={handleForceOverride}
                disabled={!overrideNotes.trim() || isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-red-700 dark:hover:bg-red-600"
              >
                {forceUnblock.isPending ? 'Overriding...' : 'Force Override'}
                {!forceUnblock.isPending && <Zap className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-700/50 dark:bg-red-900/20 dark:text-red-300">
            {error}
          </div>
        )}
      </div>
    </Dialog>
  );
}
