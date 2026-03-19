import { useState } from 'react';
import { useUiStore } from '@/stores/uiStore';
import { useTabloStore } from '@/stores/tabloStore';
import {
  useGlazingSchedule,
  useFiringSchedule,
  useSortingSchedule,
  useKilnSchedule,
} from '@/hooks/useSchedule';
import { Card } from '@/components/ui/Card';
import { Tabs } from '@/components/ui/Tabs';
import { Spinner } from '@/components/ui/Spinner';
import { FactorySelector } from '@/components/layout/FactorySelector';
import { SectionTable } from '@/components/tablo/SectionTable';
import { TabloFilters } from '@/components/tablo/TabloFilters';
import { KilnCard } from '@/components/tablo/KilnCard';
import { ProductionSplitModal } from '@/components/tablo/ProductionSplitModal';
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

  // Fetch data for all sections
  const { data: glazingData, isLoading: glazingLoading, isError: glazingError } = useGlazingSchedule(activeFactoryId);
  const { data: firingData, isLoading: firingLoading, isError: firingError } = useFiringSchedule(activeFactoryId);
  const { data: sortingData, isLoading: sortingLoading, isError: sortingError } = useSortingSchedule(activeFactoryId);
  const { data: kilnData, isLoading: kilnLoading, isError: kilnError } = useKilnSchedule(activeFactoryId);

  const isLoading =
    (activeTab === 'glazing' && glazingLoading) ||
    (activeTab === 'firing' && firingLoading) ||
    (activeTab === 'sorting' && sortingLoading) ||
    (activeTab === 'kilns' && kilnLoading);
  const hasError = glazingError || firingError || sortingError || kilnError;

  const glazingPositions: PositionItem[] = glazingData?.items || [];
  const firingPositions: PositionItem[] = firingData?.items || [];
  const sortingPositions: PositionItem[] = sortingData?.items || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const kilns: any[] = kilnData?.items || [];

  const sectionPositions: Record<string, PositionItem[]> = {
    glazing: glazingPositions,
    firing: firingPositions,
    sorting: sortingPositions,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Production Tablo</h1>
          <p className="mt-1 text-sm text-gray-500">
            Drag to reorder priorities, change statuses inline
          </p>
        </div>
        <FactorySelector />
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
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
              <KilnCard key={k.kiln.id} kiln={k.kiln} batches={k.batches} />
            ))}
          </div>
        )
      ) : (
        /* Section tabs (glazing/firing/sorting) */
        sectionPositions[activeTab]?.length === 0 ? (
          <div className="py-8 text-center text-gray-400">
            No positions in this section
          </div>
        ) : (
          <SectionTable
            positions={sectionPositions[activeTab]}
            section={activeTab}
            onSplitPosition={setSplitModalPosition}
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
    </div>
  );
}
