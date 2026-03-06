import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useOrder } from '@/hooks/useOrders';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Tabs } from '@/components/ui/Tabs';
import { Spinner } from '@/components/ui/Spinner';
import { DataTable } from '@/components/ui/Table';

export default function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const { data: order, isLoading } = useOrder(orderId);
  const [tab, setTab] = useState('positions');

  if (isLoading) {
    return <div className="flex justify-center py-20"><Spinner className="h-10 w-10" /></div>;
  }

  if (!order) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => navigate('/manager')}>&larr; Back</Button>
        <div className="py-12 text-center text-gray-400">Order not found</div>
      </div>
    );
  }

  const positions = order.positions || [];
  const items = order.items || [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const positionColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    { key: 'color', header: 'Color' },
    { key: 'size', header: 'Size' },
    { key: 'quantity', header: 'Qty' },
    {
      key: 'status',
      header: 'Status',
      render: (p) => <Badge status={p.status} />,
    },
    { key: 'product_type', header: 'Type' },
    {
      key: 'batch_id',
      header: 'Batch',
      render: (p) => p.batch_id ? <span className="text-xs text-gray-500">{p.batch_id.slice(0, 8)}...</span> : '\u2014',
    },
    {
      key: 'delay_hours',
      header: 'Delay',
      render: (p) => p.delay_hours ? <span className="text-orange-600">{p.delay_hours}h</span> : '\u2014',
    },
  ];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const itemColumns: { key: string; header: string; render?: (item: any) => React.ReactNode }[] = [
    { key: 'color', header: 'Color' },
    { key: 'size', header: 'Size' },
    { key: 'quantity_pcs', header: 'Qty (pcs)' },
    { key: 'application', header: 'Application' },
    { key: 'finishing', header: 'Finishing' },
    { key: 'product_type', header: 'Type' },
    {
      key: 'thickness_mm',
      header: 'Thickness',
      render: (item) => item.thickness_mm ? `${item.thickness_mm} mm` : '\u2014',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/manager')}>&larr; Back</Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">Order {order.order_number}</h1>
            <Badge status={order.status} />
          </div>
        </div>
      </div>

      {/* Order Info */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <div className="text-xs text-gray-500">Client</div>
          <div className="mt-1 font-medium text-gray-900">{order.client || '\u2014'}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Deadline</div>
          <div className="mt-1 font-medium text-gray-900">
            {order.final_deadline ? new Date(order.final_deadline).toLocaleDateString() : '\u2014'}
          </div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Factory</div>
          <div className="mt-1 font-medium text-gray-900">{order.factory_id || '\u2014'}</div>
        </Card>
        <Card>
          <div className="text-xs text-gray-500">Positions</div>
          <div className="mt-1 font-medium text-gray-900">
            <span className="text-green-600">{order.positions_ready || 0}</span>
            <span className="text-gray-400"> / </span>
            <span>{order.positions_count || 0}</span>
            <span className="ml-1 text-xs text-gray-400">ready</span>
          </div>
        </Card>
      </div>

      {order.notes && (
        <Card>
          <div className="text-xs text-gray-500">Notes</div>
          <div className="mt-1 text-sm text-gray-700">{order.notes}</div>
        </Card>
      )}

      {/* Tabs */}
      <Tabs
        tabs={[
          { id: 'positions', label: `Positions (${positions.length})` },
          { id: 'items', label: `Items (${items.length})` },
        ]}
        activeTab={tab}
        onChange={setTab}
      />

      {/* Content */}
      {tab === 'positions' && (
        positions.length > 0 ? (
          <DataTable columns={positionColumns} data={positions} />
        ) : (
          <div className="py-8 text-center text-gray-400">No positions yet</div>
        )
      )}

      {tab === 'items' && (
        items.length > 0 ? (
          <DataTable columns={itemColumns} data={items} />
        ) : (
          <div className="py-8 text-center text-gray-400">No items</div>
        )
      )}
    </div>
  );
}
