/**
 * KilnEquipmentDialog — Layer 1 of the firing model redesign.
 *
 * Shows the full history of equipment configurations (thermocouple,
 * controller, cable, typology) for a kiln, and lets the PM install a
 * new configuration when equipment is physically swapped.
 *
 * Installing a new config closes the current one (effective_to=now)
 * and creates a fresh row with effective_from=now. Historical rows
 * remain so that any future firing-profile / set-point references
 * them remain meaningful.
 */
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import apiClient from '@/api/client';
import type { KilnItem } from '@/hooks/useKilns';

interface EquipmentConfig {
  id: string;
  kiln_id: string;
  typology: string | null;
  thermocouple_brand: string | null;
  thermocouple_model: string | null;
  thermocouple_length_cm: number | null;
  thermocouple_position: string | null;
  controller_brand: string | null;
  controller_model: string | null;
  cable_brand: string | null;
  cable_length_cm: number | null;
  cable_type: string | null;
  notes: string | null;
  reason: string | null;
  effective_from: string;
  effective_to: string | null;
  is_current: boolean;
  installed_by_name: string | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  kiln: KilnItem | null;
}

const TYPOLOGY_OPTIONS = [
  { value: '', label: '— select —' },
  { value: 'horizontal', label: 'Horizontal' },
  { value: 'vertical', label: 'Vertical' },
  { value: 'raku', label: 'Raku' },
];

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function blank() {
  return {
    typology: '',
    thermocouple_brand: '',
    thermocouple_model: '',
    thermocouple_length_cm: '' as number | '',
    thermocouple_position: '',
    controller_brand: '',
    controller_model: '',
    cable_brand: '',
    cable_length_cm: '' as number | '',
    cable_type: '',
    notes: '',
    reason: '',
  };
}

