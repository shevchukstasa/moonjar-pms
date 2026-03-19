import { useState, useCallback, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useUploadPdf, useConfirmPdf } from '@/hooks/useOrders';
import { useFactories } from '@/hooks/useFactories';
import type { PdfParsedOrder, PdfParsedItem, FieldConfidence } from '@/api/orders';

interface Props {
  open: boolean;
  onClose: () => void;
  defaultFactoryId?: string;
}

type Step = 'upload' | 'preview';

const PRODUCT_TYPES = [
  { value: 'tile', label: 'Tile' },
  { value: 'countertop', label: 'Countertop' },
  { value: 'sink', label: 'Sink' },
  { value: '3d', label: '3D' },
];

/** Returns a Tailwind ring class based on field confidence value */
function confidenceRing(fc?: FieldConfidence): string {
  if (!fc) return '';
  if (fc.value >= 0.8) return 'ring-1 ring-green-300';
  if (fc.value >= 0.5) return 'ring-1 ring-amber-300';
  if (fc.value > 0) return 'ring-1 ring-red-300';
  return 'ring-1 ring-red-400';
}

/** Small inline confidence badge */
function ConfidenceBadge({ fc }: { fc?: FieldConfidence }) {
  if (!fc || fc.source === 'not_found') return null;
  const pct = Math.round(fc.value * 100);
  const color =
    fc.value >= 0.8 ? 'text-green-600 bg-green-50' :
    fc.value >= 0.5 ? 'text-amber-600 bg-amber-50' :
    'text-red-600 bg-red-50';
  return (
    <span className={`ml-1 inline-block rounded px-1 py-0.5 text-[10px] font-medium ${color}`}>
      {pct}%
    </span>
  );
}

