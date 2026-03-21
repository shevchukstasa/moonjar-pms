import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { factoriesApi } from '@/api/factories';
import {
  adminSettingsApi,
  type EscalationRule,
  type EscalationRuleInput,
  type DefectThreshold,
  type ServiceLeadTimeDetail,
} from '@/api/adminSettings';

const TABS = [
  { id: 'escalation', label: 'Escalation Rules' },
  { id: 'receiving', label: 'Receiving' },
  { id: 'defects', label: 'Defect Thresholds' },
  { id: 'consolidation', label: 'Purchase Consolidation' },
  { id: 'lead-times', label: 'Service Lead Times' },
];

export default function AdminSettingsPage() {
  const [activeTab, setActiveTab] = useState('escalation');
  const [selectedFactory, setSelectedFactory] = useState('');

  const { data: factories = [], isLoading: loadingFactories } = useQuery({
    queryKey: ['factories'],
    queryFn: () => factoriesApi.list(),
  });

  useEffect(() => {
    if (factories.length > 0 && !selectedFactory) {
      setSelectedFactory(factories[0].id);
    }
  }, [factories, selectedFactory]);

  if (loadingFactories) {
    return <div className="flex items-center justify-center p-12"><Spinner className="h-8 w-8" /></div>;
  }

  const factoryOptions = factories.map((f: { id: string; name: string }) => ({
    value: f.id,
    label: f.name,
  }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Admin Settings</h1>
        <div className="w-64">
          <Select
            label="Factory"
            options={factoryOptions}
            value={selectedFactory}
            onChange={(e) => setSelectedFactory(e.target.value)}
          />
        </div>
      </div>

      <Tabs tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

      {!selectedFactory ? (
        <Card><p className="text-sm text-gray-500">Select a factory to view settings.</p></Card>
      ) : (
        <>
          {activeTab === 'escalation' && <EscalationRulesTab factoryId={selectedFactory} />}
          {activeTab === 'receiving' && <ReceivingTab factoryId={selectedFactory} />}
          {activeTab === 'defects' && <DefectThresholdsTab />}
          {activeTab === 'consolidation' && <ConsolidationTab factoryId={selectedFactory} />}
          {activeTab === 'lead-times' && <ServiceLeadTimesTab factoryId={selectedFactory} />}
        </>
      )}
    </div>
  );
}


// ==================== Tab 1: Escalation Rules ====================

function EscalationRulesTab({ factoryId }: { factoryId: string }) {
  const qc = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<Partial<EscalationRuleInput>>({});
  const [showAdd, setShowAdd] = useState(false);
  const [newRule, setNewRule] = useState<EscalationRuleInput>({
    factory_id: factoryId,
    task_type: '',
    pm_timeout_hours: 4,
    ceo_timeout_hours: 8,
    owner_timeout_hours: 24,
    night_level: 1,
    is_active: true,
  });
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  useEffect(() => {
    setNewRule((prev) => ({ ...prev, factory_id: factoryId }));
  }, [factoryId]);

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ['escalation-rules', factoryId],
    queryFn: () => adminSettingsApi.listEscalationRules(factoryId),
    enabled: !!factoryId,
  });

  const createMut = useMutation({
    mutationFn: (data: EscalationRuleInput) => adminSettingsApi.createEscalationRule(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['escalation-rules', factoryId] }); setShowAdd(false); },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<EscalationRuleInput> }) => adminSettingsApi.updateEscalationRule(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['escalation-rules', factoryId] }); setEditingId(null); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => adminSettingsApi.deleteEscalationRule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['escalation-rules', factoryId] }),
  });

  if (isLoading) return <Card><Spinner /></Card>;

  function startEdit(rule: EscalationRule) {
    setEditingId(rule.id);
    setEditData({
      pm_timeout_hours: rule.pm_timeout_hours,
      ceo_timeout_hours: rule.ceo_timeout_hours,
      owner_timeout_hours: rule.owner_timeout_hours,
      night_level: rule.night_level,
      is_active: rule.is_active,
    });
  }

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Escalation Rules</h3>
        <Button size="sm" onClick={() => setShowAdd(true)}>Add Rule</Button>
      </div>

      {showAdd && (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 space-y-2">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            <Input label="Task Type" value={newRule.task_type} onChange={(e) => setNewRule({ ...newRule, task_type: e.target.value })} />
            <Input label="PM Timeout (h)" type="number" value={newRule.pm_timeout_hours} onChange={(e) => setNewRule({ ...newRule, pm_timeout_hours: Number(e.target.value) })} />
            <Input label="CEO Timeout (h)" type="number" value={newRule.ceo_timeout_hours} onChange={(e) => setNewRule({ ...newRule, ceo_timeout_hours: Number(e.target.value) })} />
            <Input label="Owner Timeout (h)" type="number" value={newRule.owner_timeout_hours} onChange={(e) => setNewRule({ ...newRule, owner_timeout_hours: Number(e.target.value) })} />
            <Input label="Night Level" type="number" min={1} max={3} value={newRule.night_level} onChange={(e) => setNewRule({ ...newRule, night_level: Number(e.target.value) })} />
            <div className="flex items-end gap-2">
              <Button size="sm" onClick={() => createMut.mutate(newRule)} disabled={!newRule.task_type || createMut.isPending}>
                {createMut.isPending ? 'Saving...' : 'Save'}
              </Button>
              <Button size="sm" variant="secondary" onClick={() => setShowAdd(false)}>Cancel</Button>
            </div>
          </div>
          {createMut.isError && <p className="text-xs text-red-500">{(createMut.error as Error).message}</p>}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs font-medium uppercase text-gray-500">
              <th className="px-2 py-2">Task Type</th>
              <th className="px-2 py-2">PM (h)</th>
              <th className="px-2 py-2">CEO (h)</th>
              <th className="px-2 py-2">Owner (h)</th>
              <th className="px-2 py-2">Night</th>
              <th className="px-2 py-2">Active</th>
              <th className="px-2 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule: EscalationRule) => (
              <tr key={rule.id} className="border-b hover:bg-gray-50">
                <td className="px-2 py-2 font-medium">{rule.task_type}</td>
                {editingId === rule.id ? (
                  <>
                    <td className="px-2 py-2"><input type="number" className="w-16 rounded border px-1 py-0.5 text-sm" value={editData.pm_timeout_hours ?? ''} onChange={(e) => setEditData({ ...editData, pm_timeout_hours: Number(e.target.value) })} /></td>
                    <td className="px-2 py-2"><input type="number" className="w-16 rounded border px-1 py-0.5 text-sm" value={editData.ceo_timeout_hours ?? ''} onChange={(e) => setEditData({ ...editData, ceo_timeout_hours: Number(e.target.value) })} /></td>
                    <td className="px-2 py-2"><input type="number" className="w-16 rounded border px-1 py-0.5 text-sm" value={editData.owner_timeout_hours ?? ''} onChange={(e) => setEditData({ ...editData, owner_timeout_hours: Number(e.target.value) })} /></td>
                    <td className="px-2 py-2"><input type="number" min={1} max={3} className="w-12 rounded border px-1 py-0.5 text-sm" value={editData.night_level ?? ''} onChange={(e) => setEditData({ ...editData, night_level: Number(e.target.value) })} /></td>
                    <td className="px-2 py-2"><input type="checkbox" checked={editData.is_active ?? true} onChange={(e) => setEditData({ ...editData, is_active: e.target.checked })} /></td>
                    <td className="px-2 py-2 space-x-1">
                      <Button size="sm" onClick={() => updateMut.mutate({ id: rule.id, data: editData })} disabled={updateMut.isPending}>Save</Button>
                      <Button size="sm" variant="secondary" onClick={() => setEditingId(null)}>Cancel</Button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-2 py-2">{rule.pm_timeout_hours}</td>
                    <td className="px-2 py-2">{rule.ceo_timeout_hours}</td>
                    <td className="px-2 py-2">{rule.owner_timeout_hours}</td>
                    <td className="px-2 py-2">{rule.night_level}</td>
                    <td className="px-2 py-2">{rule.is_active ? 'Yes' : 'No'}</td>
                    <td className="px-2 py-2 space-x-1">
                      <Button size="sm" variant="ghost" onClick={() => startEdit(rule)}>Edit</Button>
                      <Button size="sm" variant="danger" onClick={() => setDeleteTarget(rule.id)}>Delete</Button>
                    </td>
                  </>
                )}
              </tr>
            ))}
            {rules.length === 0 && (
              <tr><td colSpan={7} className="px-2 py-6 text-center text-gray-400">No escalation rules configured for this factory.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => { if (deleteTarget) deleteMut.mutate(deleteTarget); setDeleteTarget(null); }}
        title="Delete Escalation Rule"
        message="Are you sure you want to delete this escalation rule? This action cannot be undone."
      />
    </Card>
  );
}


