import apiClient from './client';

export interface SectionProgress {
  section_id: string;
  completed: boolean;
  quiz_score: number | null;
  quiz_attempts: number;
  xp_earned: number;
  completed_at: string | null;
}

export interface OnboardingOverview {
  sections: SectionProgress[];
  total_xp: number;
  completed_count: number;
  total_sections: number;
  pct_complete: number;
}

export interface QuizResult {
  score: number;
  passed: boolean;
  xp_awarded: number;
  correct_answers: Record<string, string>;
}

export interface LocaleString {
  en: string;
  id: string;
  ru: string;
}

export interface QuizOption {
  value: string;
  label: LocaleString;
}

export interface QuizQuestion {
  id: string;
  question: LocaleString;
  options: QuizOption[];
}

export interface ContentSlide {
  title: LocaleString;
  content: LocaleString;
  icon: string;
}

export interface SectionContent {
  icon: string;
  title: LocaleString;
  slides: ContentSlide[];
  quiz: QuizQuestion[];
}

export interface OnboardingContentResponse {
  sections: string[];
  content: Record<string, SectionContent>;
  xp_section_read: number;
  xp_quiz_pass: number;
  quiz_pass_threshold: number;
}

export const onboardingApi = {
  getProgress: async (): Promise<OnboardingOverview> => {
    const { data } = await apiClient.get('/onboarding/progress');
    return data;
  },

  completeSection: async (sectionId: string): Promise<SectionProgress> => {
    const { data } = await apiClient.post('/onboarding/complete-section', {
      section_id: sectionId,
    });
    return data;
  },

  submitQuiz: async (
    sectionId: string,
    answers: Record<string, string>,
  ): Promise<QuizResult> => {
    const { data } = await apiClient.post('/onboarding/submit-quiz', {
      section_id: sectionId,
      answers,
    });
    return data;
  },

  getContent: async (lang: string): Promise<OnboardingContentResponse> => {
    const { data } = await apiClient.get(`/onboarding/content/${lang}`);
    return data;
  },
};
