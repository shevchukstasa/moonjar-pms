import { useState, useMemo } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable';
import { PositionRow, type PositionItem } from './PositionRow';
import { useReorderPositions } from '@/hooks/useSchedule';
import { useTabloStore } from '@/stores/tabloStore';

interface Props {
  positions: PositionItem[];
  section: string;
}

export function SectionTable({ positions, section }: Props) {
  const reorder = useReorderPositions();
  const filters = useTabloStore((s) => s.filters);
  const [items, setItems] = useState<PositionItem[]>([]);

  // Sync positions from server, but keep local order during drag
  const sortedPositions = useMemo(() => {
    const sorted = [...positions].sort((a, b) => {
      // 1. Manual priority
      const pa = a.priority_order ?? 0;
      const pb = b.priority_order ?? 0;
      if (pa !== pb) return pa - pb;
      // 2. Group by order (order_id keeps same-order positions together)
      if (a.order_id < b.order_id) return -1;
      if (a.order_id > b.order_id) return 1;
      // 3. Position number within the order
      const na = a.position_number ?? 0;
      const nb = b.position_number ?? 0;
      if (na !== nb) return na - nb;
      // 4. Split index for split positions
      return (a.split_index ?? 0) - (b.split_index ?? 0);
    });
    setItems(sorted);
    return sorted;
  }, [positions]);

  // Apply filters
  const filtered = useMemo(() => {
    let result = items.length > 0 ? items : sortedPositions;
    if (filters.search) {
      const s = filters.search.toLowerCase();
      result = result.filter(
        (p) =>
          p.order_number.toLowerCase().includes(s) ||
          p.color.toLowerCase().includes(s),
      );
    }
    if (filters.status) {
      result = result.filter((p) => p.status === filters.status);
    }
    return result;
  }, [items, sortedPositions, filters]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = items.findIndex((p) => p.id === active.id);
    const newIndex = items.findIndex((p) => p.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const reordered = arrayMove(items, oldIndex, newIndex);
    setItems(reordered);

    // Send new order to backend
    reorder.mutate(reordered.map((p) => p.id));
  };

  // Totals
  const totalPcs = filtered.reduce((sum, p) => sum + (p.quantity || 0), 0);

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={filtered.map((p) => p.id)} strategy={verticalListSortingStrategy}>
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50 text-xs font-medium uppercase text-gray-500">
              <tr>
                <th className="w-8 px-2 py-2" />
                <th className="px-3 py-2">Order</th>
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Color</th>
                <th className="px-3 py-2">Size</th>
                <th className="px-3 py-2">Application</th>
                <th className="px-3 py-2">Collection</th>
                <th className="px-3 py-2 text-right">Qty</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2 text-right">Delay</th>
              </tr>
            </thead>
            <tbody className="divide-y bg-white">
              {filtered.map((p, idx) => (
                <PositionRow
                  key={p.id}
                  position={p}
                  index={idx}
                  section={section}
                />
              ))}
            </tbody>
            <tfoot className="border-t bg-gray-50">
              <tr>
                <td colSpan={7} className="px-3 py-2 text-xs font-semibold text-gray-600">
                  Total: {filtered.length} positions
                </td>
                <td className="px-3 py-2 text-right text-xs font-semibold text-gray-600">
                  {totalPcs} pcs
                </td>
                <td colSpan={3} />
              </tr>
            </tfoot>
          </table>
        </SortableContext>
      </DndContext>
    </div>
  );
}
