import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useFactories, type Factory } from '@/hooks/useFactories';
import { useUsers } from '@/hooks/useUsers';
import { useBotStatus, useRefreshBotStatus, useTestChat, useRecentChats } from '@/hooks/useTelegramBot';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { Tabs } from '@/components/ui/Tabs';
import { FactoryDialog } from '@/components/admin/FactoryDialog';
import { AuditLogViewer } from '@/components/admin/AuditLogViewer';
import { ActiveSessionsViewer } from '@/components/admin/ActiveSessionsViewer';
import { StubsToggle } from '@/components/admin/StubsToggle';
import { MaterialDeduplication } from '@/components/admin/MaterialDeduplication';
import { Trash2 } from 'lucide-react';
import apiClient from '@/api/client';

export default function AdminPanelPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: factoriesData, isLoading: factoriesLoading, isError: factoriesError } = useFactories();
  const { data: usersData, isLoading: usersLoading, isError: usersError } = useUsers({ per_page: 1 });
  const { data: botStatus, isLoading: botLoading, isError: botError } = useBotStatus();
  const refreshBot = useRefreshBotStatus();
  const testChat = useTestChat();
  const recentChats = useRecentChats();
  const [showRecentChats, setShowRecentChats] = useState(false);
  const [factoryDialogOpen, setFactoryDialogOpen] = useState(false);
  const [editFactory, setEditFactory] = useState<Factory | null>(null);
  const [securityTab, setSecurityTab] = useState('audit');

  // Owner chat ID management
  const { data: ownerChatData } = useQuery<{ chat_id: string | null; source: string }>({
    queryKey: ['telegram', 'owner-chat'],
    queryFn: () => apiClient.get('/telegram/owner-chat').then((r) => r.data),
  });
  const [ownerChatInput, setOwnerChatInput] = useState('');
  const [ownerChatMsg, setOwnerChatMsg] = useState<{ ok: boolean; text: string } | null>(null);
  useEffect(() => {
    if (ownerChatData?.chat_id) setOwnerChatInput(ownerChatData.chat_id);
  }, [ownerChatData]);

  const saveOwnerChat = useMutation({
    mutationFn: (chatId: string) => apiClient.put('/telegram/owner-chat', { chat_id: chatId }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['telegram'] });
      setOwnerChatMsg({ ok: true, text: 'Saved!' });
    },
    onError: () => setOwnerChatMsg({ ok: false, text: 'Failed to save' }),
  });

  const testOwnerChat = async () => {
    if (!ownerChatInput.trim()) return;
    setOwnerChatMsg(null);
    try {
      const res = await testChat.mutateAsync(ownerChatInput.trim());
      setOwnerChatMsg(res.success
        ? { ok: true, text: `Connected: ${res.chat_title || 'OK'}` }
        : { ok: false, text: res.error || 'Test failed' });
    } catch { setOwnerChatMsg({ ok: false, text: 'Test failed' }); }
  };

  const factories = factoriesData?.items || [];
  const totalUsers = usersData?.total ?? 0;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const factoryColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = useMemo(
    () => [
      { key: 'name', header: 'Name' },
      {
        key: 'location',
        header: 'Location',
        render: (f: Factory) => (
          <span className="text-sm">{f.location || <span className="text-gray-400">&mdash;</span>}</span>
        ),
      },
      {
        key: 'timezone',
        header: 'Timezone',
        render: (f: Factory) => (
          <span className="text-sm">{f.timezone || <span className="text-gray-400">&mdash;</span>}</span>
        ),
      },
      {
        key: 'telegram',
        header: 'Telegram',
        render: (f: Factory) => {
          const hasMasters = f.masters_group_chat_id != null;
          const hasPurchaser = f.purchaser_chat_id != null;
          if (!hasMasters && !hasPurchaser) {
            return <span className="text-xs text-gray-400">Not configured</span>;
          }
          return (
            <div className="flex gap-1">
              {hasMasters && (
                <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                  Masters
                </span>
              )}
              {hasPurchaser && (
                <span className="inline-flex items-center rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                  Purchaser
                </span>
              )}
            </div>
          );
        },
      },
      {
        key: 'is_active',
        header: 'Status',
        render: (f: Factory) => (
          <Badge
            status={f.is_active ? 'active' : 'inactive'}
            label={f.is_active ? 'Active' : 'Inactive'}
          />
        ),
      },
      {
        key: 'actions',
        header: '',
        render: (f: Factory) => (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setEditFactory(f);
              setFactoryDialogOpen(true);
            }}
          >
            Edit
          </Button>
        ),
      },
    ],
    [],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
        <p className="mt-1 text-sm text-gray-500">System configuration and reference data</p>
      </div>

      {/* API Error Banner */}
      {(factoriesError || usersError) && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">
            ⚠ Error loading data from API. {factoriesError ? 'Factories API error. ' : ''}{usersError ? 'Users API error.' : ''}
          </p>
          <p className="mt-1 text-xs text-red-600">Try refreshing the page. If the problem persists, check the backend logs.</p>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <div className="text-sm text-gray-500">Users</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {usersLoading ? <Spinner className="h-5 w-5" /> : usersError ? <span className="text-red-400">ERR</span> : totalUsers}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Factories</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {factoriesLoading ? <Spinner className="h-5 w-5" /> : factoriesError ? <span className="text-red-400">ERR</span> : factories.length}
          </div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Active Factories</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {factoriesLoading ? (
              <Spinner className="h-5 w-5" />
            ) : (
              factories.filter((f) => f.is_active).length
            )}
          </div>
        </Card>
      </div>

      {/* Telegram Bot Status */}
      <Card>
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-sm font-semibold text-gray-700">Telegram Bot</h3>
            {botLoading ? (
              <div className="mt-2">
                <Spinner className="h-5 w-5" />
              </div>
            ) : botError ? (
              <div className="mt-2 flex items-center gap-2">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-400" />
                <span className="text-sm text-gray-500">Unable to check bot status</span>
              </div>
            ) : botStatus?.connected ? (
              <div className="mt-2 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
                  <span className="text-sm font-medium text-gray-900">
                    Connected — {botStatus.bot_username}
                  </span>
                </div>
                {botStatus.bot_name && (
                  <p className="text-xs text-gray-500">{botStatus.bot_name}</p>
                )}
                {/* Owner Chat ID — editable */}
                <div className="mt-2 flex items-center gap-2">
                  <label className="text-xs text-gray-500 whitespace-nowrap">Owner chat:</label>
                  <input
                    type="text"
                    value={ownerChatInput}
                    onChange={(e) => { setOwnerChatInput(e.target.value); setOwnerChatMsg(null); }}
                    placeholder="-1001234567890"
                    className="w-44 rounded border border-gray-300 px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
                  />
                  <Button
                    type="button" variant="secondary" size="sm"
                    disabled={!ownerChatInput.trim() || testChat.isPending}
                    onClick={testOwnerChat}
                  >Test</Button>
                  <Button
                    type="button" size="sm"
                    disabled={!ownerChatInput.trim() || saveOwnerChat.isPending}
                    onClick={() => saveOwnerChat.mutate(ownerChatInput.trim())}
                  >Save</Button>
                </div>
                {ownerChatMsg && (
                  <p className={`mt-1 text-xs ${ownerChatMsg.ok ? 'text-green-600' : 'text-red-500'}`}>{ownerChatMsg.text}</p>
                )}
              </div>
            ) : (
              <div className="mt-2 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500" />
                  <span className="text-sm font-medium text-gray-900">Not connected</span>
                </div>
                <p className="text-xs text-gray-500">
                  {botStatus?.error || botStatus?.message || 'Set TELEGRAM_BOT_TOKEN environment variable to enable Telegram notifications.'}
                </p>
              </div>
            )}
          </div>
          <span className="rounded-md bg-gray-100 p-1.5 text-gray-400">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-4H7l5-7v4h4l-5 7z" />
            </svg>
          </span>
        </div>
        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-gray-400">
            Bot token is managed via environment variables. Contact DevOps to change.
          </p>
          <div className="flex gap-2">
            <Button
              type="button" variant="ghost" size="sm"
              disabled={refreshBot.isPending}
              onClick={() => refreshBot.mutate()}
              className="text-xs"
            >
              {refreshBot.isPending ? <Spinner className="h-3 w-3" /> : '↻ Refresh'}
            </Button>
            <Button
              type="button" variant="ghost" size="sm"
              disabled={recentChats.isPending}
              onClick={() => { recentChats.mutate(); setShowRecentChats(true); }}
              className="text-xs"
            >
              {recentChats.isPending ? <Spinner className="h-3 w-3" /> : '🔍 Discover Chat IDs'}
            </Button>
          </div>
        </div>
        {/* Recent chats discovery panel */}
        {showRecentChats && (
          <div className="mt-3 rounded-md border border-blue-100 bg-blue-50 p-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold text-blue-800">Recent Chats (from bot updates)</h4>
              <button onClick={() => setShowRecentChats(false)} className="text-xs text-blue-500 hover:text-blue-700">✕</button>
            </div>
            {recentChats.isPending ? (
              <Spinner className="h-4 w-4" />
            ) : recentChats.data?.error ? (
              <p className="text-xs text-red-500">{recentChats.data.error}</p>
            ) : recentChats.data?.chats && recentChats.data.chats.length > 0 ? (
              <div className="space-y-1">
                {recentChats.data.chats.map((c) => (
                  <div key={c.chat_id} className="flex items-center gap-3 rounded bg-white px-2 py-1 text-xs">
                    <code className="font-mono font-bold text-blue-700">{c.chat_id}</code>
                    <span className="text-gray-700">{c.title}</span>
                    <span className="rounded bg-gray-100 px-1 text-[10px] text-gray-500">{c.type}</span>
                  </div>
                ))}
                <p className="mt-1 text-[10px] text-blue-600">Copy the chat ID and paste it into the factory's Telegram settings.</p>
              </div>
            ) : (
              <p className="text-xs text-blue-700">
                No recent messages found. Write something in the group where the bot is added, then click "Discover" again.
              </p>
            )}
          </div>
        )}
      </Card>

      {/* Factories Section */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Factories</h2>
          <Button
            size="sm"
            onClick={() => {
              setEditFactory(null);
              setFactoryDialogOpen(true);
            }}
          >
            + Add Factory
          </Button>
        </div>
        {factoriesLoading ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-8 w-8" />
          </div>
        ) : factories.length === 0 ? (
          <div className="py-8 text-center text-gray-400">No factories configured</div>
        ) : (
          <DataTable
            columns={factoryColumns}
            data={factories as unknown as Record<string, unknown>[]}
          />
        )}
      </div>

      {/* Security Section */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Security</h2>
        <Tabs
          tabs={[
            { id: 'audit', label: 'Audit Log' },
            { id: 'sessions', label: 'Active Sessions' },
          ]}
          activeTab={securityTab}
          onChange={setSecurityTab}
        />
        <div className="mt-4">
          {securityTab === 'audit' ? <AuditLogViewer /> : <ActiveSessionsViewer />}
        </div>
      </div>

      {/* Integration Stubs */}
      <StubsToggle />

      {/* Quick Links */}
      <Card title="Quick Links">
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => navigate('/users')}>
            Manage Users &rarr;
          </Button>
          <Button variant="secondary" onClick={() => navigate('/tablo')}>
            Production Tablo &rarr;
          </Button>
        </div>
      </Card>

      {/* Reference Data */}
      <Card title="Reference Data">
        <p className="mb-3 text-sm text-gray-500">Manage product reference data and catalogs</p>
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => navigate('/admin/recipes')}>
            Recipes &rarr;
          </Button>
          <Button variant="secondary" onClick={() => navigate('/admin/suppliers')}>
            Suppliers &rarr;
          </Button>
          <Button variant="secondary" onClick={() => navigate('/admin/collections')}>
            Collections &rarr;
          </Button>
          <Button variant="secondary" onClick={() => navigate('/admin/colors')}>
            Colors &rarr;
          </Button>
          <Button variant="secondary" onClick={() => navigate('/admin/application-types')}>
            Application Types &rarr;
          </Button>
          <Button variant="secondary" onClick={() => navigate('/admin/places-of-application')}>
            Places of Application &rarr;
          </Button>
          <Button variant="secondary" onClick={() => navigate('/admin/finishing-types')}>
            Finishing Types &rarr;
          </Button>
          <Button variant="secondary" onClick={() => navigate('/admin/temperature-groups')}>
            Temperature Groups &rarr;
          </Button>
        </div>
      </Card>

      {/* Material Deduplication */}
      <MaterialDeduplication />

      {/* PM Cleanup Permissions */}
      <AdminCleanupCard factories={factories} />

      {/* Factory Dialog */}
      <FactoryDialog
        open={factoryDialogOpen}
        onClose={() => {
          setFactoryDialogOpen(false);
          setEditFactory(null);
        }}
        factory={editFactory}
      />
    </div>
  );
}

