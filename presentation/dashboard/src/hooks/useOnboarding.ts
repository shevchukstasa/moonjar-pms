import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  onboardingApi,
  type OnboardingOverview,
  type OnboardingContentResponse,
  type QuizResult,
  type SectionProgress,
} from '@/api/onboarding';

const KEYS = {
  progress: ['onboarding', 'progress'],
  content: (lang: string) => ['onboarding', 'content', lang],
};

export function useOnboardingProgress() {
  return useQuery<OnboardingOverview>({
    queryKey: KEYS.progress,
    queryFn: onboardingApi.getProgress,
  });
}

export function useOnboardingContent(lang: string) {
  return useQuery<OnboardingContentResponse>({
    queryKey: KEYS.content(lang),
    queryFn: () => onboardingApi.getContent(lang),
    staleTime: 60 * 60 * 1000, // content rarely changes
  });
}

export function useCompleteSection() {
  const qc = useQueryClient();
  return useMutation<SectionProgress, Error, string>({
    mutationFn: (sectionId) => onboardingApi.completeSection(sectionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.progress }),
  });
}

export function useSubmitQuiz() {
  const qc = useQueryClient();
  return useMutation<
    QuizResult,
    Error,
    { sectionId: string; answers: Record<string, string> }
  >({
    mutationFn: ({ sectionId, answers }) =>
      onboardingApi.submitQuiz(sectionId, answers),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.progress }),
  });
}