// ==================== Tab 2: Receiving Settings ====================

function ReceivingTab({ factoryId }: { factoryId: string }) {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['receiving-settings', factoryId],
    queryFn: () => adminSettingsApi.getReceivingSettings(factoryId),
    enabled: !!factoryId,
  });

  const updateMut = useMutation({
    mutationFn: (mode: string) => adminSettingsApi.updateReceivingSettings(factoryId, { approval_mode: mode }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['receiving-settings', factoryId] }),
  });

  if (isLoading) return <Card><Spinner /></Card>;

  const currentMode = data?.approval_mode ?? 'all';

  return (
    <Card>
      <h3 className="mb-4 text-sm font-semibold text-gray-900">Receiving Approval Mode</h3>
      <p className="mb-4 text-sm text-gray-600">
        Choose how material receiving is approved for this factory.
      </p>
      <div className="space-y-3">
        <label className="flex cursor-pointer items-center gap-3 rounded-lg border p-4 hover:bg-gray-50">
          <input
            type="radio"
            name="approval_mode"
            value="all"
            checked={currentMode === 'all'}
            onChange={() => updateMut.mutate('all')}
            className="h-4 w-4 text-primary-500"
          />
          <div>
            <div className="font-medium text-gray-900">Manual Approval (all)</div>
            <div className="text-sm text-gray-500">All received materials require manual approval before entering inventory.</div>
          </div>
        </label>
        <label className="flex cursor-pointer items-center gap-3 rounded-lg border p-4 hover:bg-gray-50">
          <input
            type="radio"
            name="approval_mode"
            value="auto"
            checked={currentMode === 'auto'}
            onChange={() => updateMut.mutate('auto')}
            className="h-4 w-4 text-primary-500"
          />
          <div>
            <div className="font-medium text-gray-900">Auto Approval</div>
            <div className="text-sm text-gray-500">Materials are automatically approved upon receiving if they pass quality checks.</div>
          </div>
        </label>
      </div>
      {updateMut.isPending && <p className="mt-2 text-xs text-gray-400">Saving...</p>}
    </Card>
  );
}