function AdminCleanupCard({ factories }: { factories: Factory[] }) {
  const [selectedFactory, setSelectedFactory] = useState<string>('');
  const [canDeleteTasks, setCanDeleteTasks] = useState(false);
  const [canDeletePositions, setCanDeletePositions] = useState(false);
  const [saving, setSaving] = useState(false);

  const factoryId = selectedFactory || (factories[0]?.id ?? '');

  useEffect(() => {
    if (!factoryId) return;
    apiClient.get('/cleanup/permissions', { params: { factory_id: factoryId } })
      .then((r) => {
        setCanDeleteTasks(r.data.pm_can_delete_tasks);
        setCanDeletePositions(r.data.pm_can_delete_positions);
      })
      .catch(() => {});
  }, [factoryId]);

  const toggle = async (field: 'pm_can_delete_tasks' | 'pm_can_delete_positions', value: boolean) => {
    if (!factoryId) return;
    setSaving(true);
    try {
      const r = await apiClient.patch('/cleanup/permissions', {
        factory_id: factoryId,
        [field]: value,
      });
      setCanDeleteTasks(r.data.pm_can_delete_tasks);
      setCanDeletePositions(r.data.pm_can_delete_positions);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <div className="flex items-center gap-2 mb-3">
        <Trash2 className="h-4 w-4 text-red-500" />
        <span className="text-sm font-semibold text-gray-700">PM Cleanup Permissions</span>
        <span className="ml-auto text-xs text-amber-600 font-medium">⚠ Temporary</span>
      </div>
      {factories.length > 1 && (
        <select
          value={selectedFactory}
          onChange={(e) => setSelectedFactory(e.target.value)}
          className="mb-3 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          {factories.map((f) => (
            <option key={f.id} value={f.id}>{f.name}</option>
          ))}
        </select>
      )}
      <div className="space-y-2">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={canDeleteTasks}
            disabled={saving || !factoryId}
            onChange={(e) => toggle('pm_can_delete_tasks', e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
          />
          <span className="text-sm text-gray-700">PM can delete tasks</span>
        </label>
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={canDeletePositions}
            disabled={saving || !factoryId}
            onChange={(e) => toggle('pm_can_delete_positions', e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
          />
          <span className="text-sm text-gray-700">PM can delete positions</span>
        </label>
      </div>
    </Card>
  );
}
