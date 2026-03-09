import apiClient from './client';

export interface LoginInput {
  email: string;
  password: string;
}

export interface GoogleLoginInput {
  credential: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: string;
  language: string;
  is_active: boolean;
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
  verifyOwnerKey: (data: { owner_key: string }) =>
    apiClient.post('/auth/verify-owner-key', data).then((r) => r.data),
};