// ==================== Tab 3: Defect Thresholds ====================

function DefectThresholdsTab() {
  const qc = useQueryClient();
  const [editingMaterial, setEditingMaterial] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<number>(3);
  const [newMaterialId, setNewMaterialId] = useState('');
  const [newPercent, setNewPercent] = useState<number>(3);
  const [showAdd, setShowAdd] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const { data: thresholds = [], isLoading } = useQuery({
    queryKey: ['defect-thresholds'],
    queryFn: () => adminSettingsApi.listDefectThresholds(),
  });

  const { data: materials = [] } = useQuery({
    queryKey: ['materials-list'],
    queryFn: () => import('@/api/client').then((m) => m.default.get('/materials').then((r) => r.data)),
  });

  const upsertMut = useMutation({
    mutationFn: ({ materialId, percent }: { materialId: string; percent: number }) =>
      adminSettingsApi.upsertDefectThreshold(materialId, { max_defect_percent: percent }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['defect-thresholds'] }); setEditingMaterial(null); setShowAdd(false); },
  });

  const deleteMut = useMutation({
    mutationFn: (materialId: string) => adminSettingsApi.deleteDefectThreshold(materialId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['defect-thresholds'] }),
  });

  if (isLoading) return <Card><Spinner /></Card>;

  const existingMaterialIds = new Set(thresholds.map((t: DefectThreshold) => t.material_id));
  const availableMaterials = (materials as { id: string; name: string }[]).filter(
    (m) => !existingMaterialIds.has(m.id),
  );

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Material Defect Thresholds</h3>
        <Button size="sm" onClick={() => setShowAdd(true)}>Add Threshold</Button>
      </div>

      {showAdd && (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Select
                label="Material"
                options={[{ value: '', label: '-- Select Material --' }, ...availableMaterials.map((m) => ({ value: m.id, label: m.name }))]}
                value={newMaterialId}
                onChange={(e) => setNewMaterialId(e.target.value)}
              />
            </div>
            <div className="w-32">
              <Input label="Max Defect %" type="number" min={0} max={100} step={0.1} value={newPercent} onChange={(e) => setNewPercent(Number(e.target.value))} />
            </div>
            <Button size="sm" onClick={() => { if (newMaterialId) upsertMut.mutate({ materialId: newMaterialId, percent: newPercent }); }} disabled={!newMaterialId || upsertMut.isPending}>
              {upsertMut.isPending ? 'Saving...' : 'Save'}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setShowAdd(false)}>Cancel</Button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs font-medium uppercase text-gray-500">
              <th className="px-2 py-2">Material</th>
              <th className="px-2 py-2">Max Defect %</th>
              <th className="px-2 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {thresholds.map((t: DefectThreshold) => (
              <tr key={t.material_id} className="border-b hover:bg-gray-50">
                <td className="px-2 py-2 font-medium">{t.material_name || t.material_id}</td>
                {editingMaterial === t.material_id ? (
                  <>
                    <td className="px-2 py-2">
                      <input type="number" min={0} max={100} step={0.1} className="w-20 rounded border px-1 py-0.5 text-sm" value={editValue} onChange={(e) => setEditValue(Number(e.target.value))} />
                    </td>
                    <td className="px-2 py-2 space-x-1">
                      <Button size="sm" onClick={() => upsertMut.mutate({ materialId: t.material_id, percent: editValue })} disabled={upsertMut.isPending}>Save</Button>
                      <Button size="sm" variant="secondary" onClick={() => setEditingMaterial(null)}>Cancel</Button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-2 py-2">{t.max_defect_percent}%</td>
                    <td className="px-2 py-2 space-x-1">
                      <Button size="sm" variant="ghost" onClick={() => { setEditingMaterial(t.material_id); setEditValue(t.max_defect_percent); }}>Edit</Button>
                      <Button size="sm" variant="danger" onClick={() => setDeleteTarget(t.material_id)}>Delete</Button>
                    </td>
                  </>
                )}
              </tr>
            ))}
            {thresholds.length === 0 && (
              <tr><td colSpan={3} className="px-2 py-6 text-center text-gray-400">No defect thresholds configured.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => { if (deleteTarget) deleteMut.mutate(deleteTarget); setDeleteTarget(null); }}
        title="Delete Defect Threshold"
        message="Are you sure you want to remove this defect threshold?"
      />
    </Card>
  );
}


