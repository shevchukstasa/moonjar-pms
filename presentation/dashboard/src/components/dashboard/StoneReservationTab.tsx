import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/client';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';

interface StoneReservation {
  id: string;
  position_id: string;
  position_label: string;
  order_number: string;
  size_category: string;
  product_type: string;
  reserved_qty: number;
  reserved_sqm: number;
  stone_defect_pct: number;
  status: string;
}

interface DefectRate {
  size_category: string;
  product_type: string;
  defect_pct: number;
}

interface WeeklyReport {
  total_waste_pct: number;
  total_reserved_sqm: number;
  total_used_sqm: number;
  total_wasted_sqm: number;
}

interface StoneReservationTabProps {
  factoryId?: string;
}

export function StoneReservationTab({ factoryId }: StoneReservationTabProps) {
  const params = factoryId ? { factory_id: factoryId } : {};

  const { data: reservationsData, isLoading: reservationsLoading, error: reservationsError } = useQuery<{
    items: StoneReservation[];
    total: number;
  }>({
    queryKey: ['stone-reservations', params],
    queryFn: () => apiClient.get('/stone-reservations', { params }).then((r) => r.data),
    staleTime: 30_000,
  });

  const { data: defectRates, isLoading: ratesLoading } = useQuery<{ items: DefectRate[] }>({
    queryKey: ['stone-reservations-defect-rates', params],
    queryFn: () => apiClient.get('/stone-reservations/defect-rates', { params }).then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: weeklyReport, isLoading: weeklyLoading } = useQuery<WeeklyReport>({
    queryKey: ['stone-reservations-weekly', params],
    queryFn: () => apiClient.get('/stone-reservations/weekly-report', { params }).then((r) => r.data),
    staleTime: 60_000,
  });

  const isLoading = reservationsLoading || ratesLoading || weeklyLoading;

  if (isLoading) {
    return <div className="flex justify-center py-12"><Spinner /></div>;
  }

  if (reservationsError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-800">Error loading stone reservations</p>
      </div>
    );
  }

  const reservations = reservationsData?.items || [];
  const totalReservations = reservationsData?.total || 0;
  const totalSqm = reservations.reduce((sum, r) => sum + r.reserved_sqm, 0);
  const rates = defectRates?.items || [];

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="text-xs text-gray-500">Active Reservations</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{totalReservations}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-gray-500">Reserved SQM</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{totalSqm.toFixed(1)}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-gray-500">This Week Waste %</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {weeklyReport?.total_waste_pct != null ? `${weeklyReport.total_waste_pct.toFixed(1)}%` : '\u2014'}
          </div>
        </Card>
      </div>

      {/* Reservations table */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Active Reservations</h2>

        {reservations.length === 0 ? (
          <EmptyState title="No active reservations" description="Stone reservations will appear when positions are planned." />
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Position</th>
                  <th className="px-4 py-3">Order</th>
                  <th className="px-4 py-3">Size Cat.</th>
                  <th className="px-4 py-3">Product Type</th>
                  <th className="px-4 py-3 text-right">Reserved Qty</th>
                  <th className="px-4 py-3 text-right">Reserved SQM</th>
                  <th className="px-4 py-3 text-right">Defect %</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {reservations.map((r) => (
                  <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{r.position_label}</td>
                    <td className="px-4 py-3 text-gray-700">{r.order_number}</td>
                    <td className="px-4 py-3 text-gray-700">{r.size_category}</td>
                    <td className="px-4 py-3 text-gray-700">{r.product_type}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{r.reserved_qty}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{r.reserved_sqm.toFixed(2)}</td>
                    <td className={`px-4 py-3 text-right ${r.stone_defect_pct > 10 ? 'text-red-600 font-medium' : 'text-gray-700'}`}>
                      {r.stone_defect_pct.toFixed(1)}%
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                        r.status === 'active' ? 'bg-green-100 text-green-800 border-green-200'
                          : r.status === 'consumed' ? 'bg-gray-100 text-gray-600 border-gray-200'
                            : 'bg-yellow-100 text-yellow-800 border-yellow-200'
                      }`}>
                        {r.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Defect rates config (read-only) */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Defect Rates by Size x Product</h2>

        {rates.length === 0 ? (
          <Card className="border-gray-200 bg-gray-50/50">
            <p className="text-center text-sm text-gray-500">No defect rate configuration available</p>
          </Card>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Size Category</th>
                  <th className="px-4 py-3">Product Type</th>
                  <th className="px-4 py-3 text-right">Defect %</th>
                </tr>
              </thead>
              <tbody>
                {rates.map((rate, idx) => (
                  <tr key={idx} className="border-b border-gray-100">
                    <td className="px-4 py-3 text-gray-900">{rate.size_category}</td>
                    <td className="px-4 py-3 text-gray-700">{rate.product_type}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-700">{rate.defect_pct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
