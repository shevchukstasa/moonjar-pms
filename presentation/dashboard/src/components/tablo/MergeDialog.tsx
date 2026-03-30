import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { positionsApi } from '@/api/positions';
import { useMergePosition } from '@/hooks/usePositions';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import type { PositionItem } from './PositionRow';

interface MergeableChild {
  id: string;
  status: string;
  quantity: number;
  split_category: string | null;
  position_label: string | null;
}

interface MergeDialogProps {
  /**
   * The position the user clicked "merge" on.
   * - If it has parent_position_id, it's a child — we use parent_position_id as the parent
   *   and pre-select this child.
   * - If it doesn't have parent_position_id, it's a parent — we fetch its children.
   */
  position: PositionItem;
  onClose: () => void;
}

export function MergeDialog({ position, onClose }: MergeDialogProps) {
  const isChild = !!position.parent_position_id;
  const parentId = isChild ? position.parent_position_id! : position.id;

  const [selectedChildId, setSelectedChildId] = useState<string | null>(
    isChild ? position.id : null,
  );
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useQuery<{
    parent_id: string;
    mergeable_children: MergeableChild[];
  }>({
    queryKey: ['positions', parentId, 'mergeable-children'],
    queryFn: () => positionsApi.getMergeableChildren(parentId),
  });

  const mergeMutation = useMergePosition();

  const children = data?.mergeable_children ?? [];

  // If only one child, auto-select it
  useEffect(() => {
    if (children.length === 1 && !selectedChildId) {
      setSelectedChildId(children[0].id);
    }
  }, [children, selectedChildId]);

  const handleMerge = () => {
    if (!selectedChildId) return;
    mergeMutation.mutate(
      { parentId, childId: selectedChildId },
      {
        onSuccess: () => {
          setSuccessMsg('Merge completed successfully');
          setTimeout(() => onClose(), 1200);
        },
      },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Merge Position</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">
            &times;
          </button>
        </div>

        {/* Position info */}
        <div className="mb-4 rounded-md bg-gray-50 p-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-gray-900">{position.order_number}</span>
            <span className="text-gray-500">{position.size}</span>
          </div>
          <div className="mt-1 flex items-center justify-between text-sm text-gray-600">
            <span>{position.color}</span>
            <span className="font-semibold">Qty: {position.quantity}</span>
          </div>
          <div className="mt-1 text-xs text-gray-400">
            {isChild ? 'Child position' : 'Parent position'} &middot; Status: {position.status}
          </div>
        </div>

        {/* Success message */}
        {successMsg && (
          <div className="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
            {successMsg}
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex justify-center py-8">
            <Spinner className="h-6 w-6" />
          </div>
        )}

        {/* Error fetching children */}
        {isError && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {(error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
              'Failed to load mergeable children.'}
          </div>
        )}

        {/* No mergeable children */}
        {!isLoading && !isError && children.length === 0 && (
          <div className="py-6 text-center text-sm text-gray-400">
            No mergeable children found for this position.
          </div>
        )}

        {/* Children list */}
        {!isLoading && children.length > 0 && (
          <div className="mb-4 space-y-2">
            <p className="text-xs text-gray-500 mb-2">
              {children.length === 1
                ? 'Confirm merging this child back into the parent:'
                : 'Select a child position to merge back into the parent:'}
            </p>
            {children.map((child) => (
              <label
                key={child.id}
                className={`flex items-center gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                  selectedChildId === child.id
                    ? 'border-green-400 bg-green-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <input
                  type="radio"
                  name="merge-child"
                  value={child.id}
                  checked={selectedChildId === child.id}
                  onChange={() => setSelectedChildId(child.id)}
                  className="h-4 w-4 text-green-600 focus:ring-green-500"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900">
                      {child.position_label ?? child.id.slice(0, 8)}
                    </span>
                    <span className="text-sm font-semibold text-gray-700">
                      {child.quantity} pcs
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-2">
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
                      {child.status}
                    </span>
                    {child.split_category && (
                      <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                        {child.split_category}
                      </span>
                    )}
                  </div>
                </div>
              </label>
            ))}
          </div>
        )}

        {/* Merge mutation error */}
        {mergeMutation.isError && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {(mergeMutation.error as { response?: { data?: { detail?: string } } })?.response?.data
              ?.detail ?? 'Merge failed. Please try again.'}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleMerge}
            disabled={!selectedChildId || mergeMutation.isPending || !!successMsg}
          >
            {mergeMutation.isPending ? 'Merging...' : 'Merge'}
          </Button>
        </div>
      </div>
    </div>
  );
}
