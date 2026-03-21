import apiClient from './client';

export interface CalendarEntry {
  id: string;
  factory_id: string;
  factory_name: string | null;
  date: string;
  is_working_day: boolean;
  num_shifts: number;
  holiday_name: string | null;
  holiday_source: string | null;
  approved_by: string | null;
  approved_at: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface CalendarListResponse {
  items: CalendarEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface WorkingDaysResponse {
  factory_id: string;
  start_date: string;
  end_date: string;
  total_days: number;
  working_days: number;
  holidays: number;
  sundays: number;
}

export interface CalendarCreatePayload {
  factory_id: string;
  date: string;
  is_working_day?: boolean;
  num_shifts?: number;
  holiday_name?: string | null;
  holiday_source?: string | null;
  notes?: string | null;
}

export interface CalendarBulkPayload {
  factory_id: string;
  entries: CalendarCreatePayload[];
}

export interface BulkCreateResponse {
  created: CalendarEntry[];
  skipped: { date: string; reason: string }[];
  total_created: number;
  total_skipped: number;
}

export const factoryCalendarApi = {
  list: (factoryId: string, year: number, month: number): Promise<CalendarListResponse> =>
    apiClient
      .get('/factory-calendar', { params: { factory_id: factoryId, year, month, per_page: 100 } })
      .then((r) => r.data),

  workingDays: (factoryId: string, startDate: string, endDate: string): Promise<WorkingDaysResponse> =>
    apiClient
      .get('/factory-calendar/working-days', {
        params: { factory_id: factoryId, start_date: startDate, end_date: endDate },
      })
      .then((r) => r.data),

  create: (data: CalendarCreatePayload): Promise<CalendarEntry> =>
    apiClient.post('/factory-calendar', data).then((r) => r.data),

  bulkCreate: (data: CalendarBulkPayload): Promise<BulkCreateResponse> =>
    apiClient.post('/factory-calendar/bulk', data).then((r) => r.data),

  remove: (entryId: string): Promise<void> =>
    apiClient.delete(`/factory-calendar/${entryId}`).then(() => undefined),
};
