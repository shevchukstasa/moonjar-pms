import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { useAuthStore } from '../stores/authStore';

interface MaterialItem {
  id: string;
  name: string;
  balance: number;
  min_balance: number;
  unit: string;
  material_type: string;
  is_low_stock: boolean;
  warehouse_section: string | null;
  supplier_name: string | null;
}

type SortBy = 'name' | 'balance';

export function InventoryPage() {
  const { selectedFactoryId } = useAuthStore();
  const [materials, setMaterials] = useState<MaterialItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortBy>('name');
  const [showLowOnly, setShowLowOnly] = useState(false);

  const fetchMaterials = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get('/materials', {
        params: {
          factory_id: selectedFactoryId,
          per_page: 200,
          low_stock: showLowOnly || undefined,
        },
      });
      setMaterials(res.data.items ?? res.data ?? []);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Gagal memuat data stok.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedFactoryId, showLowOnly]);

  useEffect(() => {
    fetchMaterials();
  }, [fetchMaterials]);

  // Filter + sort
  const filtered = materials
    .filter((m) => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        m.name.toLowerCase().includes(q) ||
        m.material_type.toLowerCase().includes(q) ||
        (m.warehouse_section ?? '').toLowerCase().includes(q)
      );
    })
    .sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      return a.balance - b.balance;
    });

  const lowCount = materials.filter((m) => m.is_low_stock).length;

  return (
    <div className="p-4 max-w-lg mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold text-gray-900">Stok Gudang</h1>
        {lowCount > 0 && (
          <span className="text-xs font-semibold bg-red-100 text-red-700 px-2.5 py-1 rounded-full">
            {lowCount} rendah
          </span>
        )}
      </div>

      {/* Search */}
      <div className="mb-3">
        <input
          type="text"
          inputMode="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Cari material..."
          className="w-full px-4 py-3 rounded-lg border border-gray-300 text-base bg-white outline-none focus:ring-2 focus:ring-primary-400 touch-target"
        />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-4 overflow-x-auto">
        <button
          onClick={() => setShowLowOnly(!showLowOnly)}
          className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors touch-target ${
            showLowOnly
              ? 'bg-red-600 text-white border-red-600'
              : 'bg-white text-gray-600 border-gray-300'
          }`}
        >
          Stok Rendah
        </button>
        <button
          onClick={() => setSortBy(sortBy === 'name' ? 'balance' : 'name')}
          className="flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold border bg-white text-gray-600 border-gray-300 touch-target"
        >
          Urutkan: {sortBy === 'name' ? 'Nama' : 'Saldo'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-4">
          {error}
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

      {/* Empty */}
      {!loading && filtered.length === 0 && (
        <div className="text-center py-12">
          <svg className="mx-auto mb-3 text-gray-300" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
          </svg>
          <p className="text-gray-500 text-sm">
            {search ? 'Tidak ditemukan.' : 'Tidak ada material.'}
          </p>
        </div>
      )}

      {/* Materials list */}
      {!loading && filtered.length > 0 && (
        <div className="space-y-2">
          {filtered.map((m) => (
            <div
              key={m.id}
              className={`bg-white rounded-xl border shadow-sm p-4 ${
                m.is_low_stock ? 'border-red-200' : 'border-gray-100'
              }`}
            >
              <div className="flex items-start justify-between mb-1">
                <h3 className="font-semibold text-gray-900 text-sm leading-tight flex-1 mr-2">
                  {m.name}
                </h3>
                {m.is_low_stock && (
                  <span className="flex-shrink-0 w-2.5 h-2.5 bg-red-500 rounded-full mt-1" title="Stok rendah" />
                )}
              </div>
              <div className="flex items-end justify-between">
                <div className="text-xs text-gray-500 space-y-0.5">
                  <p>{m.material_type}</p>
                  {m.warehouse_section && <p>Lokasi: {m.warehouse_section}</p>}
                </div>
                <div className="text-right">
                  <p
                    className={`text-lg font-bold ${
                      m.is_low_stock ? 'text-red-600' : 'text-gray-900'
                    }`}
                  >
                    {m.balance.toLocaleString('id-ID')}
                  </p>
                  <p className="text-xs text-gray-500">
                    {m.unit}
                    {m.min_balance > 0 && (
                      <span className="ml-1 text-gray-400">
                        / min {m.min_balance.toLocaleString('id-ID')}
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          ))}

          {/* Count */}
          <p className="text-center text-xs text-gray-400 pt-2">
            {filtered.length} material
          </p>

          {/* Refresh */}
          <button
            onClick={fetchMaterials}
            className="w-full py-3 text-sm text-primary-600 font-semibold hover:text-primary-700"
          >
            Muat Ulang
          </button>
        </div>
      )}
    </div>
  );
}
