import apiClient from './client';

export interface ReferenceItem {
  value: string;
  label: string;
}

export interface AllReferenceData {
  product_types: ReferenceItem[];
  stone_types: ReferenceItem[];
  glaze_types: ReferenceItem[];
  finish_types: ReferenceItem[];
  shape_types: ReferenceItem[];
  material_types: ReferenceItem[];
  position_statuses: ReferenceItem[];
  collections: ReferenceItem[];
}

export const referenceApi = {
  getAll: () =>
    apiClient.get<AllReferenceData>('/reference/all').then((r) => r.data),
  getProductTypes: () =>
    apiClient.get<ReferenceItem[]>('/reference/product-types').then((r) => r.data),
  getStoneTypes: () =>
    apiClient.get<ReferenceItem[]>('/reference/stone-types').then((r) => r.data),
  getGlazeTypes: () =>
    apiClient.get<ReferenceItem[]>('/reference/glaze-types').then((r) => r.data),
  getFinishTypes: () =>
    apiClient.get<ReferenceItem[]>('/reference/finish-types').then((r) => r.data),
  getShapeTypes: () =>
    apiClient.get<ReferenceItem[]>('/reference/shape-types').then((r) => r.data),
  getMaterialTypes: () =>
    apiClient.get<ReferenceItem[]>('/reference/material-types').then((r) => r.data),
  getPositionStatuses: () =>
    apiClient.get<ReferenceItem[]>('/reference/position-statuses').then((r) => r.data),
  getCollections: () =>
    apiClient.get<ReferenceItem[]>('/reference/collections').then((r) => r.data),
};
