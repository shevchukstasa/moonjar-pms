import apiClient from './client';

// ── Types ──────────────────────────────────────────────────

export interface WorkerSkill {
  id: string;
  user_id: string;
  factory_id: string;
  stage: string;
  proficiency: 'trainee' | 'capable' | 'expert';
  certified_at: string | null;
  certified_by: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface ShiftDefinition {
  id: string;
  factory_id: string;
  name: string;
  name_id: string | null;
  start_time: string | null;
  end_time: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface ShiftAssignment {
  id: string;
  factory_id: string;
  user_id: string;
  shift_definition_id: string;
  date: string;
  stage: string;
  is_lead: boolean;
  assigned_by: string | null;
  created_at: string | null;
}

export interface DailyCapacity {
  factory_id: string;
  date: string;
  total_workers: number;
  stages: Record<string, { workers: number; leads: number; user_ids: string[] }>;
}

export interface ShiftAssignmentCreate {
  factory_id: string;
  user_id: string;
  shift_definition_id: string;
  date: string;
  stage: string;
  is_lead?: boolean;
}

export interface ShiftDefinitionCreate {
  factory_id: string;
  name: string;
  name_id?: string;
  start_time: string;
  end_time: string;
}

// ── API ────────────────────────────────────────────────────

export const workforceApi = {
  // Skills
  listSkills: (factoryId: string, stage?: string): Promise<WorkerSkill[]> =>
    apiClient
      .get('/workforce/skills', { params: { factory_id: factoryId, ...(stage ? { stage } : {}) } })
      .then((r) => r.data),

  createSkill: (data: { user_id: string; factory_id: string; stage: string; proficiency: string; notes?: string }) =>
    apiClient.post('/workforce/skills', data).then((r) => r.data),

  // Shifts
  listShifts: (factoryId: string): Promise<ShiftDefinition[]> =>
    apiClient
      .get('/workforce/shifts', { params: { factory_id: factoryId } })
      .then((r) => r.data),

  createShift: (data: ShiftDefinitionCreate): Promise<ShiftDefinition> =>
    apiClient.post('/workforce/shifts', data).then((r) => r.data),

  // Assignments
  listAssignments: (factoryId: string, date: string): Promise<ShiftAssignment[]> =>
    apiClient
      .get('/workforce/assignments', { params: { factory_id: factoryId, date } })
      .then((r) => r.data),

  createAssignment: (data: ShiftAssignmentCreate) =>
    apiClient.post('/workforce/assignments', data).then((r) => r.data),

  deleteAssignment: (assignmentId: string): Promise<void> =>
    apiClient.delete(`/workforce/assignments/${assignmentId}`).then(() => undefined),

  // Daily capacity
  getDailyCapacity: (factoryId: string, date: string): Promise<DailyCapacity> =>
    apiClient
      .get('/workforce/daily-capacity', { params: { factory_id: factoryId, date } })
      .then((r) => r.data),
};
