import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useAuthStore } from '@/stores/authStore';
import {
  useOnboardingProgress,
  useOnboardingContent,
  useCompleteSection,
  useSubmitQuiz,
} from '@/hooks/useOnboarding';
import type {
  SectionContent,
  QuizQuestion,
  LocaleString,
  SectionProgress,
  QuizResult,
} from '@/api/onboarding';
import { Spinner } from '@/components/ui/Spinner';

// ── Helpers ──────────────────────────────────────────────────────

type Lang = 'en' | 'id' | 'ru';

function t(ls: LocaleString | undefined, lang: Lang): string {
  if (!ls) return '';
  return ls[lang] || ls.en || '';
}

function getLang(user: { language?: string } | null): Lang {
  const l = user?.language;
  if (l === 'ru' || l === 'id' || l === 'en') return l;
  if (typeof navigator !== 'undefined') {
    const bl = navigator.language.slice(0, 2);
    if (bl === 'ru' || bl === 'id') return bl;
  }
  return 'en';
}

const SECTION_ICONS: Record<string, string> = {
  welcome: '🌋', navigation: '🧭', orders: '📦', materials: '🧱',
  schedule: '📅', kilns: '🔥', quality: '✅', tasks: '📋',
  telegram: '📱', reports: '📊', gamification: '🎮', advanced: '🧪',
};

const ACHIEVEMENT_THRESHOLDS = [
  { xp: 150, label: { en: 'Quick Learner', id: 'Pelajar Cepat', ru: '\u0411\u044b\u0441\u0442\u0440\u044b\u0439 \u0443\u0447\u0435\u043d\u0438\u043a' }, icon: '🌟' },
  { xp: 450, label: { en: 'Rising Star', id: 'Bintang Baru', ru: '\u0412\u043e\u0441\u0445\u043e\u0434\u044f\u0449\u0430\u044f \u0437\u0432\u0435\u0437\u0434\u0430' }, icon: '⭐' },
  { xp: 900, label: { en: 'Knowledge Master', id: 'Master Pengetahuan', ru: '\u041c\u0430\u0441\u0442\u0435\u0440 \u0437\u043d\u0430\u043d\u0438\u0439' }, icon: '🏆' },
  { xp: 1200, label: { en: 'Quiz Champion', id: 'Juara Kuis', ru: '\u0427\u0435\u043c\u043f\u0438\u043e\u043d \u0432\u0438\u043a\u0442\u043e\u0440\u0438\u043d' }, icon: '💎' },
  { xp: 1800, label: { en: 'Expert', id: 'Ahli', ru: 'Эксперт' }, icon: '👑' },
];

