import apiClient from './client';

export interface ProductionStage {
  id: string;
  name: string;
  order: number;
}

export interface ProductionStageForm {
  name: string;
  order: number;
}

export const stagesApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/stages', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/stages/${id}`).then((r) => r.data),
  create: (data: ProductionStageForm) =>
    apiClient.post('/stages', data).then((r) => r.data),
  update: (id: string, data: Partial<ProductionStageForm>) =>
    apiClient.patch(`/stages/${id}`, data).then((r) => r.data),
  delete: (id: string) =>
    apiClient.delete(`/stages/${id}`).then((r) => r.data),
};