// ==================== Tab 4: Purchase Consolidation ====================

function ConsolidationTab({ factoryId }: { factoryId: string }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ consolidation_window_days: 7, urgency_threshold_days: 5, planning_horizon_days: 30 });
  const [dirty, setDirty] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['consolidation-settings', factoryId],
    queryFn: () => adminSettingsApi.getConsolidationSettings(factoryId),
    enabled: !!factoryId,
  });

  useEffect(() => {
    if (data) {
      setForm({
        consolidation_window_days: data.consolidation_window_days,
        urgency_threshold_days: data.urgency_threshold_days,
        planning_horizon_days: data.planning_horizon_days,
      });
      setDirty(false);
    }
  }, [data]);

  const updateMut = useMutation({
    mutationFn: () => adminSettingsApi.updateConsolidationSettings(factoryId, form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['consolidation-settings', factoryId] }); setDirty(false); },
  });

  if (isLoading) return <Card><Spinner /></Card>;

  function handleChange(field: string, value: number) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setDirty(true);
  }

  return (
    <Card>
      <h3 className="mb-4 text-sm font-semibold text-gray-900">Purchase Consolidation Settings</h3>
      <p className="mb-4 text-sm text-gray-600">
        Configure how purchase requests are consolidated for this factory.
      </p>
      <div className="grid gap-4 sm:grid-cols-3">
        <Input
          label="Consolidation Window (days)"
          type="number"
          min={1}
          value={form.consolidation_window_days}
          onChange={(e) => handleChange('consolidation_window_days', Number(e.target.value))}
        />
        <Input
          label="Urgency Threshold (days)"
          type="number"
          min={1}
          value={form.urgency_threshold_days}
          onChange={(e) => handleChange('urgency_threshold_days', Number(e.target.value))}
        />
        <Input
          label="Planning Horizon (days)"
          type="number"
          min={1}
          value={form.planning_horizon_days}
          onChange={(e) => handleChange('planning_horizon_days', Number(e.target.value))}
        />
      </div>
      <div className="mt-4">
        <Button onClick={() => updateMut.mutate()} disabled={!dirty || updateMut.isPending}>
          {updateMut.isPending ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>
      {updateMut.isError && <p className="mt-2 text-xs text-red-500">Failed to save settings.</p>}
    </Card>
  );
}