const ROLE_TITLES: Record<string, { title: LocaleString; subtitle: LocaleString }> = {
  production_manager: {
    title: { en: 'PM Onboarding Academy', id: 'Akademi Onboarding PM', ru: 'Академия онбординга PM' },
    subtitle: { en: 'Master the Production Management System', id: 'Kuasai Sistem Manajemen Produksi', ru: 'Освойте систему управления производством' },
  },
  ceo: {
    title: { en: 'CEO Onboarding Academy', id: 'Akademi Onboarding CEO', ru: 'Академия онбординга CEO' },
    subtitle: { en: 'Master Strategic Factory Oversight', id: 'Kuasai Pengawasan Strategis Pabrik', ru: 'Освойте стратегическое управление фабрикой' },
  },
  quality_manager: {
    title: { en: 'QM Onboarding Academy', id: 'Akademi Onboarding QM', ru: 'Академия онбординга QM' },
    subtitle: { en: 'Master Quality Control & Assurance', id: 'Kuasai Kontrol & Jaminan Kualitas', ru: 'Освойте контроль качества' },
  },
  warehouse: {
    title: { en: 'Warehouse Onboarding Academy', id: 'Akademi Onboarding Gudang', ru: 'Академия онбординга склада' },
    subtitle: { en: 'Master Stock & Logistics Management', id: 'Kuasai Manajemen Stok & Logistik', ru: 'Освойте управление складом и логистикой' },
  },
  sorter_packer: {
    title: { en: 'Packer Onboarding Academy', id: 'Akademi Onboarding Packer', ru: 'Академия онбординга упаковки' },
    subtitle: { en: 'Master Sorting & Packing Operations', id: 'Kuasai Operasi Sortir & Packing', ru: 'Освойте сортировку и упаковку' },
  },
  purchaser: {
    title: { en: 'Purchaser Onboarding Academy', id: 'Akademi Onboarding Pembelian', ru: 'Академия онбординга закупок' },
    subtitle: { en: 'Master Procurement & Supplier Management', id: 'Kuasai Pengadaan & Manajemen Pemasok', ru: 'Освойте закупки и работу с поставщиками' },
  },
  administrator: {
    title: { en: 'Admin Onboarding Academy', id: 'Akademi Onboarding Admin', ru: 'Академия онбординга администратора' },
    subtitle: { en: 'Master System Configuration & Data Management', id: 'Kuasai Konfigurasi Sistem & Manajemen Data', ru: 'Освойте настройку системы и управление данными' },
  },
  owner: {
    title: { en: 'Owner Onboarding Academy', id: 'Akademi Onboarding Owner', ru: 'Академия онбординга владельца' },
    subtitle: { en: 'Master Full System Overview & Analytics', id: 'Kuasai Gambaran & Analitik Sistem Lengkap', ru: 'Освойте полный обзор системы и аналитику' },
  },
};

const MESSAGES = {
  title: { en: 'Onboarding Academy', id: 'Akademi Onboarding', ru: 'Академия онбординга' } as LocaleString,
  subtitle: { en: 'Master the System', id: 'Kuasai Sistem', ru: 'Освойте систему' } as LocaleString,
  totalXp: { en: 'Total XP', id: 'Total XP', ru: '\u0412\u0441\u0435\u0433\u043e XP' } as LocaleString,
  sections: { en: 'sections', id: 'bagian', ru: '\u0440\u0430\u0437\u0434\u0435\u043b\u043e\u0432' } as LocaleString,
  completed: { en: 'completed', id: 'selesai', ru: '\u043f\u0440\u043e\u0439\u0434\u0435\u043d\u043e' } as LocaleString,
  startSection: { en: 'Start Learning', id: 'Mulai Belajar', ru: '\u041d\u0430\u0447\u0430\u0442\u044c' } as LocaleString,
  continueSection: { en: 'Continue', id: 'Lanjutkan', ru: '\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c' } as LocaleString,
  takeQuiz: { en: 'Take Quiz', id: 'Ikuti Kuis', ru: '\u041f\u0440\u043e\u0439\u0442\u0438 \u0442\u0435\u0441\u0442' } as LocaleString,
  retakeQuiz: { en: 'Retake Quiz', id: 'Ulangi Kuis', ru: '\u041f\u0435\u0440\u0435\u0441\u0434\u0430\u0442\u044c' } as LocaleString,
  next: { en: 'Next', id: 'Selanjutnya', ru: '\u0414\u0430\u043b\u0435\u0435' } as LocaleString,
  prev: { en: 'Back', id: 'Kembali', ru: '\u041d\u0430\u0437\u0430\u0434' } as LocaleString,
  finishReading: { en: 'Finish Reading', id: 'Selesai Membaca', ru: '\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c \u0447\u0442\u0435\u043d\u0438\u0435' } as LocaleString,
  submitQuiz: { en: 'Submit Answers', id: 'Kirim Jawaban', ru: '\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c' } as LocaleString,
  quizPassed: { en: 'Excellent! You passed!', id: 'Luar biasa! Anda lulus!', ru: '\u041e\u0442\u043b\u0438\u0447\u043d\u043e! \u0412\u044b \u043f\u0440\u043e\u0448\u043b\u0438!' } as LocaleString,
  quizFailed: { en: 'Not quite! Try again!', id: 'Belum tepat! Coba lagi!', ru: '\u041d\u0435 \u0441\u043e\u0432\u0441\u0435\u043c! \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0441\u043d\u043e\u0432\u0430!' } as LocaleString,
  score: { en: 'Score', id: 'Skor', ru: '\u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442' } as LocaleString,
  xpEarned: { en: 'XP earned', id: 'XP didapat', ru: 'XP \u043f\u043e\u043b\u0443\u0447\u0435\u043d\u043e' } as LocaleString,
  backToMenu: { en: 'Back to Menu', id: 'Kembali ke Menu', ru: '\u041a \u043c\u0435\u043d\u044e' } as LocaleString,
  achievements: { en: 'Achievements', id: 'Pencapaian', ru: '\u0414\u043e\u0441\u0442\u0438\u0436\u0435\u043d\u0438\u044f' } as LocaleString,
  locked: { en: 'Complete previous section first', id: 'Selesaikan bagian sebelumnya dulu', ru: '\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u0435 \u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 \u0440\u0430\u0437\u0434\u0435\u043b' } as LocaleString,
  allDone: { en: 'Congratulations! You completed the entire onboarding!', id: 'Selamat! Anda menyelesaikan seluruh onboarding!', ru: '\u041f\u043e\u0437\u0434\u0440\u0430\u0432\u043b\u044f\u0435\u043c! \u0412\u044b \u043f\u0440\u043e\u0448\u043b\u0438 \u0432\u0435\u0441\u044c \u043e\u043d\u0431\u043e\u0440\u0434\u0438\u043d\u0433!' } as LocaleString,
  quizBest: { en: 'Best score', id: 'Skor terbaik', ru: '\u041b\u0443\u0447\u0448\u0438\u0439 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442' } as LocaleString,
};


