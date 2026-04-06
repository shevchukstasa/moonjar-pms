import apiClient from './client';

// ── Types ────────────────────────────────────────────────────────

export interface SkillBadge {
  id: string;
  code: string;
  name: string;
  name_id: string | null;
  category: string;
  icon: string | null;
  description: string | null;
  required_operations: number;
  required_zero_defect_pct: number;
  required_mentor_approval: boolean;
  points_on_earn: number;
  operation_id: string | null;
}

export interface UserSkill {
  id: string;
  user_id: string;
  skill_badge_id: string;
  skill_badge: SkillBadge;
  status: 'learning' | 'pending_certification' | 'certified' | 'revoked';
  operations_completed: number;
  zero_defect_pct: number;
  started_at: string;
  certified_at: string | null;
  certified_by: string | null;
  points_earned: number;
}

export interface Competition {
  id: string;
  title: string;
  title_id: string | null;
  competition_type: 'individual' | 'team';
  metric: string;
  scoring_formula: string;
  quality_weight: number;
  start_date: string;
  end_date: string;
  status: 'proposed' | 'upcoming' | 'active' | 'completed' | 'cancelled';
  prize_description: string | null;
  prize_budget_idr: number | null;
  created_by: string | null;
  team_type?: string;
}

export interface CompetitionStanding {
  rank: number;
  user_id: string;
  user_name: string;
  score: number;
  quality_score: number;
  speed_score: number;
  streak_days: number;
  team_name?: string;
}

export interface Prize {
  id: string;
  user_id: string;
  user_name: string;
  prize_type: string;
  description: string;
  amount_idr: number | null;
  status: 'pending' | 'approved' | 'rejected' | 'awarded';
  reason: string | null;
  month: string;
  created_at: string;
  approved_by: string | null;
}

export interface Season {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: string;
  final_standings: unknown;
  prizes_awarded: unknown;
}

export interface CeoDashboardData {
  total_points_this_month: number;
  active_users: number;
  top_performers: { user_id: string; user_name: string; points: number }[];
  active_competitions: number;
  skills_certified_this_month: number;
  engagement_rate: number;
  monthly_trend: { month: string; points: number; users: number }[];
}

export interface ProductivityImpact {
  before_gamification: { avg_quality: number; avg_speed: number; defect_rate: number };
  after_gamification: { avg_quality: number; avg_speed: number; defect_rate: number };
  improvement_pct: { quality: number; speed: number; defect_reduction: number };
  roi_estimate: number;
}

export interface CompetitionCreatePayload {
  title: string;
  title_id?: string;
  competition_type?: string;
  metric?: string;
  scoring_formula?: string;
  quality_weight?: number;
  start_date: string;
  end_date: string;
  prize_description?: string;
  prize_budget_idr?: number;
}

export interface TeamCompetitionCreatePayload extends CompetitionCreatePayload {
  team_type?: string;
  teams?: Record<string, unknown>[];
}

export interface ProposePayload {
  title: string;
  title_id?: string;
  metric?: string;
  start_date: string;
  end_date: string;
}

// ── API ──────────────────────────────────────────────────────────

export const gamificationApi = {
  // Skills
  listSkillBadges: (factoryId: string) =>
    apiClient.get<SkillBadge[]>('/gamification/skills/badges', { params: { factory_id: factoryId } }).then((r) => r.data),

  seedSkillBadges: (factoryId: string) =>
    apiClient.post('/gamification/skills/badges/seed', null, { params: { factory_id: factoryId } }).then((r) => r.data),

  getUserSkills: (userId: string, factoryId: string) =>
    apiClient.get<UserSkill[]>(`/gamification/skills/user/${userId}`, { params: { factory_id: factoryId } }).then((r) => r.data),

  startSkill: (skillBadgeId: string) =>
    apiClient.post('/gamification/skills/start', { skill_badge_id: skillBadgeId }).then((r) => r.data),

  certifySkill: (userSkillId: string) =>
    apiClient.post('/gamification/skills/certify', { user_skill_id: userSkillId }).then((r) => r.data),

  revokeSkill: (userSkillId: string) =>
    apiClient.post('/gamification/skills/revoke', { user_skill_id: userSkillId }).then((r) => r.data),

  // Competitions
  listCompetitions: (factoryId: string, status?: string) =>
    apiClient.get<Competition[]>('/gamification/competitions', { params: { factory_id: factoryId, status } }).then((r) => r.data),

  getStandings: (competitionId: string) =>
    apiClient.get<CompetitionStanding[]>(`/gamification/competitions/${competitionId}/standings`).then((r) => r.data),

  createCompetition: (factoryId: string, data: CompetitionCreatePayload) =>
    apiClient.post('/gamification/competitions', data, { params: { factory_id: factoryId } }).then((r) => r.data),

  createTeamCompetition: (factoryId: string, data: TeamCompetitionCreatePayload) =>
    apiClient.post('/gamification/competitions/team', data, { params: { factory_id: factoryId } }).then((r) => r.data),

  proposeChallenge: (factoryId: string, data: ProposePayload) =>
    apiClient.post('/gamification/competitions/propose', data, { params: { factory_id: factoryId } }).then((r) => r.data),

  approveCompetition: (competitionId: string) =>
    apiClient.post(`/gamification/competitions/${competitionId}/approve`).then((r) => r.data),

  updateScores: (factoryId: string) =>
    apiClient.post('/gamification/competitions/update-scores', null, { params: { factory_id: factoryId } }).then((r) => r.data),

  // Prizes
  listPrizes: (factoryId: string, status?: string) =>
    apiClient.get<Prize[]>('/gamification/prizes', { params: { factory_id: factoryId, status } }).then((r) => r.data),

  generateMonthlyPrizes: (factoryId: string) =>
    apiClient.post('/gamification/prizes/generate-monthly', null, { params: { factory_id: factoryId } }).then((r) => r.data),

  approvePrize: (prizeId: string) =>
    apiClient.post(`/gamification/prizes/${prizeId}/approve`).then((r) => r.data),

  rejectPrize: (prizeId: string) =>
    apiClient.post(`/gamification/prizes/${prizeId}/reject`).then((r) => r.data),

  awardPrize: (prizeId: string) =>
    apiClient.post(`/gamification/prizes/${prizeId}/award`).then((r) => r.data),

  // CEO Dashboard
  ceoDashboard: (factoryId: string) =>
    apiClient.get<CeoDashboardData>('/gamification/ceo-dashboard', { params: { factory_id: factoryId } }).then((r) => r.data),

  productivityImpact: (factoryId: string) =>
    apiClient.get<ProductivityImpact>('/gamification/ceo-dashboard/impact', { params: { factory_id: factoryId } }).then((r) => r.data),

  sendCeoReport: (factoryId: string) =>
    apiClient.post('/gamification/ceo-dashboard/send-report', null, { params: { factory_id: factoryId } }).then((r) => r.data),

  // Seasons
  listSeasons: (factoryId: string) =>
    apiClient.get<Season[]>('/gamification/seasons', { params: { factory_id: factoryId } }).then((r) => r.data),
};
