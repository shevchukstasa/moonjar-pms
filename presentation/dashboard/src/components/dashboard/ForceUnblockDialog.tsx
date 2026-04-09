import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Spinner } from '@/components/ui/Spinner';
import { useForceUnblock, useForceUnblockOptions, useUpdatePosition } from '@/hooks/usePositions';
import { recipesApi, type RecipeItem } from '@/api/recipes';
import { positionsApi, type ForceUnblockOption } from '@/api/positions';
import {
  ClipboardList, Plus, Zap, ArrowLeft, AlertTriangle, Package, CheckCircle,
  Truck, Replace, Palette, Settings, Edit3, Ruler, Undo2, Trash2,
} from 'lucide-react';

// ---- Types ----
interface ForceUnblockDialogProps {
  positionId: string;
  positionLabel: string;
  currentStatus: string;
  color: string;
  collection: string | null;
  onClose: () => void;
}

type DialogMode = 'choose' | 'select_recipe' | 'confirm_action';

const STATUS_LABELS: Record<string, string> = {
  insufficient_materials: 'Insufficient Materials',
  awaiting_recipe: 'Awaiting Recipe',
  awaiting_stencil_silkscreen: 'Awaiting Stencil/Silkscreen',
  awaiting_color_matching: 'Awaiting Color Matching',
  awaiting_consumption_data: 'Awaiting Consumption Data',
  awaiting_size_confirmation: 'Awaiting Size Confirmation',
  blocked_by_qm: 'Blocked by QM',
};

// Icon mapping from backend icon keys
const ICON_MAP: Record<string, React.ReactNode> = {
  package: <Package className="h-6 w-6" />,
  truck: <Truck className="h-6 w-6" />,
  replace: <Replace className="h-6 w-6" />,
  plus: <Plus className="h-6 w-6" />,
  clipboard: <ClipboardList className="h-6 w-6" />,
  zap: <Zap className="h-6 w-6" />,
  check: <CheckCircle className="h-6 w-6" />,
  palette: <Palette className="h-6 w-6" />,
  settings: <Settings className="h-6 w-6" />,
  edit: <Edit3 className="h-6 w-6" />,
  ruler: <Ruler className="h-6 w-6" />,
  undo: <Undo2 className="h-6 w-6" />,
  trash: <Trash2 className="h-6 w-6" />,
};

// ---- Option Card ----
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