// ── Sub-components ───────────────────────────────────────────────

/** Circular progress ring */
function ProgressRing({ pct, size = 120, strokeWidth = 8, children }: {
  pct: number; size?: number; strokeWidth?: number; children?: React.ReactNode;
}) {
  const r = (size - strokeWidth) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke="currentColor" strokeWidth={strokeWidth}
          className="text-stone-200 dark:text-stone-800" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke="url(#onb-gradient)" strokeWidth={strokeWidth}
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out" />
        <defs>
          <linearGradient id="onb-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#d4a574" />
            <stop offset="100%" stopColor="#f59e0b" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {children}
      </div>
    </div>
  );
}

/** Animated XP counter with floating +XP effect */
function XPCounter({ xp, recentGain }: { xp: number; recentGain: number }) {
  const [showGain, setShowGain] = useState(false);
  const prevXp = useRef(xp);

  useEffect(() => {
    if (xp > prevXp.current && recentGain > 0) {
      setShowGain(true);
      const timer = setTimeout(() => setShowGain(false), 2000);
      prevXp.current = xp;
      return () => clearTimeout(timer);
    }
    prevXp.current = xp;
  }, [xp, recentGain]);

  return (
    <div className="relative">
      <span className="text-3xl font-bold bg-gradient-to-r from-amber-500 to-yellow-400 bg-clip-text text-transparent">
        {xp.toLocaleString()}
      </span>
      {showGain && (
        <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-lg font-bold text-amber-400 animate-float-up whitespace-nowrap">
          +{recentGain} XP
        </span>
      )}
    </div>
  );
}

/** Confetti-like celebration particles */
function CelebrationEffect({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden">
      {Array.from({ length: 40 }).map((_, i) => (
        <div key={i}
          className="absolute w-3 h-3 rounded-full animate-confetti"
          style={{
            left: `${Math.random() * 100}%`,
            backgroundColor: ['#d4a574', '#f59e0b', '#ef4444', '#10b981', '#6366f1', '#f97316'][i % 6],
            animationDelay: `${Math.random() * 0.5}s`,
            animationDuration: `${1.5 + Math.random() * 1.5}s`,
          }}
        />
      ))}
    </div>
  );
}

