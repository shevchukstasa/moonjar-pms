import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useOrder } from '@/hooks/useOrders';
import { useShipments, useCreateShipment, useMarkShipped, useCancelShipment } from '@/hooks/useShipments';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

const CARRIERS = [
  { value: '', label: 'Select carrier...' },
  { value: 'JNE', label: 'JNE' },
  { value: 'TIKI', label: 'TIKI' },
  { value: 'J&T', label: 'J&T Express' },
  { value: 'SiCepat', label: 'SiCepat' },
  { value: 'AnterAja', label: 'AnterAja' },
  { value: 'Pickup', label: 'Pickup (Self-collect)' },
  { value: 'Container', label: 'Container Shipping' },
  { value: 'Other', label: 'Other' },
];

const SHIPPING_METHODS = [
  { value: '', label: 'Select method...' },
  { value: 'courier', label: 'Courier' },
  { value: 'pickup', label: 'Pickup' },
  { value: 'container', label: 'Container' },
];

const SHIPMENT_STATUS_COLORS: Record<string, string> = {
  prepared: 'bg-yellow-100 text-yellow-800',
  shipped: 'bg-blue-100 text-blue-800',
  in_transit: 'bg-purple-100 text-purple-800',
  delivered: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
};

function ShipmentStatusBadge({ status }: { status: string }) {
  const cls = SHIPMENT_STATUS_COLORS[status] || 'bg-gray-100 text-gray-800';
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function posLabel(p: any): string {
  if (p.position_label) return p.position_label;
  if (p.position_number != null) {
    return p.split_index != null
      ? `#${p.position_number}.${p.split_index}`
      : `#${p.position_number}`;
  }
  return '#?';
}

interface PositionSelection {
  position_id: string;
  selected: boolean;
  quantity_shipped: number;
  box_number: number | null;
}

export default function ShipmentPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const { data: order, isLoading: orderLoading } = useOrder(orderId);
  const { data: shipmentsData, isLoading: shipmentsLoading } = useShipments(orderId);
  const createShipment = useCreateShipment();
  const markShipped = useMarkShipped();
  const cancelShipment = useCancelShipment();

  // Form state
  const [trackingNumber, setTrackingNumber] = useState('');
  const [carrier, setCarrier] = useState('');
  const [shippingMethod, setShippingMethod] = useState('');
  const [totalBoxes, setTotalBoxes] = useState('');
  const [totalWeight, setTotalWeight] = useState('');
  const [estimatedDelivery, setEstimatedDelivery] = useState('');
  const [notes, setNotes] = useState('');
  const [selections, setSelections] = useState<Record<string, PositionSelection>>({});
  const [showCreateConfirm, setShowCreateConfirm] = useState(false);
  const [showShipConfirm, setShowShipConfirm] = useState<string | null>(null);
  const [showCancelConfirm, setShowCancelConfirm] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState('');

  // Get positions ready for shipment
  const readyPositions = useMemo(() => {
    if (!order?.positions) return [];
    return order.positions.filter(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (p: any) => p.status === 'ready_for_shipment'
    );
  }, [order]);

  // Initialize selections when positions load
  useMemo(() => {
    if (readyPositions.length > 0 && Object.keys(selections).length === 0) {
      const initial: Record<string, PositionSelection> = {};
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      readyPositions.forEach((p: any) => {
        initial[p.id] = {
          position_id: p.id,
          selected: true,
          quantity_shipped: p.quantity || 0,
          box_number: null,
        };
      });
      setSelections(initial);
    }
  }, [readyPositions]); // eslint-disable-line react-hooks/exhaustive-deps

  if (orderLoading || shipmentsLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => navigate(-1)}>&larr; Back</Button>
        <div className="py-12 text-center text-gray-400">Order not found</div>
      </div>
    );
  }

  const shipments = shipmentsData?.items || [];
  const selectedItems = Object.values(selections).filter((s) => s.selected);
  const totalPieces = selectedItems.reduce((sum, s) => sum + s.quantity_shipped, 0);

  const togglePosition = (id: string) => {
    setSelections((prev) => ({
      ...prev,
      [id]: { ...prev[id], selected: !prev[id]?.selected },
    }));
  };

  const updateQuantity = (id: string, qty: number) => {
    setSelections((prev) => ({
      ...prev,
      [id]: { ...prev[id], quantity_shipped: qty },
    }));
  };

  const updateBoxNumber = (id: string, box: number | null) => {
    setSelections((prev) => ({
      ...prev,
      [id]: { ...prev[id], box_number: box },
    }));
  };

  const handleCreate = async () => {
    if (!orderId || selectedItems.length === 0) return;
    try {
      await createShipment.mutateAsync({
        order_id: orderId,
        tracking_number: trackingNumber || undefined,
        carrier: carrier || undefined,
        shipping_method: shippingMethod || undefined,
        total_boxes: totalBoxes ? parseInt(totalBoxes) : undefined,
        total_weight_kg: totalWeight ? parseFloat(totalWeight) : undefined,
        estimated_delivery: estimatedDelivery || undefined,
        notes: notes || undefined,
        items: selectedItems.map((s) => ({
          position_id: s.position_id,
          quantity_shipped: s.quantity_shipped,
          box_number: s.box_number ?? undefined,
        })),
      });
      setSuccessMessage('Shipment created successfully.');
      setShowCreateConfirm(false);
      // Reset form
      setTrackingNumber('');
      setCarrier('');
      setShippingMethod('');
      setTotalBoxes('');
      setTotalWeight('');
      setEstimatedDelivery('');
      setNotes('');
      setSelections({});
    } catch (e) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const msg = (e as any)?.response?.data?.detail || 'Failed to create shipment';
      alert(msg);
      setShowCreateConfirm(false);
    }
  };

  const handleShip = async (shipmentId: string) => {
    try {
      await markShipped.mutateAsync(shipmentId);
      setSuccessMessage('Shipment marked as shipped. Sales has been notified.');
      setShowShipConfirm(null);
    } catch (e) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const msg = (e as any)?.response?.data?.detail || 'Failed to mark as shipped';
      alert(msg);
      setShowShipConfirm(null);
    }
  };

  const handleCancel = async (shipmentId: string) => {
    try {
      await cancelShipment.mutateAsync(shipmentId);
      setSuccessMessage('Shipment cancelled.');
      setShowCancelConfirm(null);
    } catch (e) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const msg = (e as any)?.response?.data?.detail || 'Failed to cancel shipment';
      alert(msg);
      setShowCancelConfirm(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate(`/manager/orders/${orderId}`)}>&larr; Back to Order</Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">
            Shipments &mdash; Order {order.order_number}
          </h1>
          <p className="text-sm text-gray-500">
            {order.client} &middot; <Badge status={order.status} />
          </p>
        </div>
      </div>

      {/* Success message */}
      {successMessage && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800 flex justify-between items-center">
          {successMessage}
          <button onClick={() => setSuccessMessage('')} className="text-green-600 hover:text-green-800">&times;</button>
        </div>
      )}

      {/* Existing shipments */}
      {shipments.length > 0 && (
        <Card>
          <div className="p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Existing Shipments</h2>
            <div className="space-y-3">
              {shipments.map((s) => (
                <div key={s.id} className="rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <ShipmentStatusBadge status={s.status} />
                      <span className="text-sm font-medium">{s.total_pieces} pcs</span>
                      {s.tracking_number && (
                        <span className="text-xs text-gray-500">#{s.tracking_number}</span>
                      )}
                      {s.carrier && (
                        <span className="text-xs text-gray-500">via {s.carrier}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {s.status === 'prepared' && (
                        <>
                          <Button
                            size="sm"
                            className="bg-blue-600 hover:bg-blue-700 text-white"
                            onClick={() => setShowShipConfirm(s.id)}
                            disabled={markShipped.isPending}
                          >
                            Mark Shipped
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => setShowCancelConfirm(s.id)}
                            disabled={cancelShipment.isPending}
                          >
                            Cancel
                          </Button>
                        </>
                      )}
                      {s.shipped_at && (
                        <span className="text-xs text-gray-400">
                          Shipped {new Date(s.shipped_at).toLocaleDateString()}
                        </span>
                      )}
                      {s.delivered_at && (
                        <span className="text-xs text-green-600">
                          Delivered {new Date(s.delivered_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  {/* Shipment items */}
                  <div className="mt-2">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-gray-500 border-b">
                          <th className="pb-1">Position</th>
                          <th className="pb-1">Color</th>
                          <th className="pb-1">Size</th>
                          <th className="pb-1 text-right">Qty Shipped</th>
                          <th className="pb-1 text-right">Box #</th>
                        </tr>
                      </thead>
                      <tbody>
                        {s.items.map((item) => (
                          <tr key={item.id} className="border-b border-gray-100 last:border-0">
                            <td className="py-1">{item.position_label || '—'}</td>
                            <td className="py-1">{item.color || '—'}</td>
                            <td className="py-1">{item.size || '—'}</td>
                            <td className="py-1 text-right">{item.quantity_shipped}</td>
                            <td className="py-1 text-right">{item.box_number ?? '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {s.notes && (
                    <p className="mt-2 text-xs text-gray-500 italic">{s.notes}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* New Shipment form (only if there are positions ready) */}
      {readyPositions.length > 0 && (
        <Card>
          <div className="p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Create New Shipment</h2>

            {/* Position selection */}
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">
                Select positions to ship ({selectedItems.length} selected, {totalPieces} pcs total)
              </h3>
              <div className="rounded-lg border border-gray-200 overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr className="text-left text-xs text-gray-500">
                      <th className="p-2 w-8">
                        <input
                          type="checkbox"
                          checked={selectedItems.length === readyPositions.length}
                          onChange={() => {
                            const allSelected = selectedItems.length === readyPositions.length;
                            setSelections((prev) => {
                              const next = { ...prev };
                              Object.keys(next).forEach((k) => {
                                next[k] = { ...next[k], selected: !allSelected };
                              });
                              return next;
                            });
                          }}
                          className="rounded border-gray-300"
                        />
                      </th>
                      <th className="p-2">Position</th>
                      <th className="p-2">Color</th>
                      <th className="p-2">Size</th>
                      <th className="p-2">Available</th>
                      <th className="p-2">Ship Qty</th>
                      <th className="p-2">Box #</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {readyPositions.map((p: any) => {
                      const sel = selections[p.id];
                      return (
                        <tr key={p.id} className={`border-t border-gray-100 ${sel?.selected ? 'bg-blue-50/50' : ''}`}>
                          <td className="p-2">
                            <input
                              type="checkbox"
                              checked={sel?.selected || false}
                              onChange={() => togglePosition(p.id)}
                              className="rounded border-gray-300"
                            />
                          </td>
                          <td className="p-2 font-medium">{posLabel(p)}</td>
                          <td className="p-2">{p.color}</td>
                          <td className="p-2">{p.size}</td>
                          <td className="p-2">{p.quantity} pcs</td>
                          <td className="p-2 w-24">
                            <input
                              type="number"
                              min={1}
                              max={p.quantity}
                              value={sel?.quantity_shipped || 0}
                              onChange={(e) => updateQuantity(p.id, parseInt(e.target.value) || 0)}
                              disabled={!sel?.selected}
                              className="w-full rounded border border-gray-300 px-2 py-1 text-sm disabled:opacity-50"
                            />
                          </td>
                          <td className="p-2 w-20">
                            <input
                              type="number"
                              min={1}
                              value={sel?.box_number ?? ''}
                              onChange={(e) => updateBoxNumber(p.id, e.target.value ? parseInt(e.target.value) : null)}
                              disabled={!sel?.selected}
                              placeholder="-"
                              className="w-full rounded border border-gray-300 px-2 py-1 text-sm disabled:opacity-50"
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Shipping details */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <Select
                label="Carrier"
                value={carrier}
                onChange={(e) => setCarrier(e.target.value)}
                options={CARRIERS}
              />
              <Select
                label="Shipping Method"
                value={shippingMethod}
                onChange={(e) => setShippingMethod(e.target.value)}
                options={SHIPPING_METHODS}
              />
              <Input
                label="Tracking Number"
                value={trackingNumber}
                onChange={(e) => setTrackingNumber(e.target.value)}
                placeholder="e.g., JNE123456789"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <Input
                label="Total Boxes"
                type="number"
                min={1}
                value={totalBoxes}
                onChange={(e) => setTotalBoxes(e.target.value)}
                placeholder="Number of boxes"
              />
              <Input
                label="Total Weight (kg)"
                type="number"
                step="0.1"
                min={0}
                value={totalWeight}
                onChange={(e) => setTotalWeight(e.target.value)}
                placeholder="e.g., 25.5"
              />
              <Input
                label="Estimated Delivery"
                type="date"
                value={estimatedDelivery}
                onChange={(e) => setEstimatedDelivery(e.target.value)}
              />
            </div>

            <div className="mb-4">
              <label className="mb-1 block text-sm font-medium text-gray-700">Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Shipping notes, special instructions..."
                rows={2}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>

            <div className="flex justify-end">
              <Button
                className="bg-green-600 hover:bg-green-700 text-white"
                onClick={() => setShowCreateConfirm(true)}
                disabled={selectedItems.length === 0 || createShipment.isPending}
              >
                {createShipment.isPending ? <Spinner className="h-4 w-4 mr-2" /> : null}
                Create Shipment ({totalPieces} pcs)
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* No positions ready message */}
      {readyPositions.length === 0 && shipments.length === 0 && (
        <Card>
          <div className="p-8 text-center text-gray-400">
            No positions are ready for shipment yet.
          </div>
        </Card>
      )}

      {readyPositions.length === 0 && shipments.length > 0 && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          All positions have been included in shipments.
        </div>
      )}

      {/* Confirm dialogs */}
      <ConfirmDialog
        open={showCreateConfirm}
        onClose={() => setShowCreateConfirm(false)}
        onConfirm={handleCreate}
        title="Create Shipment"
        message={`Create a shipment with ${selectedItems.length} position(s) totaling ${totalPieces} pieces?`}
      />

      {showShipConfirm && (
        <ConfirmDialog
          open={!!showShipConfirm}
          onClose={() => setShowShipConfirm(null)}
          onConfirm={() => handleShip(showShipConfirm)}
          title="Confirm Ship"
          message="Mark this shipment as shipped? This will update position statuses and notify Sales."
        />
      )}

      {showCancelConfirm && (
        <ConfirmDialog
          open={!!showCancelConfirm}
          onClose={() => setShowCancelConfirm(null)}
          onConfirm={() => handleCancel(showCancelConfirm)}
          title="Cancel Shipment"
          message="Cancel this shipment? This action cannot be undone."
        />
      )}
    </div>
  );
}
