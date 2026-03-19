import { useState, useRef, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';

interface PositionInfo {
  id: string;
  order_number: string;
  position_number: number;
  product_type: string;
  size: string;
  color: string;
  quantity: number;
  status: string;
  factory_name?: string;
}

export function ScanPage() {
  const [barcode, setBarcode] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PositionInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handleLookup = async (code: string) => {
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await apiClient.get('/positions/lookup', { params: { code: code.trim() } });
      setResult(res.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Posisi tidak ditemukan.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    handleLookup(barcode);
  };

  const handleClear = () => {
    setBarcode('');
    setResult(null);
    setError(null);
    inputRef.current?.focus();
  };

  const statusLabel: Record<string, string> = {
    new: 'Baru',
    in_production: 'Produksi',
    drying: 'Pengeringan',
    firing: 'Pembakaran',
    cooling: 'Pendinginan',
    sorting: 'Sortir',
    packing: 'Pengemasan',
    ready: 'Siap',
    shipped: 'Dikirim',
  };

  const statusColor: Record<string, string> = {
    new: 'bg-gray-200 text-gray-700',
    in_production: 'bg-blue-100 text-blue-700',
    drying: 'bg-yellow-100 text-yellow-700',
    firing: 'bg-orange-100 text-orange-700',
    cooling: 'bg-cyan-100 text-cyan-700',
    sorting: 'bg-purple-100 text-purple-700',
    packing: 'bg-indigo-100 text-indigo-700',
    ready: 'bg-green-100 text-green-700',
    shipped: 'bg-gray-100 text-gray-500',
  };

  return (
    <div className="p-4 max-w-lg mx-auto">
      {/* Scanner input */}
      <form onSubmit={handleSubmit} className="mb-6">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Pindai atau masukkan kode barcode
        </label>
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            inputMode="text"
            autoFocus
            value={barcode}
            onChange={(e) => setBarcode(e.target.value)}
            placeholder="Kode order / barcode..."
            className="flex-1 px-4 py-3 rounded-lg border border-gray-300 text-base bg-white outline-none focus:ring-2 focus:ring-primary-400 focus:border-primary-400 touch-target"
          />
          <button
            type="submit"
            disabled={loading || !barcode.trim()}
            className="px-5 py-3 rounded-lg bg-primary-600 text-white font-semibold text-base hover:bg-primary-700 disabled:opacity-50 touch-target transition-colors"
          >
            {loading ? (
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              'Cari'
            )}
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {/* Result card */}
      {result && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">
              #{result.order_number}-{result.position_number}
            </h2>
            <span
              className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                statusColor[result.status] ?? 'bg-gray-200 text-gray-700'
              }`}
            >
              {statusLabel[result.status] ?? result.status}
            </span>
          </div>

          <div className="p-4 space-y-3">
            <InfoRow label="Produk" value={result.product_type} />
            <InfoRow label="Ukuran" value={result.size} />
            <InfoRow label="Warna" value={result.color} />
            <InfoRow label="Jumlah" value={String(result.quantity)} />
            {result.factory_name && <InfoRow label="Pabrik" value={result.factory_name} />}
          </div>

          {/* Actions */}
          <div className="p-4 pt-2 flex gap-2">
            <button
              onClick={() => navigate('/receive')}
              className="flex-1 py-3 rounded-lg bg-green-600 hover:bg-green-700 text-white font-semibold text-sm transition-colors touch-target"
            >
              Terima Material
            </button>
            <button
              onClick={() => navigate('/inventory')}
              className="flex-1 py-3 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold text-sm transition-colors touch-target"
            >
              Lihat Stok
            </button>
          </div>
        </div>
      )}

      {/* Quick actions when no result */}
      {!result && !error && !loading && (
        <div className="mt-8 space-y-3">
          <p className="text-sm text-gray-500 text-center mb-4">Aksi cepat</p>
          <button
            onClick={() => navigate('/receive')}
            className="w-full py-4 rounded-xl bg-white border border-gray-200 shadow-sm text-left px-4 flex items-center gap-3 touch-target hover:bg-gray-50 transition-colors"
          >
            <span className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center text-green-600">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </span>
            <div>
              <p className="font-semibold text-gray-900 text-sm">Terima Material</p>
              <p className="text-xs text-gray-500">Konfirmasi penerimaan barang</p>
            </div>
          </button>
          <button
            onClick={() => navigate('/inventory')}
            className="w-full py-4 rounded-xl bg-white border border-gray-200 shadow-sm text-left px-4 flex items-center gap-3 touch-target hover:bg-gray-50 transition-colors"
          >
            <span className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
            </span>
            <div>
              <p className="font-semibold text-gray-900 text-sm">Lihat Stok</p>
              <p className="text-xs text-gray-500">Cek saldo material gudang</p>
            </div>
          </button>
        </div>
      )}

      {/* Clear button */}
      {(result || error) && (
        <button
          onClick={handleClear}
          className="mt-4 w-full py-3 rounded-lg border border-gray-300 text-gray-600 font-semibold text-sm hover:bg-gray-50 transition-colors touch-target"
        >
          Pindai Lagi
        </button>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-semibold text-gray-900">{value}</span>
    </div>
  );
}
