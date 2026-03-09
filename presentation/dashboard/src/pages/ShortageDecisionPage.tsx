import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { useTask, useShortageResolution } from '@/hooks/useTasks';
import { useFactories } from '@/hooks/useFactories';

export default function ShortageDecisionPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { data: task, isLoading, isError } = useTask(taskId);
  const { data: factoriesData } = useFactories();
  const resolveMutation = useShortageResolution();
  const [decision, setDecision] = useState<'manufacture' | 'decline' | null>(null);
  const [targetFactoryId, setTargetFactoryId] = useState('');
  const [manufactureQty, setManufactureQty] = useState(0);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-8 text-center">
        <p className="text-sm font-medium text-red-800">⚠ Error loading task. Try refreshing.</p>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="p-8 text-center text-gray-500">Task not found</div>
    );
  }

  const meta = (task.metadata_json || {}) as Record<string, unknown>;
  const needed = (meta.needed as number) || 0;
  const totalGood = (meta.total_good as number) || 0;
  const shortage = (meta.shortage as number) || 0;
  const color = (meta.color as string) || '';
  const size = (meta.size as string) || '';
  const sortedPositions = (meta.sorted_positions as Array<{
    position_id: string;
    factory_id: string;
    good: number;
  }>) || [];

  const factories = factoriesData?.items || [];

  // Set default values when decision changes
  const handleSelectDecision = (d: 'manufacture' | 'decline') => {
    setDecision(d);
    if (d === 'manufacture') {
      setManufactureQty(shortage);
      if (factories.length > 0 && !targetFactoryId) {
        setTargetFactoryId(factories[0].id);
      }
    }
  };

  const handleSubmit = async () => {
    if (!taskId || !decision) return;
    setError('');
    try {
      await resolveMutation.mutateAsync({
        id: taskId,
        data: {
          decision,
          ...(decision === 'manufacture' ? {
            target_factory_id: targetFactoryId,
            manufacture_quantity: manufactureQty,
          } : {}),
          notes: notes || undefined,
        },
      });
      navigate('/manager');
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
      setError(resp?.detail || 'Failed to resolve shortage');
    }
  };

  const isResolved = task.status === 'done';

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/manager')}
          className="mb-2 text-sm text-primary-600 hover:underline"
        >
          &larr; Back to Manager
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Stock Shortage Decision</h1>
        <p className="mt-1 text-sm text-gray-500">
          Order: {task.related_order_number || 'N/A'}
        </p>
      </div>

      {/* Shortage Info */}
      <Card>
        <h3 className="mb-3 text-sm font-semibold text-gray-900">Shortage Details</h3>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-500">Color</span>
            <p className="font-semibold">{color}</p>
          </div>
          <div>
            <span className="text-gray-500">Size</span>
            <p className="font-semibold">{size}</p>
          </div>
          <div>
            <span className="text-gray-500">Ordered</span>
            <p className="font-semibold">{needed} pcs</p>
          </div>
          <div>
            <span className="text-gray-500">Sorted Good</span>
            <p className="font-semibold text-green-700">{totalGood} pcs</p>
          </div>
          <div className="col-span-2">
            <span className="text-gray-500">Shortage</span>
            <p className="text-lg font-bold text-red-700">{shortage} pcs</p>
          </div>
        </div>

        {/* Sorted positions by factory */}
        {sortedPositions.length > 0 && (
          <div className="mt-4 border-t pt-3">
            <p className="mb-2 text-xs font-medium text-gray-500">Sorting results by factory:</p>
            {sortedPositions.map((sp) => {
              const factory = factories.find((f) => f.id === sp.factory_id);
              return (
                <div key={sp.position_id} className="flex justify-between text-xs">
                  <span className="text-gray-600">{factory?.name || sp.factory_id.slice(0, 8)}</span>
                  <span className="font-medium">{sp.good} pcs good</span>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Resolution (only if not already resolved) */}
      {isResolved ? (
        <Card className="border-green-200 bg-green-50">
          <p className="text-sm font-medium text-green-700">
            This shortage has been resolved: {(meta.resolution as string) || 'done'}
          </p>
        </Card>
      ) : (
        <>
          {/* Decision buttons */}
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => handleSelectDecision('manufacture')}
              className={`rounded-lg border-2 p-4 text-left transition-all ${
                decision === 'manufacture'
                  ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-500'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <p className="font-semibold text-gray-900">Manufacture</p>
              <p className="mt-1 text-xs text-gray-500">
                Create a production order for the missing quantity
              </p>
            </button>
            <button
              onClick={() => handleSelectDecision('decline')}
              className={`rounded-lg border-2 p-4 text-left transition-all ${
                decision === 'decline'
                  ? 'border-red-500 bg-red-50 ring-1 ring-red-500'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <p className="font-semibold text-gray-900">Decline</p>
              <p className="mt-1 text-xs text-gray-500">
                Close task and notify sales manager
              </p>
            </button>
          </div>

          {/* Manufacture form */}
          {decision === 'manufacture' && (
            <Card className="border-primary-200 bg-primary-50/30">
              <h4 className="mb-3 text-sm font-semibold text-gray-900">Manufacture Details</h4>
              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Factory</label>
                  <select
                    value={targetFactoryId}
                    onChange={(e) => setTargetFactoryId(e.target.value)}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  >
                    {factories.map((f) => (
                      <option key={f.id} value={f.id}>{f.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Quantity</label>
                  <input
                    type="number"
                    min={1}
                    value={manufactureQty}
                    onChange={(e) => setManufactureQty(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>
            </Card>
          )}

          {/* Decline form */}
          {decision === 'decline' && (
            <Card className="border-red-200 bg-red-50/30">
              <h4 className="mb-3 text-sm font-semibold text-gray-900">Decline Reason</h4>
              <textarea
                placeholder="Reason for declining (optional)"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                rows={3}
              />
            </Card>
          )}

          {/* Error */}
          {error && <p className="text-sm text-red-500">{error}</p>}

          {/* Submit */}
          {decision && (
            <Button
              className="w-full"
              onClick={handleSubmit}
              disabled={resolveMutation.isPending || (decision === 'manufacture' && !targetFactoryId)}
            >
              {resolveMutation.isPending
                ? 'Processing...'
                : decision === 'manufacture'
                  ? `Manufacture ${manufactureQty} pcs`
                  : 'Decline & Notify Sales'}
            </Button>
          )}
        </>
      )}
    </div>
  );
}
