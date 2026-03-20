import apiClient from './client';

export interface LoginInput {
  email: string;
  password: string;
}

export interface GoogleLoginInput {
  id_token: string;
}

export interface FactoryBrief {
  id: string;
  name: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: string;
  language: string;
  is_active: boolean;
  totp_enabled?: boolean;
  factories?: FactoryBrief[];
}

export const authApi = {
  login: (data: LoginInput) =>
    apiClient.post('/auth/login', data).then((r) => r.data),
  googleLogin: (data: GoogleLoginInput) =>
    apiClient.post('/auth/google', data).then((r) => r.data),
  refresh: () =>
    apiClient.post('/auth/refresh').then((r) => r.data),
  logout: () =>
    apiClient.post('/auth/logout').then((r) => r.data),
  logoutAll: () =>
    apiClient.post('/auth/logout-all').then((r) => r.data),
  me: () =>
    apiClient.get<UserProfile>('/auth/me').then((r) => r.data),
  verifyOwnerKey: (data: { key: string }) =>
    apiClient.post('/auth/verify-owner-key', data).then((r) => r.data),
  verifyTotp: (data: { totp_pending_token: string; code: string }) =>
    apiClient.post('/auth/totp-verify', data).then((r) => r.data),
};
