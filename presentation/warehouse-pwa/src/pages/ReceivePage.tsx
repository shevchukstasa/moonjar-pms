import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { useAuthStore } from '../stores/authStore';

interface DeliveryItem {
  id: string;
  material_id: string;
  material_name: string;
  expected_quantity: number;
  unit: string;
  supplier_name: string | null;
  status: string;
  purchase_order_number?: string;
}

interface ReceiveState {
  deliveryId: string;
  materialId: string;
  materialName: string;
  expected: number;
  actual: string;
  unit: string;
  notes: string;
}

export function ReceivePage() {
  const { selectedFactoryId } = useAuthStore();
  const [deliveries, setDeliveries] = useState<DeliveryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [receiving, setReceiving] = useState<ReceiveState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchDeliveries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Try purchase orders endpoint first, fall back to materials with pending receives
      try {
        const res = await apiClient.get('/purchaser/deliveries', {
          params: { factory_id: selectedFactoryId, status: 'delivered' },
        });
        setDeliveries(res.data.items ?? res.data ?? []);
      } catch {
        // Fallback: list materials that may need receiving
        const res = await apiClient.get('/materials', {
          params: { factory_id: selectedFactoryId, per_page: 50 },
        });
        const items = (res.data.items ?? res.data ?? []).map(
          (m: { id: string; name: string; unit: string; supplier_name?: string | null }) => ({
            id: m.id,
            material_id: m.id,
            material_name: m.name,
            expected_quantity: 0,
            unit: m.unit,
            supplier_name: m.supplier_name ?? null,
            status: 'pending',
          }),
        );
        setDeliveries(items);
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Gagal memuat data pengiriman.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedFactoryId]);

  useEffect(() => {
    fetchDeliveries();
  }, [fetchDeliveries]);

  const openReceiveForm = (d: DeliveryItem) => {
    setSuccessMsg(null);
    setReceiving({
      deliveryId: d.id,
      materialId: d.material_id,
      materialName: d.material_name,
      expected: d.expected_quantity,
      actual: d.expected_quantity > 0 ? String(d.expected_quantity) : '',
      unit: d.unit,
      notes: '',
    });
  };

  const handleConfirmReceive = async () => {
    if (!receiving || !selectedFactoryId) return;
    const qty = parseFloat(receiving.actual);
    if (isNaN(qty) || qty <= 0) return;

    setSubmitting(true);
    setError(null);
    try {
      await apiClient.post('/materials/transactions', {
        material_id: receiving.materialId,
        factory_id: selectedFactoryId,
        type: 'receive',
        quantity: qty,
        notes: receiving.notes || undefined,
      });
      setSuccessMsg(`${receiving.materialName}: ${qty} ${receiving.unit} diterima.`);
      setReceiving(null);
      fetchDeliveries();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Gagal menyimpan penerimaan.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-4 max-w-lg mx-auto">
      <h1 className="text-lg font-bold text-gray-900 mb-4">Terima Material</h1>

      {/* Success */}
      {successMsg && (
        <div className="bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3 rounded-lg mb-4 flex items-center gap-2">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          {successMsg}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {/* Receive Modal/Form */}
      {receiving && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-end sm:items-center justify-center p-4">
          <div className="bg-white rounded-t-2xl sm:rounded-2xl w-full max-w-md shadow-xl">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="text-base font-bold text-gray-900">Konfirmasi Penerimaan</h2>
              <p className="text-sm text-gray-500 mt-0.5">{receiving.materialName}</p>
            </div>
            <div className="p-4 space-y-4">
              {receiving.expected > 0 && (
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-500">Jumlah diharapkan</span>
                  <span className="font-semibold text-gray-900">
                    {receiving.expected} {receiving.unit}
                  </span>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Jumlah diterima ({receiving.unit})
                </label>
                <input
                  type="number"
                  inputMode="decimal"
                  step="any"
                  min="0"
                  value={receiving.actual}
                  onChange={(e) => setReceiving({ ...receiving, actual: e.target.value })}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 text-lg font-semibold bg-white outline-none focus:ring-2 focus:ring-primary-400 touch-target"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Catatan</label>
                <input
                  type="text"
                  value={receiving.notes}
                  onChange={(e) => setReceiving({ ...receiving, notes: e.target.value })}
                  placeholder="Opsional..."
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 text-base bg-white outline-none focus:ring-2 focus:ring-primary-400 touch-target"
                />
              </div>
            </div>
            <div className="p-4 pt-2 flex gap-2">
              <button
                onClick={() => setReceiving(null)}
                className="flex-1 py-3 rounded-lg border border-gray-300 text-gray-600 font-semibold text-sm hover:bg-gray-50 transition-colors touch-target"
              >
                Batal
              </button>
              <button
                onClick={handleConfirmReceive}
                disabled={submitting || !receiving.actual || parseFloat(receiving.actual) <= 0}
                className="flex-1 py-3 rounded-lg bg-green-600 hover:bg-green-700 text-white font-semibold text-sm transition-colors disabled:opacity-50 touch-target"
              >
                {submitting ? 'Menyimpan...' : 'Konfirmasi'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <svg className="animate-spin h-8 w-8 text-primary-500" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      )}

      {/* Empty state */}
      {!loading && deliveries.length === 0 && (
        <div className="text-center py-12">
          <svg className="mx-auto mb-3 text-gray-300" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M21 16V8a2 2 0 0 0-1-1.73L13 2.27a2 2 0 0 0-2 0L4 6.27A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
          </svg>
          <p className="text-gray-500 text-sm">Tidak ada pengiriman masuk.</p>
          <button onClick={fetchDeliveries} className="mt-3 text-primary-600 text-sm font-semibold">
            Muat Ulang
          </button>
        </div>
      )}

      {/* Deliveries list */}
      {!loading && deliveries.length > 0 && (
        <div className="space-y-3">
          {deliveries.map((d) => (
            <div
              key={d.id}
              className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden"
            >
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-gray-900 text-sm leading-tight">
                    {d.material_name}
                  </h3>
                  {d.purchase_order_number && (
                    <span className="text-xs text-gray-400 ml-2 flex-shrink-0">
                      PO {d.purchase_order_number}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                  {d.expected_quantity > 0 && (
                    <span>
                      {d.expected_quantity} {d.unit}
                    </span>
                  )}
                  {d.supplier_name && <span>{d.supplier_name}</span>}
                </div>
                <button
                  onClick={() => openReceiveForm(d)}
                  className="w-full py-2.5 rounded-lg bg-green-600 hover:bg-green-700 text-white font-semibold text-sm transition-colors touch-target"
                >
                  Konfirmasi Penerimaan
                </button>
              </div>
            </div>
          ))}

          {/* Refresh */}
          <button
            onClick={fetchDeliveries}
            className="w-full py-3 text-sm text-primary-600 font-semibold hover:text-primary-700"
          >
            Muat Ulang
          </button>
        </div>
      )}
    </div>
  );
}
