import axios from 'axios';

function resolveBaseURL(): string {
  if (typeof window !== 'undefined' && window.location.hostname.includes('.up.railway.app')) {
    const host = window.location.hostname.replace(/-\d+\.up\.railway\.app$/, '.up.railway.app');
    return `${window.location.protocol}//${host}/api`;
  }
  return '/api';
}

const apiClient = axios.create({
  baseURL: resolveBaseURL(),
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

function getCsrfToken(): string | null {
  const fromCookie = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)?.[1];
  if (fromCookie) return decodeURIComponent(fromCookie);
  return sessionStorage.getItem('csrf_token');
}

apiClient.interceptors.request.use((config) => {
  if (['post', 'put', 'patch', 'delete'].includes(config.method || '')) {
    const csrf = getCsrfToken();
    if (csrf) config.headers['X-CSRF-Token'] = csrf;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    const csrf = response.headers['x-csrf-token'];
    if (csrf) sessionStorage.setItem('csrf_token', csrf);
    return response;
  },
  async (error) => {
    const status = error.response?.status;
    const url: string = error.config?.url || '';
    const isAuthUrl = url.includes('/auth/');

    if (status === 401 && !error.config._retry && !isAuthUrl) {
      error.config._retry = true;
      try {
        await apiClient.post('/auth/refresh');
        return apiClient(error.config);
      } catch {
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/warehouse/login';
        }
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;
