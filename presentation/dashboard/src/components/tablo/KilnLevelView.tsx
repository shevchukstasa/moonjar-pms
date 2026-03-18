import { Badge } from '@/components/ui/Badge';

interface PositionBrief {
  id: string;
  order_number: string;
  color: string;
  size: string;
  quantity: number;
  status: string;
  product_type: string;
  placement_level?: number | null;
  loading_method?: 'flat' | 'edge' | null;
  is_filler?: boolean;
}

interface Props {
  positions: PositionBrief[];
}

export function KilnLevelView({ positions }: Props) {
  // Group positions by placement_level
  const levels = new Map<number, PositionBrief[]>();
  const unassigned: PositionBrief[] = [];

  for (const p of positions) {
    if (p.placement_level != null && p.placement_level > 0) {
      const arr = levels.get(p.placement_level) || [];
      arr.push(p);
      levels.set(p.placement_level, arr);
    } else {
      unassigned.push(p);
    }
  }

  const sortedLevels = [...levels.entries()].sort(([a], [b]) => a - b);

  return (
    <div className="space-y-2">
      {sortedLevels.map(([level, items]) => (
        <div key={level}>
          <div className="flex items-center gap-2 px-4 py-1 text-xs font-semibold text-gray-600 bg-gray-100">
            <span>Level {level}</span>
            <span className="text-gray-400">
              {items.reduce((s, p) => s + (p.quantity || 0), 0)} pcs
            </span>
          </div>
          <table className="w-full text-left text-sm">
            <tbody className="divide-y">
              {items.map((p) => (
                <tr key={p.id} className="bg-white">
                  <td className="px-4 py-1.5 text-xs">
                    <span className="flex items-center gap-1">
                      {p.order_number}
                      {p.is_filler && (
                        <span className="rounded bg-blue-100 px-1 py-0.5 text-[10px] text-blue-700">filler</span>
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-1.5 text-xs">{p.color}</td>
                  <td className="px-4 py-1.5 text-xs">{p.size}</td>
                  <td className="px-4 py-1.5 text-xs text-right">{p.quantity}</td>
                  <td className="px-4 py-1.5">
                    <span className="flex items-center gap-1">
                      <Badge status={p.status} />
                      {p.loading_method === 'edge' && (
                        <span className="rounded bg-purple-100 px-1 py-0.5 text-[10px] text-purple-700">edge</span>
                      )}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {unassigned.length > 0 && (
        <div>
          <div className="px-4 py-1 text-xs font-semibold text-gray-600 bg-gray-100">
            Unassigned level
          </div>
          <table className="w-full text-left text-sm">
            <tbody className="divide-y">
              {unassigned.map((p) => (
                <tr key={p.id} className="bg-white">
                  <td className="px-4 py-1.5 text-xs">
                    <span className="flex items-center gap-1">
                      {p.order_number}
                      {p.is_filler && (
                        <span className="rounded bg-blue-100 px-1 py-0.5 text-[10px] text-blue-700">filler</span>
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-1.5 text-xs">{p.color}</td>
                  <td className="px-4 py-1.5 text-xs">{p.size}</td>
                  <td className="px-4 py-1.5 text-xs text-right">{p.quantity}</td>
                  <td className="px-4 py-1.5">
                    <span className="flex items-center gap-1">
                      <Badge status={p.status} />
                      {p.loading_method === 'edge' && (
                        <span className="rounded bg-purple-100 px-1 py-0.5 text-[10px] text-purple-700">edge</span>
                      )}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
