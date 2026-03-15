import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';
import { useTask, useSizeResolution } from '@/hooks/useTasks';

interface SizeOption {
  id: string;
  name: string;
  width_mm: number;
  height_mm: number;
  thickness_mm: number | null;
  shape: string | null;
}

const SHAPE_OPTIONS = ['rectangle', 'square', 'round', 'freeform', 'triangle', 'octagon'];

export default function SizeResolutionPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { data: task, isLoading, isError } = useTask(taskId);
  const resolveMutation = useSizeResolution();

  // Mode: 'select' or 'create'
  const [mode, setMode] = useState<'select' | 'create'>('select');
  const [selectedSizeId, setSelectedSizeId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState('');

  // New size form
  const [newName, setNewName] = useState('');
  const [newWidth, setNewWidth] = useState('');
  const [newHeight, setNewHeight] = useState('');
  const [newThickness, setNewThickness] = useState('');
  const [newShape, setNewShape] = useState('rectangle');

  // Fetch all sizes for the list
  const { data: sizesData } = useQuery<{ items: SizeOption[]; total: number }>({
    queryKey: ['sizes'],
    queryFn: () => apiClient.get('/sizes').then((r) => r.data),
  });

  const allSizes = sizesData?.items || [];

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (isError || !task) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-8 text-center">
        <p className="text-sm font-medium text-red-800">
          {isError ? 'Error loading task. Try refreshing.' : 'Task not found.'}
        </p>
      </div>
    );
  }

  const meta = (task.metadata_json || {}) as Record<string, unknown>;
  const reason = (meta.reason as string) || 'unknown';
  const candidates = (meta.candidates as SizeOption[]) || [];
  const positionSize = (meta.position_size_string as string) || '';
  const positionShape = (meta.position_shape as string) || '';
  const positionThickness = meta.position_thickness_mm as number | null;
  const positionWidthMm = meta.position_width_mm as number | null;
  const positionHeightMm = meta.position_height_mm as number | null;

  const isResolved = task.status === 'done';

  // Filter sizes by search
  const filteredSizes = useMemo(() => {
    const list = candidates.length > 0 && mode === 'select' && !searchQuery
      ? candidates
      : allSizes;
    if (!searchQuery) return list;
    const q = searchQuery.toLowerCase();
    return list.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        `${s.width_mm}x${s.height_mm}`.includes(q) ||
        `${s.height_mm}x${s.width_mm}`.includes(q),
    );
  }, [candidates, allSizes, searchQuery, mode]);

  const reasonLabel: Record<string, string> = {
    no_match: 'No matching size found in reference table',
    multiple_matches: `${candidates.length} sizes match these dimensions`,
    missing_dimensions: 'Cannot extract dimensions from position',
  };

  const handleSubmit = async () => {
    setError('');
    if (!taskId) return;

    try {
      if (mode === 'select') {
        if (!selectedSizeId) {
          setError('Please select a size');
          return;
        }
        await resolveMutation.mutateAsync({
          id: taskId,
          data: { size_id: selectedSizeId },
        });
      } else {
        if (!newName || !newWidth || !newHeight) {
          setError('Name, width and height are required');
          return;
        }
        await resolveMutation.mutateAsync({
          id: taskId,
          data: {
            create_new_size: true,
            new_size_name: newName,
            new_size_width_mm: parseInt(newWidth, 10),
            new_size_height_mm: parseInt(newHeight, 10),
            new_size_thickness_mm: newThickness ? parseInt(newThickness, 10) : undefined,
            new_size_shape: newShape,
          },
        });
      }
      navigate(-1);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to resolve size';
      setError(msg);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="mb-2 text-sm text-blue-600 hover:underline"
          >
            &larr; Back
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Size Resolution</h1>
          {task.related_order_number && (
            <p className="mt-1 text-sm text-gray-500">
              Order: <span className="font-medium">{task.related_order_number}</span>
            </p>
          )}
        </div>
        {isResolved && (
          <span className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
            Resolved
          </span>
        )}
      </div>

      {/* Position Info */}
      <Card className="p-5">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
          Position Details
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Size String</span>
            <p className="font-medium text-gray-900">{positionSize || '—'}</p>
          </div>
          <div>
            <span className="text-gray-500">Dimensions (mm)</span>
            <p className="font-medium text-gray-900">
              {positionWidthMm && positionHeightMm
                ? `${positionWidthMm} x ${positionHeightMm}`
                : '—'}
            </p>
          </div>
          <div>
            <span className="text-gray-500">Shape</span>
            <p className="font-medium text-gray-900">{positionShape || '—'}</p>
          </div>
          <div>
            <span className="text-gray-500">Thickness (mm)</span>
            <p className="font-medium text-gray-900">{positionThickness ?? '—'}</p>
          </div>
        </div>
        <div className="mt-3 rounded bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
          {reasonLabel[reason] || reason}
        </div>
      </Card>

      {!isResolved && (
        <>
          {/* Mode Toggle */}
          <div className="flex gap-2">
            <Button
              variant={mode === 'select' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setMode('select')}
            >
              Select Existing Size
            </Button>
            <Button
              variant={mode === 'create' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setMode('create')}
            >
              Create New Size
            </Button>
          </div>

          {mode === 'select' ? (
            <Card className="p-5">
              <h2 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
                {candidates.length > 0 ? 'Matching Candidates' : 'All Sizes'}
              </h2>

              <Input
                placeholder="Search by name or dimensions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="mb-3"
              />

              <div className="max-h-80 overflow-y-auto rounded border border-gray-200">
                {filteredSizes.length === 0 ? (
                  <p className="py-6 text-center text-sm text-gray-400">No sizes found</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-gray-50">
                      <tr className="border-b text-left text-xs font-medium text-gray-500 uppercase">
                        <th className="px-3 py-2 w-8"></th>
                        <th className="px-3 py-2">Name</th>
                        <th className="px-3 py-2">Width</th>
                        <th className="px-3 py-2">Height</th>
                        <th className="px-3 py-2">Thickness</th>
                        <th className="px-3 py-2">Shape</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredSizes.map((s) => (
                        <tr
                          key={s.id}
                          className={`cursor-pointer border-b border-gray-100 transition-colors ${
                            selectedSizeId === s.id
                              ? 'bg-blue-50'
                              : 'hover:bg-gray-50'
                          }`}
                          onClick={() => setSelectedSizeId(s.id)}
                        >
                          <td className="px-3 py-2">
                            <input
                              type="radio"
                              name="size"
                              checked={selectedSizeId === s.id}
                              onChange={() => setSelectedSizeId(s.id)}
                              className="h-4 w-4 text-blue-600"
                            />
                          </td>
                          <td className="px-3 py-2 font-medium">{s.name}</td>
                          <td className="px-3 py-2">{s.width_mm} mm</td>
                          <td className="px-3 py-2">{s.height_mm} mm</td>
                          <td className="px-3 py-2">{s.thickness_mm ?? '—'}</td>
                          <td className="px-3 py-2">{s.shape || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </Card>
          ) : (
            <Card className="p-5">
              <h2 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Create New Size
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Input
                    label="Name"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g. 30x60"
                    required
                  />
                </div>
                <Input
                  label="Width (mm)"
                  type="number"
                  value={newWidth}
                  onChange={(e) => setNewWidth(e.target.value)}
                  placeholder="e.g. 300"
                  required
                />
                <Input
                  label="Height (mm)"
                  type="number"
                  value={newHeight}
                  onChange={(e) => setNewHeight(e.target.value)}
                  placeholder="e.g. 600"
                  required
                />
                <Input
                  label="Thickness (mm)"
                  type="number"
                  value={newThickness}
                  onChange={(e) => setNewThickness(e.target.value)}
                  placeholder="e.g. 11"
                />
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Shape</label>
                  <select
                    value={newShape}
                    onChange={(e) => setNewShape(e.target.value)}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  >
                    {SHAPE_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {s.charAt(0).toUpperCase() + s.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </Card>
          )}

          {/* Error + Submit */}
          {error && (
            <div className="rounded border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => navigate(-1)}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={resolveMutation.isPending}
            >
              {resolveMutation.isPending
                ? 'Resolving...'
                : mode === 'select'
                  ? 'Assign Selected Size'
                  : 'Create & Assign Size'}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
