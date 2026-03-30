import { useState, useMemo } from 'react';
import { useUiStore } from '@/stores/uiStore';
import { useTabloStore } from '@/stores/tabloStore';
import {
  useGlazingSchedule,
  useFiringSchedule,
  useSortingSchedule,
  useKilnSchedule,
  useBatches,
} from '@/hooks/useSchedule';
import { Card } from '@/components/ui/Card';
import { Tabs } from '@/components/ui/Tabs';
import { Spinner } from '@/components/ui/Spinner';
import { FactorySelector } from '@/components/layout/FactorySelector';
import { SectionTable } from '@/components/tablo/SectionTable';
import { TabloFilters } from '@/components/tablo/TabloFilters';
import { KilnCard } from '@/components/tablo/KilnCard';
import { BatchGroup } from '@/components/tablo/BatchGroup';
import { ProductionSplitModal } from '@/components/tablo/ProductionSplitModal';
import { MergeDialog } from '@/components/tablo/MergeDialog';
import { SplitTreeModal } from '@/components/tablo/SplitTreeModal';
import type { PositionItem } from '@/components/tablo/PositionRow';

const TABLO_TABS = [
  { id: 'glazing', label: 'Glazing' },
  { id: 'firing', label: 'Firing' },
  { id: 'sorting', label: 'Sorting' },
  { id: 'kilns', label: 'Kilns' },
];

export default function TabloDashboard() {
  const activeFactoryId = useUiStore((s) => s.activeFactoryId);
  const { activeTab, setActiveTab } = useTabloStore();
  const [splitModalPosition, setSplitModalPosition] = useState<PositionItem | null>(null);
  const [mergeDialogPosition, setMergeDialogPosition] = useState<PositionItem | null>(null);
  const [splitTreePositionId, setSplitTreePositionId] = useState<string | null>(null);

  // Fetch data for all sections
  const { data: glazingData, isLoading: glazingLoading, isError: glazingError } = useGlazingSchedule(activeFactoryId);
  const { data: firingData, isLoading: firingLoading, isError: firingError } = useFiringSchedule(activeFactoryId);
  const { data: sortingData, isLoading: sortingLoading, isError: sortingError } = useSortingSchedule(activeFactoryId);
  const { data: kilnData, isLoading: kilnLoading, isError: kilnError } = useKilnSchedule(activeFactoryId);

  // Fetch batches for the firing tab — batch metadata (resource_name, date, status)
  const batchParams = activeFactoryId ? { factory_id: activeFactoryId } : undefined;
  const { data: batchesData, isLoading: batchesLoading } = useBatches(batchParams);

  const isLoading =
    (activeTab === 'glazing' && glazingLoading) ||
    (activeTab === 'firing' && (firingLoading || batchesLoading)) ||
    (activeTab === 'sorting' && sortingLoading) ||
    (activeTab === 'kilns' && kilnLoading);
  const hasError = glazingError || firingError || sortingError || kilnError;

  const glazingPositions: PositionItem[] = glazingData?.items || [];
  const firingPositions: PositionItem[] = firingData?.items || [];
  const sortingPositions: PositionItem[] = sortingData?.items || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const kilns: any[] = kilnData?.items || [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const batchItems: any[] = batchesData?.items || [];

  // Group firing positions by batch for BatchGroup rendering
  const { firingBatches, unbatchedFiringPositions } = useMemo(() => {
    const batchMap = new Map<string, PositionItem[]>();
    const unbatched: PositionItem[] = [];
    for (const p of firingPositions) {
      if (p.batch_id) {
        const arr = batchMap.get(p.batch_id) || [];
        arr.push(p);
        batchMap.set(p.batch_id, arr);
      } else {
        unbatched.push(p);
      }
    }
    // Build BatchInfo objects from batch metadata
    const batches = batchItems
      .filter((b) => batchMap.has(b.id))
      .map((b) => ({
        info: {
          id: b.id as string,
          batch_date: b.batch_date as string | null,
          resource_name: b.resource_name as string,
          status: b.status as string,
          total_pcs: b.total_pcs as number,
          positions_count: b.positions_count as number,
        },
        positions: batchMap.get(b.id) || [],
      }));
    return { firingBatches: batches, unbatchedFiringPositions: unbatched };
  }, [firingPositions, batchItems]);

  const sectionPositions: Record<string, PositionItem[]> = {
    glazing: glazingPositions,
    firing: firingPositions,
    sorting: sortingPositions,
  };

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-gray-900">Production Tablo</h1>
          <p className="mt-0.5 md:mt-1 text-xs md:text-sm text-gray-500">
            Drag to reorder priorities, change statuses inline
          </p>
        </div>
        <div className="w-full sm:w-auto">
          <FactorySelector />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <Card>
          <div className="text-sm text-gray-500">Glazing</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {glazingData?.total ?? '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Firing</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {firingData?.total ?? '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Sorting</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {sortingData?.total ?? '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Kilns</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{kilns.length}</div>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs tabs={TABLO_TABS} activeTab={activeTab} onChange={setActiveTab} />

      {/* Filters */}
      {activeTab !== 'kilns' && <TabloFilters />}

      {/* API Error */}
      {hasError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">⚠ Error loading schedule data. Try refreshing.</p>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      ) : activeTab === 'kilns' ? (
        /* Kilns tab */
        kilns.length === 0 ? (
          <div className="py-8 text-center text-gray-400">No kilns found</div>
        ) : (
          <div className="space-y-4">
            {kilns.map((k) => (
              <KilnCard key={k.kiln?.id ?? k.id} kiln={k.kiln ?? k} batches={k.batches ?? []} />
            ))}
          </div>
        )
      ) : activeTab === 'firing' && firingBatches.length > 0 ? (
        /* Firing tab with batch groups */
        <div className="space-y-4">
          {firingBatches.map((bg) => (
            <BatchGroup key={bg.info.id} batch={bg.info} positions={bg.positions} />
          ))}
          {unbatchedFiringPositions.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-gray-600">Unbatched positions</h3>
              <SectionTable
                positions={unbatchedFiringPositions}
                section="firing"
                onSplitPosition={setSplitModalPosition}
                onMergePosition={setMergeDialogPosition}
                onViewSplitTree={setSplitTreePositionId}
              />
            </div>
          )}
        </div>
      ) : (
        /* Section tabs (glazing/firing/sorting — flat list) */
        sectionPositions[activeTab]?.length === 0 ? (
          <div className="py-8 text-center text-gray-400">
            No positions in this section
          </div>
        ) : (
          <SectionTable
            positions={sectionPositions[activeTab]}
            section={activeTab}
            onSplitPosition={setSplitModalPosition}
            onMergePosition={setMergeDialogPosition}
            onViewSplitTree={setSplitTreePositionId}
          />
        )
      )}

      {/* Production Split Modal */}
      {splitModalPosition && (
        <ProductionSplitModal
          position={splitModalPosition}
          onClose={() => setSplitModalPosition(null)}
        />
      )}

      {/* Merge Dialog */}
      {mergeDialogPosition && (
        <MergeDialog
          position={mergeDialogPosition}
          onClose={() => setMergeDialogPosition(null)}
        />
      )}

      {/* Split Tree Modal */}
      <SplitTreeModal
        positionId={splitTreePositionId}
        onClose={() => setSplitTreePositionId(null)}
      />
    </div>
  );
}