/** Section card for the overview grid */
function OnboardingCard({
  sectionId, content, progress, index, isUnlocked, lang, onClick,
}: {
  sectionId: string; content: SectionContent; progress: SectionProgress | undefined;
  index: number; isUnlocked: boolean; lang: Lang; onClick: () => void;
}) {
  const isDone = progress?.completed;
  const hasQuiz = (progress?.quiz_score ?? -1) >= 0;
  const quizPassed = (progress?.quiz_score ?? 0) >= 80;

  return (
    <button
      onClick={isUnlocked ? onClick : undefined}
      disabled={!isUnlocked}
      className={`group relative text-left w-full rounded-2xl p-5 transition-all duration-300
        ${isUnlocked
          ? 'cursor-pointer hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]'
          : 'cursor-not-allowed opacity-50'}
        ${isDone
          ? 'bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/30 border-2 border-amber-300/50 dark:border-amber-700/50'
          : 'bg-[var(--bg-card)] border border-[var(--border)]'}
        shadow-[var(--shadow)]`}
    >
      {/* Section number badge */}
      <div className={`absolute -top-3 -left-2 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
        ${isDone ? 'bg-gradient-to-br from-amber-400 to-orange-500 text-white' : 'bg-stone-200 dark:bg-stone-700 text-stone-600 dark:text-stone-300'}`}>
        {isDone ? '✓' : index + 1}
      </div>

      {/* Lock icon */}
      {!isUnlocked && (
        <div className="absolute top-3 right-3 text-stone-400 dark:text-stone-600 text-lg">🔒</div>
      )}

      {/* Icon */}
      <div className="text-3xl mb-3">{content.icon || SECTION_ICONS[sectionId]}</div>

      {/* Title */}
      <h3 className="font-semibold text-[var(--text-primary)] mb-1 pr-6">
        {t(content.title, lang)}
      </h3>

      {/* Progress indicators */}
      <div className="flex items-center gap-2 mt-3 text-xs">
        {isDone && (
          <span className="px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400 font-medium">
            +{progress?.xp_earned ?? 0} XP
          </span>
        )}
        {hasQuiz && (
          <span className={`px-2 py-0.5 rounded-full font-medium
            ${quizPassed
              ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400'
              : 'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400'}`}>
            {progress?.quiz_score}%
          </span>
        )}
        {!isDone && isUnlocked && (
          <span className="text-[var(--text-muted)]">{content.slides.length} slides + quiz</span>
        )}
      </div>

      {/* Hover glow */}
      {isUnlocked && (
        <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-br from-amber-400/5 to-orange-400/5 pointer-events-none" />
      )}
    </button>
  );
}

