import { useQuery } from '@tanstack/react-query';
import { positionsApi } from '@/api/positions';
import { Dialog } from '@/components/ui/Dialog';
import { Spinner } from '@/components/ui/Spinner';

interface SplitTreeNode {
  id: string;
  quantity: number;
  quantity_sqm: number | null;
  status: string;
  priority_order: number;
  split_index: number | null;
  position_number: number | null;
  is_parent: boolean;
  split_type: string | null;
  split_stage: string | null;
  split_at: string | null;
  split_reason: string | null;
  children: SplitTreeNode[];
}

interface SplitTreeModalProps {
  positionId: string | null;
  onClose: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  planned: 'bg-gray-100 text-gray-700',
  sent_to_glazing: 'bg-blue-100 text-blue-700',
  glazed: 'bg-blue-100 text-blue-700',
  ready_for_kiln: 'bg-yellow-100 text-yellow-700',
  in_kiln: 'bg-orange-100 text-orange-700',
  fired: 'bg-orange-100 text-orange-700',
  sorting: 'bg-purple-100 text-purple-700',
  quality_check_done: 'bg-green-100 text-green-700',
  packed: 'bg-green-100 text-green-700',
  ready_for_shipment: 'bg-green-100 text-green-700',
  shipped: 'bg-green-200 text-green-800',
  blocked: 'bg-red-100 text-red-700',
  merged: 'bg-gray-200 text-gray-500',
  write_off: 'bg-red-200 text-red-800',
  grinding: 'bg-amber-100 text-amber-700',
};

function getStatusColor(status: string): string {
  return STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-600';
}

function formatStatus(status: string): string {
  return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatLabel(node: SplitTreeNode): string {
  if (node.position_number != null && node.split_index != null) {
    return `#${node.position_number}.${node.split_index}`;
  }
  if (node.position_number != null) {
    return `#${node.position_number}`;
  }
  return '';
}

function TreeNode({ node, depth }: { node: SplitTreeNode; depth: number }) {
  const hasChildren = node.children.length > 0;
  const isMerged = node.status === 'merged';
  const label = formatLabel(node);

  return (
    <div>
      <div
        className={`flex items-center gap-2 rounded-md px-3 py-2 ${depth > 0 ? 'ml-6' : ''} ${isMerged ? 'opacity-50' : ''}`}
      >
        {/* Connector line */}
        {depth > 0 && (
          <div className="flex items-center -ml-6 w-6">
            <div className="h-px w-3 bg-gray-300" />
            <div className="h-0 w-0 border-y-[3px] border-l-[5px] border-y-transparent border-l-gray-300" />
          </div>
        )}

        {/* Node content */}
        <div className="flex flex-1 items-center gap-2 min-w-0">
          {/* Position label */}
          {label && (
            <span className="shrink-0 text-xs font-mono font-semibold text-gray-700">
              {label}
            </span>
          )}

          {/* Status badge */}
          <span
            className={`shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${getStatusColor(node.status)}`}
          >
            {formatStatus(node.status)}
          </span>

          {/* Quantity */}
          <span className="shrink-0 text-sm font-medium text-gray-900">
            {node.quantity} pcs
          </span>
          {node.quantity_sqm != null && (
            <span className="shrink-0 text-xs text-gray-500">
              ({node.quantity_sqm.toFixed(2)} m\u00B2)
            </span>
          )}

          {/* Merged indicator */}
          {isMerged && (
            <span className="shrink-0 text-[10px] text-gray-400 italic">merged</span>
          )}

          {/* Split info */}
          {node.split_type && (
            <span className="shrink-0 text-[10px] text-gray-400">
              {node.split_type}
            </span>
          )}
          {node.split_reason && (
            <span className="shrink-0 text-[10px] text-gray-400 truncate max-w-[160px]" title={node.split_reason}>
              {node.split_reason}
            </span>
          )}
        </div>

        {/* Parent indicator */}
        {hasChildren && (
          <span className="shrink-0 text-[10px] text-gray-400">
            {node.children.length} child{node.children.length > 1 ? 'ren' : ''}
          </span>
        )}
      </div>

      {/* Children */}
      {hasChildren && (
        <div className={`relative ${depth > 0 ? 'ml-6' : ''}`}>
          {/* Vertical connector line */}
          <div className="absolute left-3 top-0 bottom-2 w-px bg-gray-200" />
          <div className="space-y-0.5">
            {node.children.map((child) => (
              <TreeNode key={child.id} node={child} depth={depth + 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function SplitTreeModal({ positionId, onClose }: SplitTreeModalProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['split-tree', positionId],
    queryFn: () => positionsApi.getSplitTree(positionId!),
    enabled: !!positionId,
  });

  return (
    <Dialog open={!!positionId} onClose={onClose} title="Split Tree" className="max-w-lg">
      {isLoading && (
        <div className="flex justify-center py-8">
          <Spinner className="h-6 w-6" />
        </div>
      )}

      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {(error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to load split tree'}
        </div>
      )}

      {data && !isLoading && (
        <div className="space-y-1">
          {data.children?.length === 0 && !data.is_parent ? (
            <p className="py-4 text-center text-sm text-gray-500">This position has no splits.</p>
          ) : (
            <TreeNode node={data as SplitTreeNode} depth={0} />
          )}
        </div>
      )}
    </Dialog>
  );
}
