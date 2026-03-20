import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import apiClient from '@/api/client';

/* ────────────────────────────────────────────────────
   Types & Constants
   ──────────────────────────────────────────────────── */

interface TocEntry {
  id: string;
  text: string;
  level: number; // 2 = h2 (section), 3 = h3 (subsection)
}

const LANGUAGES = [
  { code: 'en', label: 'English', flag: '\uD83C\uDDEC\uD83C\uDDE7' },
  { code: 'id', label: 'Bahasa Indonesia', flag: '\uD83C\uDDEE\uD83C\uDDE9' },
] as const;

/** Icons for each top-level section (by index 0-9) */
const SECTION_ICONS = [
  '\uD83D\uDE80', // Getting Started
  '\uD83D\uDCCA', // Dashboard
  '\uD83E\uDDEA', // Materials
  '\uD83D\uDCE6', // Orders
  '\u2705',       // Tasks
  '\uD83D\uDCD0', // Consumption Rules
  '\uD83D\uDCC5', // Schedule
  '\uD83D\uDD25', // Kiln Inspections
  '\uD83E\uDDEA', // Consumption Measurement Tasks
  '\uD83D\uDCA1', // Tips
];

/* ────────────────────────────────────────────────────
   Helpers
   ──────────────────────────────────────────────────── */

/** Convert markdown heading text to URL-safe slug */
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
}

