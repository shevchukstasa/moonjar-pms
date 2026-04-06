import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  gamificationApi,
  type SkillBadge,
  type UserSkill,
  type Competition,
  type CompetitionStanding,
  type Prize,
  type Season,
  type CeoDashboardData,
  type ProductivityImpact,
  type CompetitionCreatePayload,
  type TeamCompetitionCreatePayload,
  type ProposePayload,
} from '@/api/gamification';

const KEYS = {
  skillBadges: (fid: string) => ['gamification', 'skill-badges', fid],
  userSkills: (uid: string, fid: string) => ['gamification', 'user-skills', uid, fid],
  competitions: (fid: string, status?: string) => ['gamification', 'competitions', fid, status],
  standings: (cid: string) => ['gamification', 'standings', cid],
  prizes: (fid: string, status?: string) => ['gamification', 'prizes', fid, status],
  ceoDashboard: (fid: string) => ['gamification', 'ceo-dashboard', fid],
  impact: (fid: string) => ['gamification', 'impact', fid],
  seasons: (fid: string) => ['gamification', 'seasons', fid],
};

// ── Skills ────────────────────────────────────────────────────────

export function useSkillBadges(factoryId?: string) {
  return useQuery<SkillBadge[]>({
    queryKey: KEYS.skillBadges(factoryId!),
    queryFn: () => gamificationApi.listSkillBadges(factoryId!),
    enabled: !!factoryId,
  });
}

export function useUserSkills(userId?: string, factoryId?: string) {
  return useQuery<UserSkill[]>({
    queryKey: KEYS.userSkills(userId!, factoryId!),
    queryFn: () => gamificationApi.getUserSkills(userId!, factoryId!),
    enabled: !!userId && !!factoryId,
  });
}

export function useSeedSkillBadges() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (factoryId: string) => gamificationApi.seedSkillBadges(factoryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'skill-badges'] }),
  });
}

export function useStartSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (skillBadgeId: string) => gamificationApi.startSkill(skillBadgeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'user-skills'] }),
  });
}

export function useCertifySkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userSkillId: string) => gamificationApi.certifySkill(userSkillId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'user-skills'] }),
  });
}

export function useRevokeSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userSkillId: string) => gamificationApi.revokeSkill(userSkillId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'user-skills'] }),
  });
}

// ── Competitions ──────────────────────────────────────────────────

export function useCompetitions(factoryId?: string, status?: string) {
  return useQuery<Competition[]>({
    queryKey: KEYS.competitions(factoryId!, status),
    queryFn: () => gamificationApi.listCompetitions(factoryId!, status),
    enabled: !!factoryId,
  });
}

export function useCompetitionStandings(competitionId?: string) {
  return useQuery<CompetitionStanding[]>({
    queryKey: KEYS.standings(competitionId!),
    queryFn: () => gamificationApi.getStandings(competitionId!),
    enabled: !!competitionId,
  });
}

export function useCreateCompetition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ factoryId, data }: { factoryId: string; data: CompetitionCreatePayload }) =>
      gamificationApi.createCompetition(factoryId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'competitions'] }),
  });
}

export function useCreateTeamCompetition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ factoryId, data }: { factoryId: string; data: TeamCompetitionCreatePayload }) =>
      gamificationApi.createTeamCompetition(factoryId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'competitions'] }),
  });
}

export function useProposeChallenge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ factoryId, data }: { factoryId: string; data: ProposePayload }) =>
      gamificationApi.proposeChallenge(factoryId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'competitions'] }),
  });
}

export function useApproveCompetition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (competitionId: string) => gamificationApi.approveCompetition(competitionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'competitions'] }),
  });
}

export function useUpdateScores() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (factoryId: string) => gamificationApi.updateScores(factoryId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['gamification', 'competitions'] });
      qc.invalidateQueries({ queryKey: ['gamification', 'standings'] });
    },
  });
}

// ── Prizes ────────────────────────────────────────────────────────

export function usePrizes(factoryId?: string, status?: string) {
  return useQuery<Prize[]>({
    queryKey: KEYS.prizes(factoryId!, status),
    queryFn: () => gamificationApi.listPrizes(factoryId!, status),
    enabled: !!factoryId,
  });
}

export function useGenerateMonthlyPrizes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (factoryId: string) => gamificationApi.generateMonthlyPrizes(factoryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'prizes'] }),
  });
}

export function useApprovePrize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (prizeId: string) => gamificationApi.approvePrize(prizeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'prizes'] }),
  });
}

export function useRejectPrize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (prizeId: string) => gamificationApi.rejectPrize(prizeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'prizes'] }),
  });
}

export function useAwardPrize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (prizeId: string) => gamificationApi.awardPrize(prizeId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gamification', 'prizes'] }),
  });
}

// ── CEO Dashboard ─────────────────────────────────────────────────

export function useCeoDashboard(factoryId?: string) {
  return useQuery<CeoDashboardData>({
    queryKey: KEYS.ceoDashboard(factoryId!),
    queryFn: () => gamificationApi.ceoDashboard(factoryId!),
    enabled: !!factoryId,
  });
}

export function useProductivityImpact(factoryId?: string) {
  return useQuery<ProductivityImpact>({
    queryKey: KEYS.impact(factoryId!),
    queryFn: () => gamificationApi.productivityImpact(factoryId!),
    enabled: !!factoryId,
  });
}

export function useSendCeoReport() {
  return useMutation({
    mutationFn: (factoryId: string) => gamificationApi.sendCeoReport(factoryId),
  });
}

// ── Seasons ───────────────────────────────────────────────────────

export function useSeasons(factoryId?: string) {
  return useQuery<Season[]>({
    queryKey: KEYS.seasons(factoryId!),
    queryFn: () => gamificationApi.listSeasons(factoryId!),
    enabled: !!factoryId,
  });
}