export function PdfUploadDialog({ open, onClose, defaultFactoryId }: Props) {
  const [step, setStep] = useState<Step>('upload');
  const [factoryId, setFactoryId] = useState(defaultFactoryId || '');
  const [parsedOrder, setParsedOrder] = useState<PdfParsedOrder | null>(null);
  const [confidence, setConfidence] = useState(0);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [templateName, setTemplateName] = useState('');
  const [templateScore, setTemplateScore] = useState(0);
  const [uploadError, setUploadError] = useState('');
  const [createError, setCreateError] = useState('');

  const uploadPdf = useUploadPdf();
  const confirmPdf = useConfirmPdf();
  const { data: factoriesData } = useFactories();

  const factoryOptions = useMemo(() => {
    const opts = [{ value: '', label: 'Select factory...' }];
    for (const f of factoriesData?.items || []) {
      opts.push({ value: f.id, label: f.name });
    }
    return opts;
  }, [factoriesData]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (!acceptedFiles.length) return;
      if (!factoryId) {
        setUploadError('Please select a factory first');
        return;
      }

      setUploadError('');
      const file = acceptedFiles[0];

      try {
        const result = await uploadPdf.mutateAsync({ file, factoryId });
        setParsedOrder(result.parsed_order);
        setConfidence(result.confidence);
        setWarnings(result.warnings);
        setValidationErrors(result.validation_errors || []);
        setTemplateName(result.template_name || '');
        setTemplateScore(result.template_match_score || 0);
        setStep('preview');
      } catch (err: unknown) {
        const resp = (err as { response?: { data?: { detail?: string } } })?.response?.data;
        setUploadError(resp?.detail || 'Failed to parse PDF');
      }
    },
    [factoryId, uploadPdf],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024, // 20MB
    disabled: uploadPdf.isPending,
  });

  const updateField = (field: keyof PdfParsedOrder, value: unknown) => {
    if (!parsedOrder) return;
    setParsedOrder({ ...parsedOrder, [field]: value });
  };

  const updateItem = (idx: number, field: keyof PdfParsedItem, value: unknown) => {
    if (!parsedOrder) return;
    const items = [...parsedOrder.items];
    items[idx] = { ...items[idx], [field]: value };
    setParsedOrder({ ...parsedOrder, items });
  };

  const removeItem = (idx: number) => {
    if (!parsedOrder) return;
    setParsedOrder({ ...parsedOrder, items: parsedOrder.items.filter((_, i) => i !== idx) });
  };

  const addItem = () => {
    if (!parsedOrder) return;
    setParsedOrder({
      ...parsedOrder,
      items: [
        ...parsedOrder.items,
        {
          color: '', size: '', quantity_pcs: 1, quantity_sqm: null,
          application: null, finishing: null, collection: null,
          product_type: 'tile', application_type: null, place_of_application: null,
          thickness: 11.0,
        },
      ],
    });
  };

  const handleConfirm = async () => {
    if (!parsedOrder || !parsedOrder.items.length) return;
    setCreateError('');

    try {
      const payload: Record<string, unknown> = {
        order_number: parsedOrder.order_number,
        client: parsedOrder.client,
        client_location: parsedOrder.client_location || undefined,
        sales_manager_name: parsedOrder.sales_manager_name || undefined,
        factory_id: factoryId,
        document_date: parsedOrder.document_date || undefined,
        final_deadline: parsedOrder.final_deadline || undefined,
        desired_delivery_date: parsedOrder.desired_delivery_date || undefined,
        mandatory_qc: parsedOrder.mandatory_qc,
        notes: parsedOrder.notes || undefined,
        items: parsedOrder.items.map((it) => ({
          color: it.color,
          size: it.size,
          quantity_pcs: it.quantity_pcs,
          quantity_sqm: it.quantity_sqm,
          application: it.application || undefined,
          finishing: it.finishing || undefined,
          collection: it.collection || undefined,
          product_type: it.product_type || 'tile',
          thickness: it.thickness || 11.0,
        })),
      };

      await confirmPdf.mutateAsync(payload);
      handleClose();
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: unknown } } })?.response?.data;
      let msg = 'Failed to create order';
      if (resp?.detail) {
        if (typeof resp.detail === 'string') msg = resp.detail;
        else if (Array.isArray(resp.detail))
          msg = resp.detail.map((e: { msg?: string }) => e.msg || JSON.stringify(e)).join('; ');
      }
      setCreateError(msg);
    }
  };

  const handleClose = () => {
    setStep('upload');
    setParsedOrder(null);
    setConfidence(0);
    setWarnings([]);
    setValidationErrors([]);
    setTemplateName('');
    setTemplateScore(0);
    setUploadError('');
    setCreateError('');
    onClose();
  };

  const confidenceColor =
    confidence >= 0.8 ? 'text-green-600' : confidence >= 0.5 ? 'text-amber-600' : 'text-red-600';

  const headerFc = parsedOrder?.field_confidence;

  return (
    <Dialog open={open} onClose={handleClose} title="Upload PDF Order" className="w-full max-w-4xl">
      {step === 'upload' && (
        <div className="space-y-4">
          {/* Factory selection */}
          <Select
            label="Factory"
            value={factoryId}
            onChange={(e) => setFactoryId((e.target as HTMLSelectElement).value)}
            options={factoryOptions}
          />

          {/* Drop zone */}
          <div
            {...getRootProps()}
            className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
              isDragActive
                ? 'border-blue-400 bg-blue-50'
                : 'border-gray-300 bg-gray-50 hover:border-gray-400'
            } ${uploadPdf.isPending ? 'pointer-events-none opacity-50' : ''}`}
          >
            <input {...getInputProps()} />
            {uploadPdf.isPending ? (
              <div className="flex flex-col items-center gap-3">
                <Spinner />
                <p className="text-sm text-gray-500">Parsing PDF...</p>
              </div>
            ) : (
              <div>
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
                  <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-gray-700">
                  {isDragActive ? 'Drop PDF here...' : 'Drag & drop PDF order file, or click to browse'}
                </p>
                <p className="mt-1 text-xs text-gray-400">PDF only, max 20 MB</p>
              </div>
            )}
          </div>

          {uploadError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {uploadError}
            </div>
          )}

          <div className="flex justify-end">
            <Button variant="secondary" onClick={handleClose}>Cancel</Button>
          </div>
        </div>
      )}

      {step === 'preview' && parsedOrder && (
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          {/* Confidence, Template & Warnings */}
          <div className="flex flex-wrap items-start gap-3">
            <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
              <span className="text-xs text-gray-500">Confidence: </span>
              <span className={`font-bold ${confidenceColor}`}>{Math.round(confidence * 100)}%</span>
            </div>
            {templateName && (
              <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2">
                <span className="text-xs text-gray-500">Template: </span>
                <span className="text-xs font-medium text-blue-700">{templateName}</span>
                <span className="ml-1 text-[10px] text-blue-500">({Math.round(templateScore * 100)}% match)</span>
              </div>
            )}
          </div>

          {warnings.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              <p className="text-xs font-medium text-amber-800 mb-0.5">Warnings:</p>
              <ul className="list-disc pl-4 text-xs text-amber-700">
                {warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {validationErrors.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2">
              <p className="text-xs font-medium text-red-800 mb-0.5">Validation Issues:</p>
              <ul className="list-disc pl-4 text-xs text-red-700">
                {validationErrors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Order header fields */}
          <div className="grid grid-cols-2 gap-3">
            <div className={`rounded-md ${confidenceRing(headerFc?.order_number)}`}>
              <Input
                label={<>Order Number <ConfidenceBadge fc={headerFc?.order_number} /></>}
                value={parsedOrder.order_number}
                onChange={(e) => updateField('order_number', (e.target as HTMLInputElement).value)}
              />
            </div>
            <div className={`rounded-md ${confidenceRing(headerFc?.client)}`}>
              <Input
                label={<>Client <ConfidenceBadge fc={headerFc?.client} /></>}
                value={parsedOrder.client}
                onChange={(e) => updateField('client', (e.target as HTMLInputElement).value)}
              />
            </div>
            <div className={`rounded-md ${confidenceRing(headerFc?.client_location)}`}>
              <Input
                label={<>Client Location <ConfidenceBadge fc={headerFc?.client_location} /></>}
                value={parsedOrder.client_location || ''}
                onChange={(e) => updateField('client_location', (e.target as HTMLInputElement).value || null)}
              />
            </div>
            <div className={`rounded-md ${confidenceRing(headerFc?.sales_manager_name)}`}>
              <Input
                label={<>Sales Manager <ConfidenceBadge fc={headerFc?.sales_manager_name} /></>}
                value={parsedOrder.sales_manager_name || ''}
                onChange={(e) => updateField('sales_manager_name', (e.target as HTMLInputElement).value || null)}
              />
            </div>
            <div className={`rounded-md ${confidenceRing(headerFc?.document_date)}`}>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Document Date <ConfidenceBadge fc={headerFc?.document_date} />
              </label>
              <input
                type="date"
                value={parsedOrder.document_date || ''}
                onChange={(e) => updateField('document_date', e.target.value || null)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div className={`rounded-md ${confidenceRing(headerFc?.final_deadline)}`}>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Deadline <ConfidenceBadge fc={headerFc?.final_deadline} />
              </label>
              <input
                type="date"
                value={parsedOrder.final_deadline || ''}
                onChange={(e) => updateField('final_deadline', e.target.value || null)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Select
              label="Factory"
              value={factoryId}
              onChange={(e) => setFactoryId((e.target as HTMLSelectElement).value)}
              options={factoryOptions}
            />
            <label className="flex items-center gap-2 text-sm mt-6">
              <input
                type="checkbox"
                checked={parsedOrder.mandatory_qc}
                onChange={(e) => updateField('mandatory_qc', e.target.checked)}
                className="rounded border-gray-300"
              />
              Mandatory QC
            </label>
          </div>

          <Input
            label="Notes"
            value={parsedOrder.notes || ''}
            onChange={(e) => updateField('notes', (e.target as HTMLInputElement).value || null)}
            placeholder="Optional notes"
          />

          {/* Items table */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-900">
                Items ({parsedOrder.items.length})
              </h3>
              <Button type="button" variant="secondary" size="sm" onClick={addItem}>
                + Add Item
              </Button>
            </div>

            <div className="space-y-3">
              {parsedOrder.items.map((item, idx) => {
                const ifc = item.field_confidence;
                return (
                  <div key={idx} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs font-medium text-gray-500">Item {idx + 1}</span>
                      {parsedOrder.items.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeItem(idx)}
                          className="text-xs text-red-500 hover:text-red-700"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                    <div className="grid grid-cols-4 gap-2">
                      <div className={`rounded-md ${confidenceRing(ifc?.color)}`}>
                        <Input
                          label={<>Color <ConfidenceBadge fc={ifc?.color} /></>}
                          value={item.color}
                          onChange={(e) => updateItem(idx, 'color', (e.target as HTMLInputElement).value)}
                        />
                      </div>
                      <div className={`rounded-md ${confidenceRing(ifc?.size)}`}>
                        <Input
                          label={<>Size <ConfidenceBadge fc={ifc?.size} /></>}
                          value={item.size}
                          onChange={(e) => updateItem(idx, 'size', (e.target as HTMLInputElement).value)}
                        />
                      </div>
                      <div className={`rounded-md ${confidenceRing(ifc?.quantity_pcs)}`}>
                        <Input
                          label={<>Quantity (pcs) <ConfidenceBadge fc={ifc?.quantity_pcs} /></>}
                          type="number"
                          value={item.quantity_pcs}
                          onChange={(e) => updateItem(idx, 'quantity_pcs', parseInt((e.target as HTMLInputElement).value) || 0)}
                        />
                      </div>
                      <Select
                        label="Product Type"
                        value={item.product_type}
                        onChange={(e) => updateItem(idx, 'product_type', (e.target as HTMLSelectElement).value)}
                        options={PRODUCT_TYPES}
                      />
                      <Input
                        label="Application"
                        value={item.application || ''}
                        onChange={(e) => updateItem(idx, 'application', (e.target as HTMLInputElement).value || null)}
                      />
                      <Input
                        label="Finishing"
                        value={item.finishing || ''}
                        onChange={(e) => updateItem(idx, 'finishing', (e.target as HTMLInputElement).value || null)}
                      />
                      <Input
                        label="Collection"
                        value={item.collection || ''}
                        onChange={(e) => updateItem(idx, 'collection', (e.target as HTMLInputElement).value || null)}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {createError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {createError}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between border-t pt-4">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setStep('upload');
                setParsedOrder(null);
              }}
            >
              Re-upload
            </Button>
            <div className="flex gap-3">
              <Button variant="secondary" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                onClick={handleConfirm}
                disabled={
                  confirmPdf.isPending ||
                  !parsedOrder.order_number ||
                  !parsedOrder.client ||
                  !factoryId ||
                  parsedOrder.items.length === 0
                }
              >
                {confirmPdf.isPending ? 'Creating...' : 'Confirm & Create Order'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </Dialog>
  );
}
