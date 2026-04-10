import { useMemo, useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';

interface CapabilityRow {
  id: string | null;
  recipe_id: string;
  kiln_id: string;
  kiln_name: string | null;
  factory_id: string | null;
  is_qualified: boolean;
  quality_rating: number | null;
  success_count: number;
  failure_count: number;
  last_fired_at: string | null;
  needs_requalification: boolean;
  notes: string | null;
  current_equipment_config_id: string | null;
  last_qualified_equipment_config_id: string | null;
}

interface Draft {
  is_qualified: boolean;
  quality_rating: number | null;
  notes: string;
  dirty: boolean;
}

interface Props {
  open: boolean;
  onClose: () => void;
  recipeId: string | null;
  recipeName?: string;
}

export default function RecipeKilnCapabilityDialog({
  open,
  onClose,
  recipeId,
  recipeName,
}: Props) {
  const queryClient = useQueryClient();
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [savingKilnId, setSavingKilnId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const { data: rows, isLoading } = useQuery<CapabilityRow[]>({
    queryKey: ['recipe-kiln-capabilities', recipeId],
    queryFn: async () => {
      if (!recipeId) return [];
      const r = await apiClient.get(`/recipes/${recipeId}/kiln-capabilities`);
      return r.data ?? [];
    },
    enabled: !!recipeId && open,
  });

  // Seed drafts whenever rows load
  useEffect(() => {
    if (!rows) return;
    const seed: Record<string, Draft> = {};
    for (const row of rows) {
      seed[row.kiln_id] = {
        is_qualified: row.is_qualified,
        quality_rating: row.quality_rating,
        notes: row.notes ?? '',
        dirty: false,
      };
    }
    setDrafts(seed);
  }, [rows]);

  const upsertMutation = useMutation({
    mutationFn: async (args: { kilnId: string; payload: Partial<Draft> }) => {
      if (!recipeId) throw new Error('no recipe');
      await apiClient.put(
        `/recipes/${recipeId}/kiln-capabilities/${args.kilnId}`,
        {
          is_qualified: args.payload.is_qualified,
          quality_rating: args.payload.quality_rating,
          notes: args.payload.notes || null,
        },
      );
    },
    onSuccess: () => {
      setErrorMsg('');
      queryClient.invalidateQueries({
        queryKey: ['recipe-kiln-capabilities', recipeId],
      });
    },
    onError: (err: unknown) => {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setErrorMsg(resp?.detail || String(err));
    },
    onSettled: () => setSavingKilnId(null),
  });

  const deleteMutation = useMutation({
    mutationFn: async (kilnId: string) => {
      if (!recipeId) return;
      await apiClient.delete(`/recipes/${recipeId}/kiln-capabilities/${kilnId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['recipe-kiln-capabilities', recipeId],
      });
    },
  });

  const grouped = useMemo(() => {
    if (!rows) return new Map<string, CapabilityRow[]>();
    const g = new Map<string, CapabilityRow[]>();
    for (const row of rows) {
      const key = row.factory_id ?? '—';
      if (!g.has(key)) g.set(key, []);
      g.get(key)!.push(row);
    }
    return g;
  }, [rows]);

  const updateDraft = (kilnId: string, patch: Partial<Draft>) => {
    setDrafts((prev) => {
      const current = prev[kilnId] ?? {
        is_qualified: false,
        quality_rating: null,
        notes: '',
        dirty: false,
      };
      return {
        ...prev,
        [kilnId]: { ...current, ...patch, dirty: true },
      };
    });
  };

  const saveRow = (kilnId: string) => {
    const draft = drafts[kilnId];
    if (!draft) return;
    setSavingKilnId(kilnId);
    upsertMutation.mutate({
      kilnId,
      payload: draft,
    });
  };

  const qualifiedCount = rows?.filter((r) => r.is_qualified).length ?? 0;
  const warningCount = rows?.filter((r) => r.needs_requalification && r.is_qualified).length ?? 0;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`Kiln capability — ${recipeName ?? 'recipe'}`}
      className="w-[min(1200px,95vw)]"
    >
      <div className="max-h-[75vh] overflow-y-auto pr-1">
        <div className="mb-3 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-800">
          <strong>How this works:</strong> by default a recipe can be fired on
          any kiln. As soon as you mark at least one kiln as qualified, the
          scheduler will ONLY route this recipe to qualified kilns. Toggle
          "qualified" + optional 1-5 rating + notes per kiln.
          <br />
          When a kiln's equipment changes, its capabilities get flagged for
          <strong> requalification</strong> — re-save the row after a test batch to clear.
        </div>

        <div className="mb-3 flex items-center gap-4 text-sm">
          <span className="text-gray-500">
            Qualified: <strong className="text-green-600">{qualifiedCount}</strong>
          </span>
          {warningCount > 0 && (
            <span className="text-amber-600">
              ⚠ Needs requalification: <strong>{warningCount}</strong>
            </span>
          )}
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner className="h-8 w-8" />
          </div>
        ) : !rows || rows.length === 0 ? (
          <p className="py-8 text-center text-gray-400">No kilns configured</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-2 py-2 text-left">Kiln</th>
                <th className="px-2 py-2 text-center">Qualified</th>
                <th className="px-2 py-2 text-center">Rating</th>
                <th className="px-2 py-2 text-left">Notes</th>
                <th className="px-2 py-2 text-right">Stats</th>
                <th className="px-2 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {Array.from(grouped.entries()).map(([factoryId, factoryRows]) => (
                <>
                  <tr key={`factory-${factoryId}`} className="bg-gray-100">
                    <td
                      colSpan={6}
                      className="px-2 py-1 text-xs font-semibold text-gray-600"
                    >
                      Factory: {factoryId}
                    </td>
                  </tr>
                  {factoryRows.map((row) => {
                    const draft = drafts[row.kiln_id] ?? {
                      is_qualified: row.is_qualified,
                      quality_rating: row.quality_rating,
                      notes: row.notes ?? '',
                      dirty: false,
                    };
                    const rowBg = row.needs_requalification && row.is_qualified
                      ? 'bg-amber-50'
                      : '';
                    return (
                      <tr
                        key={row.kiln_id}
                        className={`border-b border-gray-100 ${rowBg}`}
                      >
                        <td className="px-2 py-2">
                          <div className="font-medium">{row.kiln_name}</div>
                          {row.needs_requalification && row.is_qualified && (
                            <div className="text-xs text-amber-600">
                              ⚠ Equipment changed — requalify
                            </div>
                          )}
                        </td>
                        <td className="px-2 py-2 text-center">
                          <input
                            type="checkbox"
                            checked={draft.is_qualified}
                            onChange={(e) =>
                              updateDraft(row.kiln_id, {
                                is_qualified: e.target.checked,
                              })
                            }
                            className="h-4 w-4 rounded"
                          />
                        </td>
                        <td className="px-2 py-2 text-center">
                          <select
                            value={draft.quality_rating ?? ''}
                            onChange={(e) =>
                              updateDraft(row.kiln_id, {
                                quality_rating: e.target.value
                                  ? parseInt(e.target.value)
                                  : null,
                              })
                            }
                            disabled={!draft.is_qualified}
                            className="rounded border border-gray-300 px-2 py-1 text-sm disabled:bg-gray-50 disabled:text-gray-400"
                          >
                            <option value="">—</option>
                            {[1, 2, 3, 4, 5].map((n) => (
                              <option key={n} value={n}>
                                {n} ★
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-2 py-2">
                          <input
                            type="text"
                            value={draft.notes}
                            onChange={(e) =>
                              updateDraft(row.kiln_id, { notes: e.target.value })
                            }
                            placeholder="optional"
                            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                          />
                        </td>
                        <td className="px-2 py-2 text-right font-mono text-xs text-gray-500">
                          <div>
                            <span className="text-green-600">{row.success_count}✓</span>
                            {' '}/ <span className="text-red-600">{row.failure_count}✕</span>
                          </div>
                          {row.last_fired_at && (
                            <div>
                              last: {new Date(row.last_fired_at).toLocaleDateString()}
                            </div>
                          )}
                        </td>
                        <td className="px-2 py-2 text-right">
                          <Button
                            size="sm"
                            disabled={!draft.dirty || savingKilnId === row.kiln_id}
                            onClick={() => saveRow(row.kiln_id)}
                          >
                            {savingKilnId === row.kiln_id ? '…' : 'Save'}
                          </Button>
                          {row.id && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="ml-1 text-red-500"
                              onClick={() => deleteMutation.mutate(row.kiln_id)}
                              title="Delete row"
                            >
                              ✕
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </>
              ))}
            </tbody>
          </table>
        )}

        {errorMsg && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {errorMsg}
          </div>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