// ==================== Tab 5: Service Lead Times ====================

function ServiceLeadTimesTab({ factoryId }: { factoryId: string }) {
  const qc = useQueryClient();
  const [editValues, setEditValues] = useState<Record<string, number>>({});
  const [dirty, setDirty] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['service-lead-times', factoryId],
    queryFn: () => adminSettingsApi.getServiceLeadTimes(factoryId),
    enabled: !!factoryId,
  });

  useEffect(() => {
    if (data?.lead_times) {
      const vals: Record<string, number> = {};
      data.lead_times.forEach((lt: ServiceLeadTimeDetail) => {
        vals[lt.service_type] = lt.lead_time_days;
      });
      setEditValues(vals);
      setDirty(false);
    }
  }, [data]);

  const updateMut = useMutation({
    mutationFn: () => {
      const items = Object.entries(editValues).map(([service_type, lead_time_days]) => ({ service_type, lead_time_days }));
      return adminSettingsApi.updateServiceLeadTimes(factoryId, items);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['service-lead-times', factoryId] }); setDirty(false); },
  });

  const resetMut = useMutation({
    mutationFn: () => adminSettingsApi.resetServiceLeadTimes(factoryId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['service-lead-times', factoryId] }); setDirty(false); },
  });

  if (isLoading) return <Card><Spinner /></Card>;

  function handleChange(serviceType: string, value: number) {
    setEditValues((prev) => ({ ...prev, [serviceType]: value }));
    setDirty(true);
  }

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Service Lead Times</h3>
        <Button size="sm" variant="secondary" onClick={() => resetMut.mutate()} disabled={resetMut.isPending}>
          {resetMut.isPending ? 'Resetting...' : 'Reset to Defaults'}
        </Button>
      </div>
      <p className="mb-4 text-sm text-gray-600">
        Configure lead times for each service type. These determine how far in advance services must be requested.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs font-medium uppercase text-gray-500">
              <th className="px-2 py-2">Service Type</th>
              <th className="px-2 py-2">Lead Time (days)</th>
              <th className="px-2 py-2">Custom</th>
            </tr>
          </thead>
          <tbody>
            {(data?.lead_times || []).map((lt: ServiceLeadTimeDetail) => (
              <tr key={lt.service_type} className="border-b hover:bg-gray-50">
                <td className="px-2 py-2 font-medium capitalize">{lt.service_type.replace(/_/g, ' ')}</td>
                <td className="px-2 py-2">
                  <input
                    type="number"
                    min={0}
                    className="w-20 rounded border px-2 py-1 text-sm"
                    value={editValues[lt.service_type] ?? lt.lead_time_days}
                    onChange={(e) => handleChange(lt.service_type, Number(e.target.value))}
                  />
                </td>
                <td className="px-2 py-2">
                  {lt.is_custom ? (
                    <span className="inline-block rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">Custom</span>
                  ) : (
                    <span className="text-xs text-gray-400">Default</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4">
        <Button onClick={() => updateMut.mutate()} disabled={!dirty || updateMut.isPending}>
          {updateMut.isPending ? 'Saving...' : 'Save Lead Times'}
        </Button>
      </div>
      {updateMut.isError && <p className="mt-2 text-xs text-red-500">Failed to save lead times.</p>}
    </Card>
  );
}
