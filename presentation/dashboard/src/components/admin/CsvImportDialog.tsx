import { useState, useCallback } from 'react';
import Papa from 'papaparse';
import { Upload, Download, CheckCircle, AlertCircle, X } from 'lucide-react';
import apiClient from '@/api/client';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';

/* ── types ──────────────────────────────────────────────────────────── */

export interface CsvColumn {
  key: string;
  header: string;
  required: boolean;
  type: 'string' | 'number' | 'boolean';
  example: string;
}

interface CsvImportDialogProps {
  open: boolean;
  onClose: () => void;
  entityName: string;
  entityLabel: string;
  columns: CsvColumn[];
  onSuccess: () => void;
}

interface ImportResult {
  created: number;
  skipped: number;
  errors: string[];
}

type Step = 'upload' | 'preview' | 'importing' | 'result';

/* ── helpers ────────────────────────────────────────────────────────── */

function generateTemplateCsv(columns: CsvColumn[]): string {
  const header = columns.map((c) => c.header).join(',');
  const example = columns.map((c) => c.example).join(',');
  return `${header}\n${example}\n`;
}

function downloadCsv(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function coerceValue(value: string | undefined, type: 'string' | 'number' | 'boolean'): unknown {
  if (value === undefined || value === null || value.trim() === '') return undefined;
  if (type === 'boolean') return ['true', '1', 'yes', 'da'].includes(value.toLowerCase().trim());
  if (type === 'number') {
    const n = parseFloat(value);
    return isNaN(n) ? undefined : n;
  }
  return value.trim();
}

/* ── component ──────────────────────────────────────────────────────── */

export function CsvImportDialog({ open, onClose, entityName, entityLabel, columns, onSuccess }: CsvImportDialogProps) {
  const [step, setStep] = useState<Step>('upload');
  const [parsedRows, setParsedRows] = useState<Record<string, string>[]>([]);
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({});
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setStep('upload');
    setParsedRows([]);
    setRowErrors({});
    setResult(null);
    setError(null);
  }, []);

  const handleClose = useCallback(() => {
    reset();
    onClose();
  }, [reset, onClose]);

  /* ── template download ────────────────────────────────────────────── */
  const handleDownloadTemplate = useCallback(() => {
    const csv = generateTemplateCsv(columns);
    downloadCsv(csv, `${entityName}_template.csv`);
  }, [columns, entityName]);

  /* ── file parsing ─────────────────────────────────────────────────── */
  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setError(null);

      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          if (!results.data || results.data.length === 0) {
            setError('CSV file is empty or has no data rows.');
            return;
          }

          const rows = results.data as Record<string, string>[];
          // Map CSV headers to column keys (case-insensitive)
          const headerMap: Record<string, string> = {};
          const csvHeaders = Object.keys(rows[0] || {});
          for (const col of columns) {
            const match = csvHeaders.find((h) => h.toLowerCase().trim() === col.header.toLowerCase().trim());
            if (match) headerMap[match] = col.key;
          }

          // Check required columns are present
          const missingRequired = columns.filter((c) => c.required && !Object.values(headerMap).includes(c.key));
          if (missingRequired.length > 0) {
            setError(`Missing required columns: ${missingRequired.map((c) => c.header).join(', ')}`);
            return;
          }

          // Remap rows to use column keys
          const mapped = rows.map((row) => {
            const out: Record<string, string> = {};
            for (const [csvKey, colKey] of Object.entries(headerMap)) {
              if (row[csvKey] !== undefined && row[csvKey] !== '') {
                out[colKey] = row[csvKey];
              }
            }
            return out;
          });

          // Validate required fields per row
          const errs: Record<number, string> = {};
          for (let i = 0; i < mapped.length; i++) {
            const missing = columns.filter((c) => c.required && (!mapped[i][c.key] || mapped[i][c.key].trim() === ''));
            if (missing.length > 0) {
              errs[i] = `Missing: ${missing.map((c) => c.header).join(', ')}`;
            }
          }

          setParsedRows(mapped);
          setRowErrors(errs);
          setStep('preview');
        },
        error: (err) => {
          setError(`Parse error: ${err.message}`);
        },
      });

      // Reset file input so same file can be re-selected
      e.target.value = '';
    },
    [columns],
  );

  /* ── remove row ───────────────────────────────────────────────────── */
  const removeRow = useCallback((idx: number) => {
    setParsedRows((prev) => prev.filter((_, i) => i !== idx));
    setRowErrors((prev) => {
      const next: Record<number, string> = {};
      for (const [k, v] of Object.entries(prev)) {
        const ki = parseInt(k);
        if (ki < idx) next[ki] = v;
        else if (ki > idx) next[ki - 1] = v;
      }
      return next;
    });
  }, []);

  /* ── import ───────────────────────────────────────────────────────── */
  const handleImport = useCallback(async () => {
    setStep('importing');
    try {
      // Coerce values to proper types
      const coerced = parsedRows.map((row) => {
        const out: Record<string, unknown> = {};
        for (const col of columns) {
          if (row[col.key] !== undefined) {
            const val = coerceValue(row[col.key], col.type);
            if (val !== undefined) out[col.key] = val;
          }
        }
        return out;
      });

      const res = await apiClient.post('/reference/bulk-import', {
        entity: entityName,
        rows: coerced,
      });
      setResult(res.data as ImportResult);
      setStep('result');
      if ((res.data as ImportResult).created > 0) {
        onSuccess();
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Import failed';
      setError(msg);
      setStep('preview');
    }
  }, [parsedRows, columns, entityName, onSuccess]);

  const validRows = parsedRows.filter((_, i) => !rowErrors[i]);
  const errorCount = Object.keys(rowErrors).length;

  /* ── render ───────────────────────────────────────────────────────── */
  return (
    <Dialog open={open} onClose={handleClose} title={`Import ${entityLabel} from CSV`} className="w-full max-w-3xl">
      <div className="max-h-[75vh] space-y-4 overflow-y-auto pr-1">

        {/* ── Step: Upload ─────────────────────────────────────────── */}
        {step === 'upload' && (
          <>
            <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
              <Upload className="mx-auto mb-3 h-10 w-10 text-gray-400" />
              <p className="mb-2 text-sm text-gray-600">Select a CSV file to import</p>
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                <Upload className="h-4 w-4" />
                Choose File
                <input type="file" accept=".csv,.tsv,.txt" onChange={handleFileSelect} className="hidden" />
              </label>
            </div>

            <div className="flex items-center justify-between rounded-md bg-gray-50 px-4 py-3">
              <div className="text-sm text-gray-600">
                <p className="font-medium">Need a template?</p>
                <p className="text-xs text-gray-400">Download a sample CSV with the correct column headers</p>
              </div>
              <Button variant="secondary" size="sm" onClick={handleDownloadTemplate}>
                <Download className="mr-1.5 h-4 w-4" /> Template
              </Button>
            </div>

            {/* Column reference */}
            <div className="rounded-md border border-gray-200 p-3">
              <p className="mb-2 text-xs font-semibold text-gray-500 uppercase">Expected columns</p>
              <div className="grid grid-cols-2 gap-1 text-xs">
                {columns.map((col, i) => (
                  <div key={col.key} className="flex items-center gap-1.5">
                    <span className="inline-flex h-4 w-4 items-center justify-center rounded bg-gray-200 text-[10px] font-bold text-gray-600">{i + 1}</span>
                    <span className={col.required ? 'font-semibold text-gray-700' : 'text-gray-500'}>{col.header}</span>
                    {col.required && <span className="text-red-400">*</span>}
                    <span className="text-gray-300">({col.type})</span>
                  </div>
                ))}
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-md bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
              </div>
            )}
          </>
        )}

        {/* ── Step: Preview ────────────────────────────────────────── */}
        {step === 'preview' && (
          <>
            <div className="flex items-center justify-between text-sm">
              <div>
                <span className="font-medium">{parsedRows.length}</span> rows parsed
                {errorCount > 0 && <span className="ml-2 text-red-500">({errorCount} with errors)</span>}
              </div>
              <Button variant="secondary" size="sm" onClick={reset}>Back</Button>
            </div>

            <div className="max-h-64 overflow-auto rounded border border-gray-200">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-gray-100">
                  <tr>
                    <th className="px-2 py-1.5 text-left font-semibold text-gray-600">#</th>
                    {columns.map((col) => (
                      <th key={col.key} className="px-2 py-1.5 text-left font-semibold text-gray-600">
                        {col.header}{col.required && <span className="text-red-400">*</span>}
                      </th>
                    ))}
                    <th className="w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {parsedRows.map((row, i) => (
                    <tr key={i} className={rowErrors[i] ? 'bg-red-50' : i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-2 py-1 text-gray-400">{i + 1}</td>
                      {columns.map((col) => (
                        <td key={col.key} className="max-w-[150px] truncate px-2 py-1">{row[col.key] || ''}</td>
                      ))}
                      <td className="px-1">
                        <button onClick={() => removeRow(i)} className="rounded p-0.5 text-gray-400 hover:text-red-500">
                          <X className="h-3 w-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-md bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={handleClose}>Cancel</Button>
              <Button onClick={handleImport} disabled={validRows.length === 0}>
                Import {validRows.length} rows
              </Button>
            </div>
          </>
        )}

        {/* ── Step: Importing ─────────────────────────────────────── */}
        {step === 'importing' && (
          <div className="flex flex-col items-center gap-3 py-8">
            <Spinner className="h-8 w-8" />
            <p className="text-sm text-gray-500">Importing {parsedRows.length} rows...</p>
          </div>
        )}

        {/* ── Step: Result ────────────────────────────────────────── */}
        {step === 'result' && result && (
          <>
            <div className="flex flex-col items-center gap-3 py-4">
              <CheckCircle className="h-12 w-12 text-green-500" />
              <p className="text-lg font-semibold text-gray-900">Import Complete</p>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-md bg-green-50 p-3">
                <p className="text-2xl font-bold text-green-700">{result.created}</p>
                <p className="text-xs text-green-600">Created</p>
              </div>
              <div className="rounded-md bg-yellow-50 p-3">
                <p className="text-2xl font-bold text-yellow-700">{result.skipped}</p>
                <p className="text-xs text-yellow-600">Skipped (duplicates)</p>
              </div>
              <div className="rounded-md bg-red-50 p-3">
                <p className="text-2xl font-bold text-red-700">{result.errors.length}</p>
                <p className="text-xs text-red-600">Errors</p>
              </div>
            </div>

            {result.errors.length > 0 && (
              <div className="max-h-32 overflow-auto rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                {result.errors.map((err, i) => <p key={i}>{err}</p>)}
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button onClick={handleClose}>Close</Button>
            </div>
          </>
        )}
      </div>
    </Dialog>
  );
}