/** Content slide viewer */
function OnboardingSlide({
  content, slideIndex, totalSlides, lang, onPrev, onNext, onFinish, isLast,
}: {
  content: SectionContent; slideIndex: number; totalSlides: number; lang: Lang;
  onPrev: () => void; onNext: () => void; onFinish: () => void; isLast: boolean;
}) {
  const slide = content.slides[slideIndex];
  if (!slide) return null;

  return (
    <div className="animate-fadeIn">
      {/* Progress dots */}
      <div className="flex items-center justify-center gap-2 mb-6">
        {content.slides.map((_, i) => (
          <div key={i} className={`h-2 rounded-full transition-all duration-300
            ${i === slideIndex ? 'w-8 bg-gradient-to-r from-amber-400 to-orange-500' : 'w-2 bg-stone-300 dark:bg-stone-700'}
            ${i < slideIndex ? 'bg-amber-300 dark:bg-amber-700' : ''}`} />
        ))}
      </div>

      {/* Slide content */}
      <div className="bg-[var(--bg-card)] rounded-2xl p-8 border border-[var(--border)] shadow-[var(--shadow)] max-w-2xl mx-auto">
        <div className="text-center mb-6">
          <span className="text-5xl block mb-4">{slide.icon}</span>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">
            {t(slide.title, lang)}
          </h2>
        </div>

        <p className="text-[var(--text-secondary)] leading-relaxed text-lg whitespace-pre-line">
          {t(slide.content, lang)}
        </p>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-8 max-w-2xl mx-auto">
        <button
          onClick={onPrev}
          disabled={slideIndex === 0}
          className="px-6 py-2.5 rounded-xl font-medium transition-all
            disabled:opacity-30 disabled:cursor-not-allowed
            text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-stone-100 dark:hover:bg-stone-800"
        >
          {t(MESSAGES.prev, lang)}
        </button>

        <span className="text-sm text-[var(--text-muted)]">
          {slideIndex + 1} / {totalSlides}
        </span>

        {isLast ? (
          <button
            onClick={onFinish}
            className="px-6 py-2.5 rounded-xl font-semibold text-white
              bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600
              shadow-md hover:shadow-lg transition-all active:scale-95"
          >
            {t(MESSAGES.finishReading, lang)}
          </button>
        ) : (
          <button
            onClick={onNext}
            className="px-6 py-2.5 rounded-xl font-semibold text-white
              bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600
              shadow-md hover:shadow-lg transition-all active:scale-95"
          >
            {t(MESSAGES.next, lang)}
          </button>
        )}
      </div>
    </div>
  );
}

