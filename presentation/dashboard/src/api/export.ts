import apiClient from './client';

export const exportApi = {
  ordersExcel: (params?: { factory_id?: string; date_from?: string; date_to?: string }) =>
    apiClient.get('/export/orders/excel', { params, responseType: 'blob' }).then((r) => r.data),
  ordersPdf: (params?: { factory_id?: string; date_from?: string; date_to?: string }) =>
    apiClient.get('/export/orders/pdf', { params, responseType: 'blob' }).then((r) => r.data),
  positionsPdf: (params?: { factory_id?: string; order_id?: string }) =>
    apiClient.get('/export/positions/pdf', { params, responseType: 'blob' }).then((r) => r.data),
  ownerMonthly: (data?: { factory_id?: string; month?: string }) =>
    apiClient.post('/export/owner-monthly', data, { responseType: 'blob' }).then((r) => r.data),
  ceoDailyReport: (data?: { factory_id?: string }) =>
    apiClient.post('/export/ceo-daily', data, { responseType: 'blob' }).then((r) => r.data),
};
