import { useMaterialReservations } from '@/hooks/usePositions';
import { Spinner } from '@/components/ui/Spinner';
import type { MaterialReservationGroup, MaterialReservationGroupItem } from '@/api/positions';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

// Smart unit display: for kg values below 0.1, show in grams instead.
// Avoids misleading "0.00 kg" for small pigments like 1.6 g of Golden brown.
function formatQty(value: number, unit: string): { value: string; unit: string } {
  if (unit === 'kg' && Math.abs(value) < 0.1 && value !== 0) {
    return { value: (value * 1000).toFixed(1), unit: 'g' };
  }
  if (unit === 'kg') return { value: value.toFixed(3), unit };
  return { value: value.toFixed(2), unit };
}

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

const GROUP_STYLES: Record<string, { border: string; bg: string; icon: string }> = {
  stone: { border: 'border-l-amber-500', bg: 'bg-amber-50', icon: '🪨' },
  recipe: { border: 'border-l-blue-500', bg: 'bg-blue-50', icon: '🎨' },
  packaging: { border: 'border-l-emerald-500', bg: 'bg-emerald-50', icon: '📦' },
};

function GroupSection({ group, onClose }: { group: MaterialReservationGroup; onClose: () => void }) {
  const style = GROUP_STYLES[group.group] || { border: 'border-l-gray-400', bg: 'bg-gray-50', icon: '' };
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const role = user?.role;
  const canConfigurePackaging = role === 'owner' || role === 'administrator' || role === 'production_manager';

  const handleReceive = (materialId: string | null | undefined) => {
    if (!materialId) return;
    onClose();
    navigate(`/manager/materials?receive=${materialId}`);
  };

  const handleConfigurePackaging = () => {
    onClose();
    navigate('/admin/packaging');
  };

  if (group.items.length === 0) {
    return (
      <div className={`rounded-lg border-l-4 ${style.border} ${style.bg} p-4 mb-3`}>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-gray-700">
            {style.icon} {group.label}
          </h4>
          {group.group === 'packaging' && canConfigurePackaging && (
            <button
              onClick={handleConfigurePackaging}
              className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-700"
            >
              + Configure boxes
            </button>
          )}
        </div>
        <p className="text-xs text-gray-500 italic">
          {group.group === 'packaging'
            ? 'No box rules configured for this size. Click "Configure boxes" to set up.'
            : 'Not configured'}
        </p>
      </div>
    );
  }

  return (
    <div className={`rounded-lg border-l-4 ${style.border} mb-3 overflow-hidden`}>
      <div className={`${style.bg} px-4 py-2`}>
        <h4 className="text-sm font-semibold text-gray-700">
          {style.icon} {group.label}
        </h4>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            <th className="px-4 pb-2 pt-2 pr-4">Material</th>
            <th className="pb-2 pt-2 pr-4 text-right">Required</th>
            <th className="pb-2 pt-2 pr-4 text-right">Reserved</th>
            <th className="pb-2 pt-2 pr-4 text-right">Available</th>
            <th className="pb-2 pt-2 pr-4 text-right">Deficit</th>
            <th className="pb-2 pt-2 px-2">Status</th>
            <th className="pb-2 pt-2 px-2"></th>
          </tr>
        </thead>
        <tbody>
          {group.items.map((m: MaterialReservationGroupItem, idx: number) => {
            const req = formatQty(m.required, m.unit);
            const res = formatQty(m.reserved, m.unit);
            const avl = formatQty(m.available, m.unit);
            const dfc = formatQty(m.deficit, m.unit);
            const showReceive = (m.status === 'insufficient' || m.status === 'partially_reserved') && m.material_id;

            return (
              <tr key={`${group.group}-${idx}`} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-2 px-4 pr-4">
                  <div className="font-medium text-gray-900">{m.material}</div>
                </td>
                <td className="py-2 pr-4 text-right font-mono text-gray-700">
                  {req.value} <span className="text-xs text-gray-400">{req.unit}</span>
                </td>
                <td className="py-2 pr-4 text-right font-mono text-gray-700">
                  {res.value}
                </td>
                <td className={`py-2 pr-4 text-right font-mono ${m.available < 0 ? 'text-red-600 font-semibold' : 'text-gray-700'}`}>
                  {avl.value}
                </td>
                <td className={`py-2 pr-4 text-right font-mono ${m.deficit > 0 ? 'text-red-600 font-semibold' : 'text-gray-400'}`}>
                  {m.deficit > 0 ? dfc.value : '\u2014'}
                </td>
                <td className="py-2 px-2">
                  <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[m.status] || 'bg-gray-100 text-gray-600'}`}>
                    {STATUS_LABELS[m.status] || m.status}
                  </span>
                </td>
                <td className="py-2 px-2">
                  {showReceive && (
                    <button
                      onClick={() => handleReceive(m.material_id)}
                      className="rounded-md bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700"
                      title="Receive this material to warehouse"
                    >
                      + Receive
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

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

  // Use new grouped response if available, otherwise fall back to legacy flat view
  const hasGroups = data.groups && data.groups.length > 0;

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
            &times;
          </button>
        </div>

        {hasGroups ? (
          <div className="space-y-1">
            {data.groups!.map((g) => (
              <GroupSection key={g.group} group={g} onClose={onClose} />
            ))}
          </div>
        ) : !data.has_recipe ? (
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
                    {m.deficit > 0 ? m.deficit.toFixed(2) : '\u2014'}
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