/** Quiz component */
function OnboardingQuiz({
  questions, lang, onSubmit, isSubmitting, result, onRetake, onBack,
}: {
  questions: QuizQuestion[]; lang: Lang;
  onSubmit: (answers: Record<string, string>) => void; isSubmitting: boolean;
  result: QuizResult | null; onRetake: () => void; onBack: () => void;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const allAnswered = questions.every((q) => answers[q.id]);

  if (result) {
    return (
      <div className="animate-fadeIn max-w-2xl mx-auto">
        <div className={`rounded-2xl p-8 text-center border-2
          ${result.passed
            ? 'bg-gradient-to-br from-emerald-50 to-amber-50 dark:from-emerald-950/30 dark:to-amber-950/30 border-emerald-300 dark:border-emerald-700'
            : 'bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-950/30 dark:to-orange-950/30 border-red-300 dark:border-red-700'}`}
        >
          <div className="text-6xl mb-4">{result.passed ? '🎉' : '💪'}</div>
          <h2 className="text-2xl font-bold mb-2 text-[var(--text-primary)]">
            {result.passed ? t(MESSAGES.quizPassed, lang) : t(MESSAGES.quizFailed, lang)}
          </h2>
          <div className="text-4xl font-bold my-4 bg-gradient-to-r from-amber-500 to-orange-500 bg-clip-text text-transparent">
            {result.score}%
          </div>
          {result.xp_awarded > 0 && (
            <div className="inline-block px-4 py-2 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 font-semibold text-lg mb-4">
              +{result.xp_awarded} XP
            </div>
          )}

          {/* Show correct answers for wrong ones */}
          <div className="mt-6 space-y-3 text-left">
            {questions.map((q) => {
              const userAnswer = answers[q.id];
              const correctAnswer = result.correct_answers[q.id];
              const isCorrect = userAnswer === correctAnswer;
              return (
                <div key={q.id} className={`p-3 rounded-xl border ${isCorrect ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-950/20' : 'border-red-300 dark:border-red-700 bg-red-50/50 dark:bg-red-950/20'}`}>
                  <div className="flex items-start gap-2">
                    <span className="text-lg mt-0.5">{isCorrect ? '✅' : '❌'}</span>
                    <div>
                      <p className="font-medium text-sm text-[var(--text-primary)]">{t(q.question, lang)}</p>
                      {!isCorrect && (
                        <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                          {t(q.options.find(o => o.value === correctAnswer)?.label, lang)}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex gap-3 justify-center mt-6">
            <button onClick={onBack}
              className="px-6 py-2.5 rounded-xl font-medium text-[var(--text-secondary)] hover:bg-stone-100 dark:hover:bg-stone-800 transition-all">
              {t(MESSAGES.backToMenu, lang)}
            </button>
            {!result.passed && (
              <button onClick={onRetake}
                className="px-6 py-2.5 rounded-xl font-semibold text-white bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 shadow-md transition-all active:scale-95">
                {t(MESSAGES.retakeQuiz, lang)}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn max-w-2xl mx-auto space-y-6">
      {questions.map((q, qi) => (
        <div key={q.id} className="bg-[var(--bg-card)] rounded-2xl p-6 border border-[var(--border)] shadow-[var(--shadow)]">
          <p className="font-semibold text-[var(--text-primary)] mb-4">
            <span className="inline-block w-7 h-7 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 text-white text-sm font-bold text-center leading-7 mr-2">
              {qi + 1}
            </span>
            {t(q.question, lang)}
          </p>
          <div className="space-y-2">
            {q.options.map((opt) => (
              <label key={opt.value}
                className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all border
                  ${answers[q.id] === opt.value
                    ? 'border-amber-400 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-600'
                    : 'border-transparent hover:bg-stone-50 dark:hover:bg-stone-800/50'}`}
              >
                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all
                  ${answers[q.id] === opt.value ? 'border-amber-500 bg-amber-500' : 'border-stone-300 dark:border-stone-600'}`}>
                  {answers[q.id] === opt.value && (
                    <div className="w-2 h-2 rounded-full bg-white" />
                  )}
                </div>
                <span className="text-[var(--text-primary)]">{t(opt.label, lang)}</span>
              </label>
            ))}
          </div>
        </div>
      ))}

      <div className="flex items-center justify-between">
        <button onClick={onBack}
          className="px-6 py-2.5 rounded-xl font-medium text-[var(--text-secondary)] hover:bg-stone-100 dark:hover:bg-stone-800 transition-all">
          {t(MESSAGES.backToMenu, lang)}
        </button>
        <button
          onClick={() => onSubmit(answers)}
          disabled={!allAnswered || isSubmitting}
          className="px-8 py-3 rounded-xl font-semibold text-white
            bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600
            disabled:opacity-40 disabled:cursor-not-allowed
            shadow-md hover:shadow-lg transition-all active:scale-95"
        >
          {isSubmitting ? <Spinner className="h-5 w-5" /> : t(MESSAGES.submitQuiz, lang)}
        </button>
      </div>
    </div>
  );
}


// ── Main Page ────────────────────────────────────────────────────

type ViewState =
  | { mode: 'overview' }
  | { mode: 'slides'; sectionId: string; slideIndex: number }
  | { mode: 'quiz'; sectionId: string };

export default function OnboardingPage({ role = 'production_manager' }: { role?: string }) {
  const user = useAuthStore((s) => s.user);
  const lang = getLang(user);
  const roleTitle = ROLE_TITLES[role] || ROLE_TITLES.production_manager;

  const { data: progress, isLoading: loadingProgress } = useOnboardingProgress(role);
  const { data: contentData, isLoading: loadingContent } = useOnboardingContent(lang, role);
  const completeSection = useCompleteSection(role);
  const submitQuiz = useSubmitQuiz(role);

  const [view, setView] = useState<ViewState>({ mode: 'overview' });
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [recentXpGain, setRecentXpGain] = useState(0);
  const [celebrating, setCelebrating] = useState(false);

  // Map section progress by id
  const progressMap = useMemo(() => {
    const map: Record<string, SectionProgress> = {};
    progress?.sections.forEach((s) => { map[s.section_id] = s; });
    return map;
  }, [progress]);

  // Check if section is unlocked (first section always unlocked, rest require prev completed)
  const isSectionUnlocked = useCallback((sectionId: string, index: number) => {
    if (index === 0) return true;
    const sections = contentData?.sections ?? [];
    const prevId = sections[index - 1];
    return prevId ? (progressMap[prevId]?.completed ?? false) : false;
  }, [contentData, progressMap]);

  // Trigger celebration
  const celebrate = useCallback(() => {
    setCelebrating(true);
    setTimeout(() => setCelebrating(false), 3000);
  }, []);

  // Handlers
  const handleOpenSection = useCallback((sectionId: string) => {
    const sp = progressMap[sectionId];
    if (sp?.completed) {
      // Already completed, go to quiz or slides
      setView({ mode: 'slides', sectionId, slideIndex: 0 });
    } else {
      setView({ mode: 'slides', sectionId, slideIndex: 0 });
    }
    setQuizResult(null);
  }, [progressMap]);

  const handleFinishReading = useCallback(async (sectionId: string) => {
    const sp = progressMap[sectionId];
    if (!sp?.completed) {
      await completeSection.mutateAsync(sectionId);
      setRecentXpGain(50);
      celebrate();
    }
    setView({ mode: 'quiz', sectionId });
    setQuizResult(null);
  }, [progressMap, completeSection, celebrate]);

  const handleSubmitQuiz = useCallback(async (sectionId: string, answers: Record<string, string>) => {
    const result = await submitQuiz.mutateAsync({ sectionId, answers });
    setQuizResult(result);
    if (result.xp_awarded > 0) {
      setRecentXpGain(result.xp_awarded);
    }
    if (result.passed) {
      celebrate();
    }
  }, [submitQuiz, celebrate]);

  const handleRetakeQuiz = useCallback(() => {
    setQuizResult(null);
  }, []);

  const handleBackToMenu = useCallback(() => {
    setView({ mode: 'overview' });
    setQuizResult(null);
  }, []);

  // Loading
  if (loadingProgress || loadingContent) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-10 w-10" />
      </div>
    );
  }

  if (!progress || !contentData) return null;

  const sections = contentData.sections;
  const content = contentData.content;
  const totalXp = progress.total_xp;
  const earnedAchievements = ACHIEVEMENT_THRESHOLDS.filter((a) => totalXp >= a.xp);

  // ── SLIDE VIEW ─────────────────────────────────────────────────
  if (view.mode === 'slides') {
    const sc = content[view.sectionId];
    if (!sc) return null;

    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <CelebrationEffect active={celebrating} />
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <button onClick={handleBackToMenu}
            className="p-2 rounded-xl hover:bg-stone-100 dark:hover:bg-stone-800 transition-all text-[var(--text-secondary)]">
            ←
          </button>
          <span className="text-2xl">{sc.icon}</span>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">{t(sc.title, lang)}</h1>
        </div>

        <OnboardingSlide
          content={sc}
          slideIndex={view.slideIndex}
          totalSlides={sc.slides.length}
          lang={lang}
          onPrev={() => setView({ ...view, slideIndex: Math.max(0, view.slideIndex - 1) })}
          onNext={() => setView({ ...view, slideIndex: Math.min(sc.slides.length - 1, view.slideIndex + 1) })}
          onFinish={() => handleFinishReading(view.sectionId)}
          isLast={view.slideIndex === sc.slides.length - 1}
        />
      </div>
    );
  }

  // ── QUIZ VIEW ──────────────────────────────────────────────────
  if (view.mode === 'quiz') {
    const sc = content[view.sectionId];
    if (!sc) return null;

    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <CelebrationEffect active={celebrating} />
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <button onClick={handleBackToMenu}
            className="p-2 rounded-xl hover:bg-stone-100 dark:hover:bg-stone-800 transition-all text-[var(--text-secondary)]">
            ←
          </button>
          <span className="text-2xl">{sc.icon}</span>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">{t(sc.title, lang)} - Quiz</h1>
        </div>

        <OnboardingQuiz
          questions={sc.quiz}
          lang={lang}
          onSubmit={(answers) => handleSubmitQuiz(view.sectionId, answers)}
          isSubmitting={submitQuiz.isPending}
          result={quizResult}
          onRetake={handleRetakeQuiz}
          onBack={handleBackToMenu}
        />
      </div>
    );
  }

  // ── OVERVIEW ───────────────────────────────────────────────────
  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <CelebrationEffect active={celebrating} />

      {/* Hero section */}
      <div className="relative rounded-3xl bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 dark:from-amber-950/40 dark:via-orange-950/30 dark:to-yellow-950/20 border border-amber-200/50 dark:border-amber-800/30 p-8 mb-10 overflow-hidden">
        {/* Decorative background elements */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-amber-200/20 to-transparent rounded-full -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-orange-200/20 to-transparent rounded-full translate-y-1/3 -translate-x-1/4" />

        <div className="relative flex flex-col md:flex-row items-center gap-8">
          {/* Progress Ring */}
          <ProgressRing pct={progress.pct_complete} size={140} strokeWidth={10}>
            <span className="text-3xl font-bold text-[var(--text-primary)]">{progress.pct_complete}%</span>
          </ProgressRing>

          {/* Info */}
          <div className="flex-1 text-center md:text-left">
            <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">
              {t(roleTitle.title, lang)}
            </h1>
            <p className="text-[var(--text-secondary)] mb-4">
              {t(roleTitle.subtitle, lang)}
            </p>
            <div className="flex flex-wrap items-center gap-6 justify-center md:justify-start">
              <div>
                <div className="text-xs uppercase tracking-wider text-[var(--text-muted)] mb-1">{t(MESSAGES.totalXp, lang)}</div>
                <XPCounter xp={totalXp} recentGain={recentXpGain} />
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-[var(--text-muted)] mb-1">{t(MESSAGES.sections, lang)}</div>
                <div className="text-2xl font-bold text-[var(--text-primary)]">
                  {progress.completed_count}/{progress.total_sections}
                  <span className="text-sm font-normal text-[var(--text-muted)] ml-1">{t(MESSAGES.completed, lang)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* All done banner */}
        {progress.pct_complete === 100 && (
          <div className="mt-6 p-4 rounded-2xl bg-gradient-to-r from-emerald-100 to-amber-100 dark:from-emerald-900/30 dark:to-amber-900/30 border border-emerald-200 dark:border-emerald-800 text-center">
            <span className="text-2xl mr-2">👑</span>
            <span className="font-bold text-emerald-700 dark:text-emerald-400">{t(MESSAGES.allDone, lang)}</span>
          </div>
        )}
      </div>

      {/* Achievements row */}
      {ACHIEVEMENT_THRESHOLDS.length > 0 && (
        <div className="mb-10">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
            {t(MESSAGES.achievements, lang)}
          </h2>
          <div className="flex flex-wrap gap-3">
            {ACHIEVEMENT_THRESHOLDS.map((ach) => {
              const earned = totalXp >= ach.xp;
              return (
                <div key={ach.xp}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full border transition-all
                    ${earned
                      ? 'bg-gradient-to-r from-amber-50 to-yellow-50 dark:from-amber-950/30 dark:to-yellow-950/30 border-amber-300 dark:border-amber-700 shadow-sm'
                      : 'bg-stone-50 dark:bg-stone-900/50 border-stone-200 dark:border-stone-800 opacity-40'}`}
                >
                  <span className="text-xl">{ach.icon}</span>
                  <div>
                    <span className={`text-sm font-semibold ${earned ? 'text-amber-700 dark:text-amber-400' : 'text-[var(--text-muted)]'}`}>
                      {t(ach.label, lang)}
                    </span>
                    <span className="text-xs text-[var(--text-muted)] ml-1">({ach.xp} XP)</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Section grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {sections.map((sid, idx) => (
          <OnboardingCard
            key={sid}
            sectionId={sid}
            content={content[sid]}
            progress={progressMap[sid]}
            index={idx}
            isUnlocked={isSectionUnlocked(sid, idx)}
            lang={lang}
            onClick={() => handleOpenSection(sid)}
          />
        ))}
      </div>
    </div>
  );
}
