import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  onboardingApi,
  type OnboardingOverview,
  type OnboardingContentResponse,
  type QuizResult,
  type SectionProgress,
} from '@/api/onboarding';

const KEYS = {
  progress: (role?: string) => ['onboarding', 'progress', role ?? 'default'],
  content: (lang: string, role?: string) => ['onboarding', 'content', lang, role ?? 'default'],
};

export function useOnboardingProgress(role?: string) {
  return useQuery<OnboardingOverview>({
    queryKey: KEYS.progress(role),
    queryFn: () => onboardingApi.getProgress(role),
  });
}

export function useOnboardingContent(lang: string, role?: string) {
  return useQuery<OnboardingContentResponse>({
    queryKey: KEYS.content(lang, role),
    queryFn: () => onboardingApi.getContent(lang, role),
    staleTime: 60 * 60 * 1000, // content rarely changes
  });
}

export function useCompleteSection(role?: string) {
  const qc = useQueryClient();
  return useMutation<SectionProgress, Error, string>({
    mutationFn: (sectionId) => onboardingApi.completeSection(sectionId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.progress(role) }),
  });
}

export function useSubmitQuiz(role?: string) {
  const qc = useQueryClient();
  return useMutation<
    QuizResult,
    Error,
    { sectionId: string; answers: Record<string, string> }
  >({
    mutationFn: ({ sectionId, answers }) =>
      onboardingApi.submitQuiz(sectionId, answers, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.progress(role) }),
  });
}
