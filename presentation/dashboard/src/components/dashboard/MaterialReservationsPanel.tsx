import { useMaterialReservations } from '@/hooks/usePositions';
import { Spinner } from '@/components/ui/Spinner';

interface MaterialReservationsPanelProps {
  positionId: string;
  onClose: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  reserved: 'bg-green-100 text-green-800',
  force_reserved: 'bg-amber-100 text-amber-800',
  partially_reserved: 'bg-yellow-100 text-yellow-800',
  available: 'bg-blue-100 text-blue-800',
  insufficient: 'bg-red-100 text-red-800',
};

const STATUS_LABELS: Record<string, string> = {
  reserved: 'Reserved',
  force_reserved: 'Force Reserved',
  partially_reserved: 'Partial',
  available: 'Available',
  insufficient: 'Insufficient',
};

export function MaterialReservationsPanel({ positionId, onClose }: MaterialReservationsPanelProps) {
  const { data, isLoading, error } = useMaterialReservations(positionId);

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
        <div className="rounded-xl bg-white p-8 shadow-2xl" onClick={(e) => e.stopPropagation()}>
          <Spinner />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
        <div className="rounded-xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
          <p className="text-red-600">Error loading material reservations</p>
          <button className="mt-3 text-sm text-blue-600 underline" onClick={onClose}>Close</button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="w-full max-w-2xl max-h-[80vh] overflow-auto rounded-xl bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Material Reservations</h3>
            {data.recipe_name && (
              <p className="text-sm text-gray-500">Recipe: {data.recipe_name}</p>
            )}
          </div>
          <button
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        {!data.has_recipe ? (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center text-sm text-gray-500">
            No recipe assigned — material reservations not applicable
          </div>
        ) : data.materials.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center text-sm text-gray-500">
            Recipe has no materials configured
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="pb-2 pr-4">Material</th>
                <th className="pb-2 pr-4 text-right">Required</th>
                <th className="pb-2 pr-4 text-right">Reserved</th>
                <th className="pb-2 pr-4 text-right">Available</th>
                <th className="pb-2 pr-4 text-right">Deficit</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.materials.map((m) => (
                <tr key={m.material_id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-2 pr-4">
                    <div className="font-medium text-gray-900">{m.name}</div>
                    <div className="text-xs text-gray-400">{m.type}</div>
                  </td>
                  <td className="py-2 pr-4 text-right font-mono text-gray-700">{m.required.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-right font-mono text-gray-700">{m.reserved.toFixed(2)}</td>
                  <td className={`py-2 pr-4 text-right font-mono ${m.available < 0 ? 'text-red-600 font-semibold' : 'text-gray-700'}`}>
                    {m.available.toFixed(2)}
                  </td>
                  <td className={`py-2 pr-4 text-right font-mono ${m.deficit > 0 ? 'text-red-600 font-semibold' : 'text-gray-400'}`}>
                    {m.deficit > 0 ? m.deficit.toFixed(2) : '—'}
                  </td>
                  <td className="py-2">
                    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[m.status] || 'bg-gray-100 text-gray-600'}`}>
                      {STATUS_LABELS[m.status] || m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
