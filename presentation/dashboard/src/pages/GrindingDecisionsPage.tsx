import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useUiStore } from '@/stores/uiStore';
import {
  grindingStockApi,
  type GrindingStockItem,
  type GrindingStockDecisionInput,
} from '@/api/grindingStock';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/Table';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { Pagination } from '@/components/ui/Pagination';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { FactorySelector } from '@/components/layout/FactorySelector';

const STATUS_TABS = [
  { id: 'all', label: 'All' },
  { id: 'pending', label: 'Pending' },
  { id: 'grinding', label: 'Decided (Grind)' },
  { id: 'sent_to_mana', label: 'Sent to Mana' },
];

function formatDate(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

/* ──────────────────────────────────────────────────── */
/*  Summary Cards                                       */
/* ──────────────────────────────────────────────────── */

function SummaryCards({ factoryId }: { factoryId: string | null }) {
  const { data, isLoading } = useQuery({
    queryKey: ['grinding-stock-stats'],
    queryFn: () => grindingStockApi.stats(),
  });

  if (isLoading) return <div className="flex justify-center py-4"><Spinner className="h-6 w-6" /></div>;

  const stats = data?.stats || {};
  let total = 0;
  let pending = 0;
  let grinding = 0;
  let sentToMana = 0;

  for (const [fid, counts] of Object.entries(stats)) {
    if (factoryId && fid !== factoryId) continue;
    for (const [status, count] of Object.entries(counts)) {
      total += count;
      if (status === 'pending') pending += count;
      else if (status === 'grinding') grinding += count;
      else if (status === 'sent_to_mana') sentToMana += count;
    }
  }

  const cards = [
    { label: 'Total Items', value: total, color: 'text-gray-900' },
    { label: 'Pending Decision', value: pending, color: 'text-amber-600' },
    { label: 'Decided (Grind)', value: grinding, color: 'text-green-600' },
    { label: 'Sent to Mana', value: sentToMana, color: 'text-red-600' },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((c) => (
        <Card key={c.label}>
          <p className="text-sm text-gray-500">{c.label}</p>
          <p className={`mt-1 text-2xl font-bold ${c.color}`}>{c.value}</p>
        </Card>
      ))}
    </div>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Action Buttons                                      */
/* ──────────────────────────────────────────────────── */

function ActionButtons({
  item,
  onDecide,
  isLoading,
}: {
  item: GrindingStockItem;
  onDecide: (id: string, decision: GrindingStockDecisionInput) => void;
  isLoading: boolean;
}) {
  const [confirmMana, setConfirmMana] = useState(false);

  if (item.status !== 'pending') {
    return <Badge status={item.status} />;
  }

  return (
    <>
      <div className="flex gap-1.5">
        <Button
          size="sm"
          className="bg-green-500 text-white hover:bg-green-600"
          disabled={isLoading}
          onClick={() => onDecide(item.id, { decision: 'grinding' })}
        >
          Grind
        </Button>
        <Button
          size="sm"
          className="bg-amber-400 text-gray-900 hover:bg-amber-500"
          disabled={isLoading}
          onClick={() => onDecide(item.id, { decision: 'pending' })}
        >
          Hold
        </Button>
        <Button
          size="sm"
          variant="danger"
          disabled={isLoading}
          onClick={() => setConfirmMana(true)}
        >
          Mana
        </Button>
      </div>
      <ConfirmDialog
        open={confirmMana}
        onClose={() => setConfirmMana(false)}
        onConfirm={() => onDecide(item.id, { decision: 'sent_to_mana' })}
        title="Send to Mana"
        message={`Send "${item.color} / ${item.size}" (qty ${item.quantity}) to Mana? This action marks the item for external processing.`}
      />
    </>
  );
}

/* ──────────────────────────────────────────────────── */
/*  Main Page                                           */
/* ──────────────────────────────────────────────────── */

export default function GrindingDecisionsPage() {
  const factoryId = useUiStore((s) => s.activeFactoryId);
  const [tab, setTab] = useState('all');
  const [page, setPage] = useState(1);
  const perPage = 50;
  const queryClient = useQueryClient();

  const statusFilter = tab === 'all' ? undefined : tab;

  const { data, isLoading } = useQuery({
    queryKey: ['grinding-stock', factoryId, statusFilter, page],
    queryFn: () =>
      grindingStockApi.list({
        factory_id: factoryId || undefined,
        status: statusFilter,
        page,
        per_page: perPage,
      }),
  });

  const decideMutation = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: GrindingStockDecisionInput }) =>
      grindingStockApi.decide(id, decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['grinding-stock'] });
      queryClient.invalidateQueries({ queryKey: ['grinding-stock-stats'] });
    },
  });

  const handleDecide = (id: string, decision: GrindingStockDecisionInput) => {
    decideMutation.mutate({ id, decision });
  };

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / perPage));

  const columns = [
    {
      key: 'color',
      header: 'Color',
      render: (item: GrindingStockItem) => (
        <span className="font-medium text-gray-900">{item.color}</span>
      ),
    },
    {
      key: 'size',
      header: 'Size',
      render: (item: GrindingStockItem) => item.size,
    },
    {
      key: 'quantity',
      header: 'Qty',
      render: (item: GrindingStockItem) => (
        <span className="font-semibold">{item.quantity}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item: GrindingStockItem) => <Badge status={item.status} />,
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (item: GrindingStockItem) => formatDate(item.created_at),
    },
    {
      key: 'decided_at',
      header: 'Decided',
      render: (item: GrindingStockItem) => formatDate(item.decided_at),
    },
    {
      key: 'notes',
      header: 'Notes',
      render: (item: GrindingStockItem) => (
        <span className="max-w-[200px] truncate text-gray-500">{item.notes || '-'}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (item: GrindingStockItem) => (
        <ActionButtons
          item={item}
          onDecide={handleDecide}
          isLoading={decideMutation.isPending}
        />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Grinding Decisions</h1>
          <p className="mt-1 text-sm text-gray-500">
            Review and decide on grinding stock items
          </p>
        </div>
        <FactorySelector />
      </div>

      {/* Summary */}
      <SummaryCards factoryId={factoryId} />

      {/* Status Tabs */}
      <Tabs
        tabs={STATUS_TABS}
        activeTab={tab}
        onChange={(id) => {
          setTab(id);
          setPage(1);
        }}
      />

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : items.length === 0 ? (
        <Card>
          <p className="py-8 text-center text-sm text-gray-500">
            No grinding stock items found.
          </p>
        </Card>
      ) : (
        <>
          <DataTable columns={columns} data={items as unknown as Record<string, unknown>[]} />
          {totalPages > 1 && (
            <div className="flex justify-center">
              <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
            </div>
          )}
        </>
      )}

      {/* Error toast */}
      {decideMutation.isError && (
        <div className="fixed bottom-4 right-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 shadow-lg">
          Failed to update decision. Please try again.
        </div>
      )}
    </div>
  );
}
