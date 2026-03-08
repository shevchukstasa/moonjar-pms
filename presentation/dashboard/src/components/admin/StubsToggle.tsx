import { useState, useEffect } from 'react';
import apiClient from '@/api/client';
import { Card } from '@/components/ui/Card';

interface StubState {
  active: boolean;
  description: string;
}

interface StubsResponse {
  stubs: Record<string, StubState>;
}

export function StubsToggle() {
  const [stubs, setStubs] = useState<Record<string, StubState>>({});
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStubs = async () => {
    try {
      const res = await apiClient.get<StubsResponse>('/integration/stubs');
      setStubs(res.data.stubs);
      setError(null);
    } catch (e) {
      setError('Failed to load stubs state');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStubs();
  }, []);

  const toggleStub = async (key: string, currentActive: boolean) => {
    setUpdating(key);
    try {
      await apiClient.post('/integration/stubs', { [key]: !currentActive });
      setStubs((prev) => ({
        ...prev,
        [key]: { ...prev[key], active: !currentActive },
      }));
      setError(null);
    } catch (e) {
      setError(`Failed to toggle ${key}`);
    } finally {
      setUpdating(null);
    }
  };

  const labels: Record<string, string> = {
    schedule_estimation: 'Schedule Estimation',
    intermediate_callbacks: 'Sales Status Callbacks',
  };

  if (loading) {
    return (
      <Card>
        <div className="py-4 text-center text-sm text-gray-400">Loading stubs...</div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="mb-3 flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5 text-amber-500">
          <path d="M12 9v4m0 4h.01M5.07 19h13.86a2 2 0 0 0 1.74-2.99L13.74 4a2 2 0 0 0-3.48 0L3.33 16.01A2 2 0 0 0 5.07 19Z" />
        </svg>
        <h3 className="text-sm font-semibold text-gray-700">Integration Stubs</h3>
      </div>
      <p className="mb-4 text-xs text-gray-500">
        Stubs return placeholder data while factories, kilns, and full configuration are being set up.
        Disable stubs when real data and calculations are ready.
      </p>

      {error && (
        <div className="mb-3 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>
      )}

      <div className="divide-y divide-gray-100">
        {Object.entries(stubs).map(([key, stub]) => (
          <div key={key} className="flex items-center justify-between py-3">
            <div>
              <div className="text-sm font-medium text-gray-900">{labels[key] || key}</div>
              <div className="text-xs text-gray-500">{stub.description}</div>
            </div>
            <button
              onClick={() => toggleStub(key, stub.active)}
              disabled={updating === key}
              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                stub.active
                  ? 'bg-amber-500'
                  : 'bg-green-500'
              } ${updating === key ? 'opacity-50' : ''}`}
              title={stub.active ? 'Stub active — click to disable and use real logic' : 'Real logic active — click to enable stub'}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  stub.active ? 'translate-x-0' : 'translate-x-5'
                }`}
              />
            </button>
            <span className={`ml-2 text-xs font-medium ${stub.active ? 'text-amber-600' : 'text-green-600'}`}>
              {stub.active ? 'STUB' : 'LIVE'}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
