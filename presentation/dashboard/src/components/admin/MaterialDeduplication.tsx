import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import apiClient from '@/api/client';
import { AlertTriangle, Merge, Trash2, Check, Eye } from 'lucide-react';

interface MaterialInfo {
  id: string;
  name: string;
  material_type: string;
  unit: string;
  has_stock?: boolean;
  balance?: number;
  stock_count?: number;
  recipe_count?: number;
  transaction_count?: number;
}

interface DuplicateGroup {
  normalized_name: string;
  materials: MaterialInfo[];
}

interface DuplicatesResponse {
  total_materials: number;
  duplicate_groups: DuplicateGroup[];
  all_materials: MaterialInfo[];
}

interface CleanupAction {
  action: string;
  source?: { id: string; name: string };
  target?: { id: string; name: string };
  material?: { id: string; name: string };
  note?: string;
}

interface CleanupResponse {
  dry_run: boolean;
  total_materials?: number;
  frit_materials?: { id: string; name: string }[];
  planned_actions: CleanupAction[];
  merged_count?: number;
}

export function MaterialDeduplication() {
  const qc = useQueryClient();
  const [showAll, setShowAll] = useState(false);
  const [mergeSource, setMergeSource] = useState<string[]>([]);
  const [mergeTarget, setMergeTarget] = useState<string>('');
  const [mergeName, setMergeName] = useState('');
  const [mergeMsg, setMergeMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const { data, isLoading, isError, refetch } = useQuery<DuplicatesResponse>({
    queryKey: ['materials', 'duplicates'],
    queryFn: () => apiClient.get('/materials/duplicates').then((r) => r.data),
    enabled: false, // Only fetch on demand
  });

  const [cleanupPreview, setCleanupPreview] = useState<CleanupResponse | null>(null);

  const previewCleanup = useMutation({
    mutationFn: () =>
      apiClient
        .post('/materials/cleanup-duplicates', { dry_run: true })
        .then((r) => r.data),
    onSuccess: (result: CleanupResponse) => setCleanupPreview(result),
  });

  const executeCleanup = useMutation({
    mutationFn: () =>
      apiClient
        .post('/materials/cleanup-duplicates', { dry_run: false })
        .then((r) => r.data),
    onSuccess: (result: CleanupResponse) => {
      setCleanupPreview(result);
      qc.invalidateQueries({ queryKey: ['materials'] });
      refetch();
    },
  });

  const mergeMaterials = useMutation({
    mutationFn: (payload: { target_id: string; source_ids: string[]; new_name?: string }) =>
      apiClient.post('/materials/merge', payload).then((r) => r.data),
    onSuccess: (result) => {
      setMergeMsg({ ok: true, text: `Merged ${result.merged_count} materials into "${result.target.name}"` });
      setMergeSource([]);
      setMergeTarget('');
      setMergeName('');
      qc.invalidateQueries({ queryKey: ['materials'] });
      refetch();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Merge failed';
      setMergeMsg({ ok: false, text: msg });
    },
  });

  const allMats = data?.all_materials ?? [];
  const byType = allMats.reduce<Record<string, MaterialInfo[]>>((acc, m) => {
    const t = m.material_type || 'other';
    (acc[t] = acc[t] || []).push(m);
    return acc;
  }, {});

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Merge className="h-4 w-4 text-blue-500" />
          <h3 className="text-sm font-semibold text-gray-700">Material Deduplication</h3>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <Eye className="h-3 w-3 mr-1" />
            Scan Materials
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => previewCleanup.mutate()}
            disabled={previewCleanup.isPending}
          >
            {previewCleanup.isPending ? <Spinner className="h-3 w-3 mr-1" /> : <AlertTriangle className="h-3 w-3 mr-1" />}
            Preview Cleanup
          </Button>
        </div>
      </div>

      {isLoading && (
        <div className="flex justify-center py-4">
          <Spinner className="h-6 w-6" />
        </div>
      )}

      {isError && (
        <p className="text-sm text-red-500">Failed to load materials data</p>
      )}

      {/* Cleanup Preview */}
      {cleanupPreview && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <h4 className="text-sm font-medium text-amber-800 mb-2">
            {cleanupPreview.dry_run ? 'Cleanup Preview' : 'Cleanup Complete'}
            {cleanupPreview.merged_count !== undefined && ` — ${cleanupPreview.merged_count} merged`}
          </h4>

          {cleanupPreview.frit_materials && cleanupPreview.frit_materials.length > 0 && (
            <div className="mb-2">
              <p className="text-xs font-medium text-gray-600 mb-1">Frit materials found:</p>
              <ul className="text-xs text-gray-500 space-y-0.5">
                {cleanupPreview.frit_materials.map((f) => (
                  <li key={f.id}>
                    <code className="bg-white px-1 rounded">{f.name}</code>
                    <span className="text-gray-400 ml-1">({f.id.slice(0, 8)})</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {cleanupPreview.planned_actions.length > 0 ? (
            <>
              <ul className="text-xs space-y-1 mb-2 max-h-40 overflow-y-auto">
                {cleanupPreview.planned_actions.map((a, i) => (
                  <li key={i} className="flex items-center gap-1">
                    {a.action.startsWith('merge') ? (
                      <>
                        <Trash2 className="h-3 w-3 text-red-400" />
                        <span className="text-red-600">{a.source?.name}</span>
                        <span className="text-gray-400">&rarr;</span>
                        <span className="text-green-600">{a.target?.name}</span>
                        <span className="text-gray-400 ml-1">({a.action})</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="h-3 w-3 text-amber-400" />
                        <span className="text-amber-700">{a.material?.name}</span>
                        <span className="text-gray-400 ml-1">{a.note}</span>
                      </>
                    )}
                  </li>
                ))}
              </ul>
              {cleanupPreview.dry_run && (
                <Button
                  size="sm"
                  variant="secondary"
                  className="text-red-600 border-red-300 hover:bg-red-50"
                  onClick={() => executeCleanup.mutate()}
                  disabled={executeCleanup.isPending}
                >
                  {executeCleanup.isPending ? <Spinner className="h-3 w-3 mr-1" /> : <Check className="h-3 w-3 mr-1" />}
                  Execute Cleanup
                </Button>
              )}
            </>
          ) : (
            <p className="text-xs text-green-600">No duplicates found!</p>
          )}
        </div>
      )}

      {/* Duplicate Groups */}
      {data && data.duplicate_groups.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-red-600 mb-2">
            Exact Duplicates ({data.duplicate_groups.length} groups)
          </h4>
          <div className="space-y-2">
            {data.duplicate_groups.map((group) => (
              <div key={group.normalized_name} className="rounded border border-red-100 bg-red-50 p-2">
                <p className="text-xs font-medium text-gray-700 mb-1">{group.normalized_name}</p>
                <ul className="text-xs text-gray-500 space-y-0.5">
                  {group.materials.map((m) => (
                    <li key={m.id} className="flex items-center gap-2">
                      <code className="text-xs">{m.id.slice(0, 8)}</code>
                      <span>{m.name}</span>
                      <span className="text-gray-400">
                        (stocks: {m.stock_count}, recipes: {m.recipe_count}, txns: {m.transaction_count})
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Materials by Type */}
      {data && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-medium text-gray-500">
              All Materials: {data.total_materials}
            </h4>
            <button
              className="text-xs text-blue-500 hover:underline"
              onClick={() => setShowAll(!showAll)}
            >
              {showAll ? 'Hide' : 'Show All'}
            </button>
          </div>
          {showAll && (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {Object.entries(byType)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([type, mats]) => (
                  <div key={type}>
                    <p className="text-xs font-medium text-gray-600 mb-1 capitalize">{type} ({mats.length})</p>
                    <div className="space-y-0.5">
                      {mats.map((m) => (
                        <div key={m.id} className="flex items-center gap-2 text-xs">
                          <input
                            type="checkbox"
                            className="h-3 w-3"
                            checked={mergeSource.includes(m.id) || mergeTarget === m.id}
                            onChange={(e) => {
                              if (e.target.checked) {
                                if (!mergeTarget) {
                                  setMergeTarget(m.id);
                                  setMergeName(m.name);
                                } else {
                                  setMergeSource([...mergeSource, m.id]);
                                }
                              } else {
                                if (mergeTarget === m.id) {
                                  setMergeTarget('');
                                  setMergeName('');
                                } else {
                                  setMergeSource(mergeSource.filter((id) => id !== m.id));
                                }
                              }
                            }}
                          />
                          <code className="text-gray-400">{m.id.slice(0, 8)}</code>
                          <span className={mergeTarget === m.id ? 'font-bold text-green-700' : 'text-gray-700'}>
                            {m.name}
                          </span>
                          {m.balance !== undefined && m.balance > 0 && (
                            <span className="text-gray-400">bal: {m.balance}</span>
                          )}
                          {mergeTarget === m.id && (
                            <span className="text-green-600 text-[10px]">(TARGET)</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* Manual Merge */}
      {mergeTarget && mergeSource.length > 0 && (
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3">
          <h4 className="text-sm font-medium text-blue-800 mb-2">Manual Merge</h4>
          <p className="text-xs text-gray-600 mb-2">
            Merge {mergeSource.length} material(s) into target.
            First selected = target (green).
          </p>
          <div className="flex items-center gap-2 mb-2">
            <label className="text-xs text-gray-500">Final name:</label>
            <input
              type="text"
              value={mergeName}
              onChange={(e) => setMergeName(e.target.value)}
              className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs"
            />
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() =>
                mergeMaterials.mutate({
                  target_id: mergeTarget,
                  source_ids: mergeSource,
                  new_name: mergeName || undefined,
                })
              }
              disabled={mergeMaterials.isPending}
            >
              {mergeMaterials.isPending ? <Spinner className="h-3 w-3 mr-1" /> : <Merge className="h-3 w-3 mr-1" />}
              Merge
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setMergeSource([]);
                setMergeTarget('');
                setMergeName('');
                setMergeMsg(null);
              }}
            >
              Cancel
            </Button>
          </div>
          {mergeMsg && (
            <p className={`mt-2 text-xs ${mergeMsg.ok ? 'text-green-600' : 'text-red-500'}`}>{mergeMsg.text}</p>
          )}
        </div>
      )}
    </Card>
  );
}