export function KilnEquipmentDialog({ open, onClose, kiln }: Props) {
  const qc = useQueryClient();
  const kilnId = kiln?.id;

  const { data: history, isLoading } = useQuery<EquipmentConfig[]>({
    queryKey: ['kiln-equipment-history', kilnId],
    queryFn: () => apiClient.get(`/kilns/${kilnId}/equipment`).then((r) => r.data),
    enabled: !!kilnId && open,
  });

  const [form, setForm] = useState(blank());
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);

  // Pre-fill form with current config as a starting point
  useEffect(() => {
    if (!open || !history) return;
    const current = history.find((c) => c.is_current);
    if (current) {
      setForm({
        typology: current.typology || '',
        thermocouple_brand: current.thermocouple_brand || '',
        thermocouple_model: current.thermocouple_model || '',
        thermocouple_length_cm: current.thermocouple_length_cm ?? '',
        thermocouple_position: current.thermocouple_position || '',
        controller_brand: current.controller_brand || '',
        controller_model: current.controller_model || '',
        cable_brand: current.cable_brand || '',
        cable_length_cm: current.cable_length_cm ?? '',
        cable_type: current.cable_type || '',
        notes: '',
        reason: '',
      });
    } else {
      setForm(blank());
    }
  }, [open, history]);

  const installMut = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiClient.post(`/kilns/${kilnId}/equipment`, payload).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kiln-equipment-history', kilnId] });
      qc.invalidateQueries({ queryKey: ['kilns'] });
      setShowForm(false);
      setError('');
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || (e instanceof Error ? e.message : 'Failed to install equipment config');
      setError(msg);
    },
  });

  const deleteMut = useMutation({
    mutationFn: (configId: string) =>
      apiClient.delete(`/kilns/${kilnId}/equipment/${configId}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kiln-equipment-history', kilnId] });
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || 'Delete failed';
      setError(msg);
    },
  });

  const handleInstall = () => {
    if (!form.reason.trim()) {
      setError('Reason is required when installing new equipment (audit trail).');
      return;
    }
    const payload: Record<string, unknown> = {
      typology: form.typology || null,
      thermocouple_brand: form.thermocouple_brand || null,
      thermocouple_model: form.thermocouple_model || null,
      thermocouple_length_cm: form.thermocouple_length_cm === '' ? null : Number(form.thermocouple_length_cm),
      thermocouple_position: form.thermocouple_position || null,
      controller_brand: form.controller_brand || null,
      controller_model: form.controller_model || null,
      cable_brand: form.cable_brand || null,
      cable_length_cm: form.cable_length_cm === '' ? null : Number(form.cable_length_cm),
      cable_type: form.cable_type || null,
      notes: form.notes || null,
      reason: form.reason,
    };
    installMut.mutate(payload);
  };

  if (!kiln) return null;

  return (
    <Dialog open={open} onClose={onClose} title={`${kiln.name} — Equipment`} className="w-[min(1100px,95vw)]">
      <div className="space-y-6">
        {/* Current config */}
        {isLoading ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : (
          <>
            <div>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-900">Equipment History</h3>
                {!showForm && (
                  <Button size="sm" onClick={() => setShowForm(true)}>
                    + Install New Config
                  </Button>
                )}
              </div>

              {(!history || history.length === 0) ? (
                <div className="rounded border-2 border-dashed border-gray-300 p-6 text-center text-sm text-gray-400">
                  No equipment configurations recorded yet.
                </div>
              ) : (
                <div className="overflow-x-auto rounded border border-gray-200">
                  <table className="min-w-full divide-y divide-gray-200 text-xs">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-2 py-1.5 text-left font-medium text-gray-600">Period</th>
                        <th className="px-2 py-1.5 text-left font-medium text-gray-600">Typology</th>
                        <th className="px-2 py-1.5 text-left font-medium text-gray-600">Thermocouple</th>
                        <th className="px-2 py-1.5 text-left font-medium text-gray-600">Controller</th>
                        <th className="px-2 py-1.5 text-left font-medium text-gray-600">Cable</th>
                        <th className="px-2 py-1.5 text-left font-medium text-gray-600">Reason</th>
                        <th className="px-2 py-1.5 text-left font-medium text-gray-600">By</th>
                        <th className="px-2 py-1.5"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {history.map((cfg) => (
                        <tr key={cfg.id} className={cfg.is_current ? 'bg-green-50' : ''}>
                          <td className="px-2 py-1.5 whitespace-nowrap">
                            <div>{fmtDate(cfg.effective_from)}</div>
                            <div className="text-gray-400">
                              {cfg.is_current ? (
                                <span className="font-medium text-green-700">current</span>
                              ) : (
                                <>→ {fmtDate(cfg.effective_to)}</>
                              )}
                            </div>
                          </td>
                          <td className="px-2 py-1.5">{cfg.typology || '—'}</td>
                          <td className="px-2 py-1.5">
                            {[cfg.thermocouple_brand, cfg.thermocouple_model].filter(Boolean).join(' / ') || '—'}
                            {cfg.thermocouple_length_cm && (
                              <span className="ml-1 text-gray-400">({cfg.thermocouple_length_cm}cm)</span>
                            )}
                            {cfg.thermocouple_position && (
                              <div className="text-gray-400">{cfg.thermocouple_position}</div>
                            )}
                          </td>
                          <td className="px-2 py-1.5">
                            {[cfg.controller_brand, cfg.controller_model].filter(Boolean).join(' / ') || '—'}
                          </td>
                          <td className="px-2 py-1.5">
                            {[cfg.cable_brand, cfg.cable_type].filter(Boolean).join(' / ') || '—'}
                            {cfg.cable_length_cm && (
                              <span className="ml-1 text-gray-400">({cfg.cable_length_cm}cm)</span>
                            )}
                          </td>
                          <td className="px-2 py-1.5 text-gray-600">{cfg.reason || '—'}</td>
                          <td className="px-2 py-1.5 text-gray-500">{cfg.installed_by_name || '—'}</td>
                          <td className="px-2 py-1.5">
                            {history.length > 1 && (
                              <button
                                className="text-red-600 hover:underline"
                                onClick={() => {
                                  if (confirm('Delete this config? History should normally be kept.')) {
                                    deleteMut.mutate(cfg.id);
                                  }
                                }}
                              >
                                del
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Install form */}
            {showForm && (
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                <h3 className="mb-3 text-sm font-semibold text-gray-900">Install New Equipment Config</h3>
                <p className="mb-3 text-xs text-gray-600">
                  Use this when equipment is physically swapped on the kiln (e.g. thermocouple
                  burned out, controller replaced). The current config will be closed with
                  today&apos;s date, and downstream firing profiles will be flagged for
                  requalification.
                </p>

                <div className="grid grid-cols-2 gap-3">
                  <Select
                    label="Typology"
                    options={TYPOLOGY_OPTIONS}
                    value={form.typology}
                    onChange={(e) => setForm({ ...form, typology: e.target.value })}
                  />
                  <div />

                  <Input
                    label="Thermocouple brand"
                    value={form.thermocouple_brand}
                    onChange={(e) => setForm({ ...form, thermocouple_brand: e.target.value })}
                  />
                  <Input
                    label="Thermocouple model"
                    value={form.thermocouple_model}
                    onChange={(e) => setForm({ ...form, thermocouple_model: e.target.value })}
                  />
                  <Input
                    label="Thermocouple length (cm)"
                    type="number"
                    value={form.thermocouple_length_cm}
                    onChange={(e) => setForm({ ...form, thermocouple_length_cm: e.target.value === '' ? '' : Number(e.target.value) })}
                  />
                  <Input
                    label="Thermocouple position"
                    placeholder="e.g. top-center, side-rear"
                    value={form.thermocouple_position}
                    onChange={(e) => setForm({ ...form, thermocouple_position: e.target.value })}
                  />

                  <Input
                    label="Controller brand"
                    value={form.controller_brand}
                    onChange={(e) => setForm({ ...form, controller_brand: e.target.value })}
                  />
                  <Input
                    label="Controller model"
                    value={form.controller_model}
                    onChange={(e) => setForm({ ...form, controller_model: e.target.value })}
                  />

                  <Input
                    label="Cable brand"
                    value={form.cable_brand}
                    onChange={(e) => setForm({ ...form, cable_brand: e.target.value })}
                  />
                  <Input
                    label="Cable type"
                    value={form.cable_type}
                    onChange={(e) => setForm({ ...form, cable_type: e.target.value })}
                  />
                  <Input
                    label="Cable length (cm)"
                    type="number"
                    value={form.cable_length_cm}
                    onChange={(e) => setForm({ ...form, cable_length_cm: e.target.value === '' ? '' : Number(e.target.value) })}
                  />
                  <div />

                  <div className="col-span-2">
                    <Input
                      label="Reason *"
                      placeholder="e.g. thermocouple burned out / preventive replacement / initial setup"
                      value={form.reason}
                      onChange={(e) => setForm({ ...form, reason: e.target.value })}
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700">Notes</label>
                    <textarea
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                      rows={2}
                      value={form.notes}
                      onChange={(e) => setForm({ ...form, notes: e.target.value })}
                    />
                  </div>
                </div>

                {error && (
                  <div className="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                    {error}
                  </div>
                )}

                <div className="mt-4 flex gap-2">
                  <Button onClick={handleInstall} disabled={installMut.isPending}>
                    {installMut.isPending ? 'Installing…' : 'Install'}
                  </Button>
                  <Button variant="ghost" onClick={() => { setShowForm(false); setError(''); }}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </>
        )}

        <div className="flex justify-end border-t pt-4">
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </div>
      </div>
    </Dialog>
  );
}