/** Parse markdown to extract TOC entries from ## and ### headings */
function extractToc(md: string): TocEntry[] {
  const entries: TocEntry[] = [];
  const lines = md.split('\n');
  for (const line of lines) {
    const m2 = line.match(/^##\s+(.+)/);
    const m3 = line.match(/^###\s+(.+)/);
    if (m2) {
      const text = m2[1].trim();
      entries.push({ id: slugify(text), text, level: 2 });
    } else if (m3) {
      const text = m3[1].trim();
      entries.push({ id: slugify(text), text, level: 3 });
    }
  }
  return entries;
}

/** Get top-level sections (h2 only) */
function getSections(toc: TocEntry[]): TocEntry[] {
  return toc.filter((e) => e.level === 2);
}

/** Get subsections for a given section */
function getSubsections(toc: TocEntry[], sectionId: string): TocEntry[] {
  const sectionIdx = toc.findIndex((e) => e.id === sectionId && e.level === 2);
  if (sectionIdx === -1) return [];
  const subs: TocEntry[] = [];
  for (let i = sectionIdx + 1; i < toc.length; i++) {
    if (toc[i].level === 2) break;
    if (toc[i].level === 3) subs.push(toc[i]);
  }
  return subs;
}

/* ────────────────────────────────────────────────────
   Custom Markdown renderers that inject IDs for scroll
   ──────────────────────────────────────────────────── */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function HeadingRenderer({ level, children, ...props }: any) {
  const text = String(children);
  const id = slugify(text);
  const Tag = `h${level}` as keyof JSX.IntrinsicElements;

  const styles: Record<number, string> = {
    1: 'text-2xl font-bold text-gray-900 mb-4 mt-8 pb-3 border-b-2 border-blue-500',
    2: 'text-xl font-bold text-gray-900 mb-3 mt-10 pb-2 border-b border-gray-200 scroll-mt-6',
    3: 'text-base font-semibold text-gray-800 mb-2 mt-6 scroll-mt-6',
  };

  return (
    <Tag id={id} className={styles[level] || ''} {...props}>
      {children}
    </Tag>
  );
}

/* ────────────────────────────────────────────────────
   Sidebar TOC Component
   ──────────────────────────────────────────────────── */

function SidebarToc({
  toc,
  activeId,
  onNavigate,
  expandedSections,
  toggleSection,
}: {
  toc: TocEntry[];
  activeId: string;
  onNavigate: (id: string) => void;
  expandedSections: Set<string>;
  toggleSection: (id: string) => void;
}) {
  const sections = getSections(toc);

  return (
    <nav className="space-y-0.5">
      {sections.map((section, idx) => {
        const subs = getSubsections(toc, section.id);
        const isActive = activeId === section.id || subs.some((s) => s.id === activeId);
        const isExpanded = expandedSections.has(section.id) || isActive;
        const icon = SECTION_ICONS[idx] || '\uD83D\uDCC4';

        return (
          <div key={section.id}>
            {/* Section header */}
            <button
              onClick={() => {
                onNavigate(section.id);
                if (subs.length > 0) toggleSection(section.id);
              }}
              className={`group flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-medium transition-all ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <span className="flex-shrink-0 text-base">{icon}</span>
              <span className="flex-1 truncate">{section.text.replace(/^\d+\.\s*/, '')}</span>
              {subs.length > 0 && (
                <span className={`flex-shrink-0 text-[10px] text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                  {'\u25B6'}
                </span>
              )}
            </button>

            {/* Subsections */}
            {isExpanded && subs.length > 0 && (
              <div className="ml-4 mt-0.5 space-y-0.5 border-l-2 border-gray-100 pl-3">
                {subs.map((sub) => {
                  const subActive = activeId === sub.id;
                  return (
                    <button
                      key={sub.id}
                      onClick={() => onNavigate(sub.id)}
                      className={`block w-full rounded-md px-2.5 py-1.5 text-left text-xs transition-all ${
                        subActive
                          ? 'bg-blue-50 font-medium text-blue-700'
                          : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                      }`}
                    >
                      {sub.text.replace(/^\d+\.\d+\.?\s*/, '')}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
}

/* ────────────────────────────────────────────────────
   Mobile TOC Sheet
   ──────────────────────────────────────────────────── */

function MobileTocSheet({
  open,
  onClose,
  toc,
  activeId,
  onNavigate,
}: {
  open: boolean;
  onClose: () => void;
  toc: TocEntry[];
  activeId: string;
  onNavigate: (id: string) => void;
}) {
  if (!open) return null;

  const sections = getSections(toc);

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      {/* Sheet */}
      <div className="fixed inset-y-0 left-0 z-50 w-80 max-w-[85vw] overflow-y-auto bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="font-semibold text-gray-900">Contents</h3>
          <button onClick={onClose} className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            {'\u2715'}
          </button>
        </div>
        <div className="p-3 space-y-1">
          {sections.map((section, idx) => {
            const subs = getSubsections(toc, section.id);
            const isActive = activeId === section.id || subs.some((s) => s.id === activeId);
            const icon = SECTION_ICONS[idx] || '\uD83D\uDCC4';

            return (
              <div key={section.id}>
                <button
                  onClick={() => { onNavigate(section.id); onClose(); }}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-sm font-medium ${
                    isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <span className="text-base">{icon}</span>
                  <span>{section.text.replace(/^\d+\.\s*/, '')}</span>
                </button>
                {subs.length > 0 && (
                  <div className="ml-8 space-y-0.5 border-l-2 border-gray-100 pl-3">
                    {subs.map((sub) => (
                      <button
                        key={sub.id}
                        onClick={() => { onNavigate(sub.id); onClose(); }}
                        className={`block w-full rounded-md px-2 py-1.5 text-left text-xs ${
                          activeId === sub.id
                            ? 'font-medium text-blue-700'
                            : 'text-gray-500 hover:text-gray-700'
                        }`}
                      >
                        {sub.text.replace(/^\d+\.\d+\.?\s*/, '')}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

/* ────────────────────────────────────────────────────
   Progress Bar
   ──────────────────────────────────────────────────── */

function ReadingProgress({ contentRef }: { contentRef: React.RefObject<HTMLDivElement | null> }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const el = contentRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const total = el.scrollHeight - window.innerHeight;
      const scrolled = -rect.top;
      setProgress(total > 0 ? Math.min(100, Math.max(0, (scrolled / total) * 100)) : 0);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [contentRef]);

  return (
    <div className="h-1 w-full bg-gray-100 rounded-full overflow-hidden">
      <div
        className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-[width] duration-150"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}

/* ────────────────────────────────────────────────────
   Main PMGuidePage Component
   ──────────────────────────────────────────────────── */

export default function PMGuidePage() {
  const navigate = useNavigate();
  const [lang, setLang] = useState<string>('en');
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeId, setActiveId] = useState('');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [mobileTocOpen, setMobileTocOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // Fetch guide content
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
        const msg = err?.response?.data?.detail || err?.message || 'Failed to load guide';
        setError(msg);
        setLoading(false);
      });
  }, [lang]);

  // Parse TOC from content
  const toc = useMemo(() => extractToc(content), [content]);

  // Scroll spy — track which heading is currently in view
  useEffect(() => {
    if (toc.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // Find the topmost visible heading
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
            break;
          }
        }
      },
      { rootMargin: '-80px 0px -60% 0px', threshold: 0 },
    );

    // Observe all heading elements
    const timer = setTimeout(() => {
      for (const entry of toc) {
        const el = document.getElementById(entry.id);
        if (el) observer.observe(el);
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, [toc]);

  // Navigate to heading
  const scrollTo = useCallback((id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveId(id);
    }
  }, []);

  // Toggle sidebar section
  const toggleSection = useCallback((id: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // Download PDF
  const handleDownloadPdf = useCallback(() => {
    if (!contentRef.current) return;

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Please allow popups to download PDF');
      return;
    }

    const title = lang === 'id'
      ? 'Panduan Production Manager - Moonjar PMS'
      : 'Production Manager Guide - Moonjar PMS';

    printWindow.document.write(`<!DOCTYPE html><html><head><title>${title}</title>
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 780px; margin: 0 auto; padding: 40px 24px; color: #1a1a1a; line-height: 1.7; font-size: 13px; }
        h1 { font-size: 22px; color: #111; border-bottom: 2px solid #2563eb; padding-bottom: 8px; margin-top: 28px; }
        h2 { font-size: 18px; color: #1e40af; margin-top: 24px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }
        h3 { font-size: 14px; color: #374151; margin-top: 16px; }
        table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 12px; }
        th, td { border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; }
        th { background: #f3f4f6; font-weight: 600; }
        code { background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
        pre { background: #f3f4f6; padding: 12px; border-radius: 6px; overflow-x: auto; }
        pre code { background: none; padding: 0; }
        blockquote { border-left: 3px solid #2563eb; margin: 12px 0; padding: 6px 12px; background: #eff6ff; color: #1e40af; font-size: 12px; }
        ul, ol { padding-left: 20px; } li { margin-bottom: 3px; }
        strong { color: #111; }
        hr { border: none; border-top: 1px solid #e5e7eb; margin: 20px 0; }
        @media print { body { padding: 0; } h1, h2 { page-break-after: avoid; } table, pre { page-break-inside: avoid; } }
      </style></head><body>${contentRef.current.innerHTML}</body></html>`);
    printWindow.document.close();
    setTimeout(() => printWindow.print(), 400);
  }, [lang]);

  // Custom markdown components
  const mdComponents = useMemo(
    () => ({
      h1: (props: object) => <HeadingRenderer level={1} {...props} />,
      h2: (props: object) => <HeadingRenderer level={2} {...props} />,
      h3: (props: object) => <HeadingRenderer level={3} {...props} />,
      // Styled table
      table: (props: object) => (
        <div className="my-4 overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-sm" {...props} />
        </div>
      ),
      thead: (props: object) => <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-500" {...props} />,
      th: (props: object) => <th className="px-4 py-2.5 text-left font-semibold text-gray-700" {...props} />,
      td: (props: object) => <td className="border-t border-gray-100 px-4 py-2 text-gray-600" {...props} />,
      // Styled blockquote
      blockquote: (props: object) => (
        <div className="my-4 flex gap-3 rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3">
          <span className="flex-shrink-0 text-lg">{'\uD83D\uDCA1'}</span>
          <div className="text-sm text-blue-800 [&>p]:m-0" {...props} />
        </div>
      ),
      // Styled code blocks
      pre: (props: object) => <pre className="my-3 overflow-x-auto rounded-lg bg-gray-900 px-4 py-3 text-xs text-gray-100" {...props} />,
      code: ({ className, children, ...props }: { className?: string; children?: React.ReactNode }) => {
        // Inline code vs block code
        if (className) {
          return <code className={className} {...props}>{children}</code>;
        }
        return (
          <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-indigo-600" {...props}>
            {children}
          </code>
        );
      },
      // Styled paragraphs
      p: (props: object) => <p className="my-2 text-sm leading-relaxed text-gray-600" {...props} />,
      // Styled lists
      ul: (props: object) => <ul className="my-2 ml-4 list-disc space-y-1 text-sm text-gray-600" {...props} />,
      ol: (props: object) => <ol className="my-2 ml-4 list-decimal space-y-1 text-sm text-gray-600" {...props} />,
      li: (props: object) => <li className="leading-relaxed" {...props} />,
      // Styled links
      a: (props: object) => <a className="font-medium text-blue-600 underline decoration-blue-200 hover:text-blue-800 hover:decoration-blue-400" {...props} />,
      // Strong text
      strong: (props: object) => <strong className="font-semibold text-gray-900" {...props} />,
      // Horizontal rule
      hr: () => <hr className="my-8 border-gray-200" />,
    }),
    [],
  );

  // Section count for header
  const sectionCount = getSections(toc).length;

  return (
    <div className="flex h-full">
      {/* ──── Desktop Sidebar ──── */}
      <aside className="hidden lg:flex lg:w-72 xl:w-80 flex-shrink-0 flex-col border-r border-gray-200 bg-gray-50/50">
        {/* Sidebar header */}
        <div className="border-b px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-sm">{'\uD83D\uDCD6'}</span>
            <div>
              <h2 className="text-sm font-bold text-gray-900">
                {lang === 'id' ? 'Panduan PM' : 'PM Guide'}
              </h2>
              <p className="text-[11px] text-gray-400">
                {sectionCount} {lang === 'id' ? 'bagian' : 'sections'}
              </p>
            </div>
          </div>

          {/* Language toggle */}
          <div className="mt-3 flex rounded-lg border border-gray-200 bg-white p-0.5">
            {LANGUAGES.map((l) => (
              <button
                key={l.code}
                onClick={() => setLang(l.code)}
                className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium transition-all ${
                  lang === l.code
                    ? 'bg-blue-500 text-white shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <span className="text-sm">{l.flag}</span>
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* TOC navigation */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          {loading ? (
            <div className="flex justify-center py-8">
              <Spinner className="h-5 w-5" />
            </div>
          ) : (
            <SidebarToc
              toc={toc}
              activeId={activeId}
              onNavigate={scrollTo}
              expandedSections={expandedSections}
              toggleSection={toggleSection}
            />
          )}
        </div>

        {/* Sidebar footer actions */}
        <div className="border-t px-4 py-3 space-y-2">
          <Button
            variant="secondary"
            className="w-full justify-center text-xs"
            onClick={handleDownloadPdf}
          >
            {'\uD83D\uDCC4'} {lang === 'id' ? 'Unduh PDF' : 'Download PDF'}
          </Button>
          <Button
            variant="ghost"
            className="w-full justify-center text-xs"
            onClick={() => navigate('/manager')}
          >
            {'\u2190'} {lang === 'id' ? 'Kembali' : 'Back to Dashboard'}
          </Button>
        </div>
      </aside>

      {/* ──── Main Content ──── */}
      <div className="flex-1 min-w-0">
        {/* Top bar (sticky) */}
        <div className="sticky top-0 z-20 border-b bg-white/95 backdrop-blur">
          <div className="flex items-center justify-between px-4 py-2 lg:px-8">
            {/* Mobile: hamburger + title */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => setMobileTocOpen(true)}
                className="lg:hidden rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                title="Table of Contents"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h7" />
                </svg>
              </button>
              <div className="lg:hidden">
                <h1 className="text-sm font-bold text-gray-900">
                  {lang === 'id' ? 'Panduan PM' : 'PM Guide'}
                </h1>
              </div>
              {/* Desktop: language tabs */}
              <div className="hidden lg:flex items-center gap-1.5">
                {toc.length > 0 && activeId && (
                  <span className="text-xs text-gray-400">
                    {toc.find((e) => e.id === activeId)?.text || ''}
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              {/* Mobile language selector */}
              <div className="lg:hidden flex rounded-lg border border-gray-200 bg-white p-0.5">
                {LANGUAGES.map((l) => (
                  <button
                    key={l.code}
                    onClick={() => setLang(l.code)}
                    className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-all ${
                      lang === l.code
                        ? 'bg-blue-500 text-white'
                        : 'text-gray-400'
                    }`}
                  >
                    <span className="text-sm">{l.flag}</span>
                  </button>
                ))}
              </div>
              <button
                onClick={handleDownloadPdf}
                className="hidden sm:flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
              >
                {'\uD83D\uDCC4'} PDF
              </button>
              <button
                onClick={() => navigate('/manager')}
                className="flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
              >
                {'\u2190'} <span className="hidden sm:inline">{lang === 'id' ? 'Kembali' : 'Dashboard'}</span>
              </button>
            </div>
          </div>
          <ReadingProgress contentRef={contentRef} />
        </div>

        {/* Content area */}
        <div className="mx-auto max-w-3xl px-4 py-6 lg:px-8 lg:py-8">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Spinner className="h-8 w-8" />
              <p className="mt-3 text-sm text-gray-400">
                {lang === 'id' ? 'Memuat panduan...' : 'Loading guide...'}
              </p>
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-10 text-center">
              <p className="text-3xl">{'\u26A0\uFE0F'}</p>
              <p className="mt-2 font-medium text-red-800">{error}</p>
              <Button className="mt-4" variant="secondary" onClick={() => setLang(lang)}>
                {lang === 'id' ? 'Coba lagi' : 'Retry'}
              </Button>
            </div>
          ) : (
            <article ref={contentRef} className="guide-content">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={mdComponents}
              >
                {content}
              </ReactMarkdown>

              {/* End-of-guide footer */}
              <div className="mt-12 rounded-xl border border-gray-200 bg-gradient-to-br from-gray-50 to-blue-50/30 p-6 text-center">
                <p className="text-2xl">{'\uD83C\uDF1F'}</p>
                <p className="mt-2 text-sm font-medium text-gray-700">
                  {lang === 'id'
                    ? 'Anda telah selesai membaca panduan ini!'
                    : "You've reached the end of the guide!"}
                </p>
                <p className="mt-1 text-xs text-gray-400">
                  {lang === 'id'
                    ? 'Gunakan AI Chat di dashboard untuk pertanyaan lebih lanjut.'
                    : 'Use the AI Chat on the dashboard for any further questions.'}
                </p>
                <Button
                  className="mt-4"
                  onClick={() => navigate('/manager')}
                >
                  {'\u2190'} {lang === 'id' ? 'Kembali ke Dashboard' : 'Back to Dashboard'}
                </Button>
              </div>
            </article>
          )}
        </div>
      </div>

      {/* ──── Mobile TOC Sheet ──── */}
      <MobileTocSheet
        open={mobileTocOpen}
        onClose={() => setMobileTocOpen(false)}
        toc={toc}
        activeId={activeId}
        onNavigate={scrollTo}
      />
    </div>
  );
}