// ---- Main Dialog ----
export function ForceUnblockDialog({
  positionId,
  positionLabel,
  currentStatus,
  color,
  collection,
  onClose,
}: ForceUnblockDialogProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const forceUnblock = useForceUnblock();
  const updatePosition = useUpdatePosition();

  // Fetch context-aware options from backend
  const { data: optionsData, isLoading: optionsLoading } = useForceUnblockOptions(positionId);

  // Dialog mode
  const [mode, setMode] = useState<DialogMode>('choose');

  // Selected option for confirmation step
  const [selectedOption, setSelectedOption] = useState<ForceUnblockOption | null>(null);

  // Notes for confirmation
  const [notes, setNotes] = useState('');

  // Select recipe state
  const [search, setSearch] = useState('');
  const [selectedRecipeId, setSelectedRecipeId] = useState<string | null>(null);

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

  // Assign recipe mutation (for use_existing_recipe option)
  const assignMutation = useMutation({
    mutationFn: async () => {
      if (!selectedRecipeId) throw new Error('No recipe selected');
      await positionsApi.update(positionId, { recipe_id: selectedRecipeId });
      const recipeName = recipes.find((r) => r.id === selectedRecipeId)?.name ?? selectedRecipeId;
      await positionsApi.forceUnblock(
        positionId,
        `Recipe assigned: ${recipeName}. ${notes}`.trim(),
        'use_existing_recipe',
      );
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

  // Handle option click
  const handleOptionClick = (option: ForceUnblockOption) => {
    setError('');

    // Special routing for recipe-related options
    if (option.key === 'use_existing_recipe') {
      setSelectedOption(option);
      setMode('select_recipe');
      return;
    }
    if (option.key === 'create_new_recipe') {
      // Redirect to recipe creation page with pre-filled data
      const params = new URLSearchParams({
        create: 'true',
        name: color || '',
        collection: collection || '',
        position_id: positionId,
      });
      window.location.href = `/admin/recipes?${params.toString()}`;
      return;
    }

    // All other options go to confirmation step
    setSelectedOption(option);
    setMode('confirm_action');
  };

  // Execute the selected option
  const handleConfirm = () => {
    if (!selectedOption || !notes.trim()) return;
    setError('');

    forceUnblock.mutate(
      { id: positionId, notes: notes.trim(), option: selectedOption.key, notify_override: true },
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

  const isPending = forceUnblock.isPending || assignMutation.isPending;

  const options = optionsData?.options ?? [];

  const dialogTitle =
    mode === 'choose'
      ? 'Resolve Blocking'
      : mode === 'select_recipe'
        ? 'Select Recipe'
        : selectedOption
          ? selectedOption.title
          : 'Confirm Action';

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

        {/* Step 1: Choose from context-aware options */}
        {mode === 'choose' && (
          <>
            {optionsLoading ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : options.length === 0 ? (
              <div className="py-6 text-center text-sm text-gray-400 dark:text-stone-500">
                No unblock options available for this status.
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-3">
                {options.map((opt) => (
                  <OptionCard
                    key={opt.key}
                    icon={ICON_MAP[opt.icon] || <Zap className="h-6 w-6" />}
                    title={opt.title}
                    description={opt.description}
                    onClick={() => handleOptionClick(opt)}
                    variant={opt.variant}
                  />
                ))}
              </div>
            )}
          </>
        )}

        {/* Step 2a: Select Recipe */}
        {mode === 'select_recipe' && (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => { setMode('choose'); setError(''); setSelectedOption(null); }}
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
                <div className="py-6 text-center space-y-3">
                  <div className="text-sm text-gray-400 dark:text-stone-500">
                    {search ? 'No recipes match your search' : 'No active recipes found'}
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const params = new URLSearchParams({
                        create: 'true',
                        name: `${color || ''} ${collection || ''}`.trim(),
                        collection: collection || '',
                        position_id: positionId,
                      });
                      onClose();
                      navigate(`/admin/recipes?${params.toString()}`);
                    }}
                    className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                  >
                    + Create New Recipe
                  </button>
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

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-stone-300">
                Notes (optional)
              </label>
              <input
                type="text"
                placeholder="Additional notes..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-100"
              />
            </div>

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

        {/* Step 2b: Confirm action with notes */}
        {mode === 'confirm_action' && selectedOption && (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => { setMode('choose'); setError(''); setSelectedOption(null); setNotes(''); }}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-stone-400 dark:hover:text-stone-200"
            >
              <ArrowLeft className="h-4 w-4" /> Back
            </button>

            {/* Warning for danger options */}
            {selectedOption.variant === 'danger' && (
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 dark:border-red-700/50 dark:bg-red-900/20">
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500 dark:text-red-400" />
                <div className="text-sm text-red-700 dark:text-red-300">
                  {selectedOption.key === 'scrap'
                    ? 'This position will be marked as defective and written off. This action cannot be easily reversed.'
                    : 'This position will proceed to production bypassing the current block. CEO/Owner will be notified via Telegram.'}
                </div>
              </div>
            )}

            {/* Info for non-danger options */}
            {selectedOption.variant !== 'danger' && (
              <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-700/50 dark:bg-amber-900/20">
                <div className="mt-0.5 flex-shrink-0 text-amber-600 dark:text-amber-400">
                  {ICON_MAP[selectedOption.icon] || <CheckCircle className="h-4 w-4" />}
                </div>
                <div className="text-sm text-amber-800 dark:text-amber-300">
                  <span className="font-medium">{selectedOption.title}:</span> {selectedOption.description}
                  <br />
                  <span className="text-xs opacity-75">CEO/Owner will be notified via Telegram.</span>
                </div>
              </div>
            )}

            {/* Material warning for insufficient_materials */}
            {currentStatus === 'insufficient_materials' && selectedOption.key === 'proceed_with_available' && (
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
                placeholder={`Why are you choosing "${selectedOption.title}"?...`}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                autoFocus
              />
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <Button variant="secondary" onClick={onClose} disabled={isPending}>
                Cancel
              </Button>
              {selectedOption.variant === 'danger' ? (
                <button
                  type="button"
                  onClick={handleConfirm}
                  disabled={!notes.trim() || isPending}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-red-700 dark:hover:bg-red-600"
                >
                  {forceUnblock.isPending ? 'Processing...' : selectedOption.title}
                  {!forceUnblock.isPending && <Zap className="h-3.5 w-3.5" />}
                </button>
              ) : (
                <Button
                  onClick={handleConfirm}
                  disabled={!notes.trim() || isPending}
                >
                  {forceUnblock.isPending ? 'Processing...' : `Confirm: ${selectedOption.title}`}
                </Button>
              )}
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
