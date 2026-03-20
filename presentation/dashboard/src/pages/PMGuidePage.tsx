import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import apiClient from '@/api/client';

const LANGUAGES = [
  { code: 'en', label: 'English', flag: '\uD83C\uDDEC\uD83C\uDDE7' },
  { code: 'id', label: 'Bahasa Indonesia', flag: '\uD83C\uDDEE\uD83C\uDDE9' },
];

export default function PMGuidePage() {
  const navigate = useNavigate();
  const [lang, setLang] = useState<string>('en');
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    setError('');
    apiClient
      .get(`/guides/production_manager/${lang}`, { responseType: 'text' })
      .then((r) => {
        setContent(typeof r.data === 'string' ? r.data : JSON.stringify(r.data));
        setLoading(false);
      })
      .catch((err) => {
        const msg =
          err?.response?.data?.detail || err?.message || 'Failed to load guide';
        setError(msg);
        setLoading(false);
      });
  }, [lang]);

  const handleDownloadPdf = useCallback(() => {
    if (!contentRef.current) return;

    // Use browser print to PDF — most reliable cross-browser approach
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Please allow popups to download PDF');
      return;
    }

    const title =
      lang === 'id'
        ? 'Panduan Production Manager - Moonjar PMS'
        : 'Production Manager Guide - Moonjar PMS';

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${title}</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 24px;
            color: #1a1a1a;
            line-height: 1.7;
            font-size: 14px;
          }
          h1 { font-size: 24px; color: #111; border-bottom: 2px solid #2563eb; padding-bottom: 8px; margin-top: 32px; }
          h2 { font-size: 20px; color: #1e40af; margin-top: 28px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }
          h3 { font-size: 16px; color: #374151; margin-top: 20px; }
          table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }
          th, td { border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; }
          th { background: #f3f4f6; font-weight: 600; }
          code { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
          pre { background: #f3f4f6; padding: 16px; border-radius: 8px; overflow-x: auto; }
          pre code { background: none; padding: 0; }
          blockquote { border-left: 4px solid #2563eb; margin: 16px 0; padding: 8px 16px; background: #eff6ff; color: #1e40af; }
          ul, ol { padding-left: 24px; }
          li { margin-bottom: 4px; }
          strong { color: #111; }
          hr { border: none; border-top: 1px solid #e5e7eb; margin: 24px 0; }
          @media print {
            body { padding: 0; }
            h1, h2 { page-break-after: avoid; }
            table, pre { page-break-inside: avoid; }
          }
        </style>
      </head>
      <body>
        ${contentRef.current.innerHTML}
      </body>
      </html>
    `);
    printWindow.document.close();

    // Wait for content to render, then trigger print dialog
    setTimeout(() => {
      printWindow.print();
    }, 500);
  }, [lang]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {lang === 'id' ? 'Panduan PM' : 'PM Guide'}
          </h1>
          <p className="mt-0.5 text-sm text-gray-500">
            {lang === 'id'
              ? 'Panduan lengkap untuk Production Manager'
              : 'Complete guide for Production Manager role'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => navigate('/manager')}>
            {'\u2190'} Dashboard
          </Button>
          <Button variant="secondary" onClick={handleDownloadPdf}>
            {'\uD83D\uDCC4'} Download PDF
          </Button>
        </div>
      </div>

      {/* Language selector */}
      <div className="flex gap-2">
        {LANGUAGES.map((l) => (
          <button
            key={l.code}
            onClick={() => setLang(l.code)}
            className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
              lang === l.code
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            <span className="text-lg">{l.flag}</span>
            {l.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-6 py-8 text-center">
          <p className="text-sm text-red-600">{'\u26A0'} {error}</p>
          <Button
            className="mt-4"
            variant="secondary"
            onClick={() => setLang(lang)}
          >
            Retry
          </Button>
        </div>
      ) : (
        <div
          ref={contentRef}
          className="prose prose-sm max-w-none rounded-lg border border-gray-200 bg-white px-8 py-6 shadow-sm
            prose-headings:text-gray-900
            prose-h1:border-b prose-h1:border-blue-200 prose-h1:pb-2 prose-h1:text-xl
            prose-h2:border-b prose-h2:border-gray-100 prose-h2:pb-1 prose-h2:text-lg prose-h2:text-blue-800
            prose-h3:text-base prose-h3:text-gray-700
            prose-p:text-gray-600
            prose-a:text-blue-600
            prose-strong:text-gray-900
            prose-code:rounded prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-xs prose-code:font-normal prose-code:text-indigo-600
            prose-pre:bg-gray-50
            prose-blockquote:border-l-blue-500 prose-blockquote:bg-blue-50 prose-blockquote:text-blue-800
            prose-table:text-sm
            prose-th:bg-gray-50
            prose-td:border-gray-200
            prose-th:border-gray-200
            prose-li:text-gray-600"
        >
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
