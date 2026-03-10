import axios from 'axios';

function resolveBaseURL(): string {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  // Production: derive backend URL from frontend hostname
  // Frontend: moonjar-pms-production-XXXX.up.railway.app
  // Backend:  moonjar-pms-production.up.railway.app
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

/**
 * CSRF token resolution — two sources:
 * 1. Cookie (works for same-origin deployments, e.g. localhost)
 * 2. sessionStorage (works for cross-origin Railway deployments where the backend
 *    sets the cookie on its domain which JS on the frontend domain can't read;
 *    the backend also sends X-CSRF-Token response header which we store here)
 */
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
    // Store CSRF token from response header (set by backend on login/refresh).
    // This allows cross-origin Railway deployments to work even when
    // document.cookie can't read the backend-domain cookie.
    const csrf = response.headers['x-csrf-token'];
    if (csrf) sessionStorage.setItem('csrf_token', csrf);
    return response;
  },
  async (error) => {
    const status = error.response?.status;
    const url = error.config?.url || '';
    // Skip interceptor for auth endpoints to avoid infinite loops
    const isAuthUrl = url.includes('/auth/');
    if (status === 401 && !error.config._retry && !isAuthUrl) {
      error.config._retry = true;
      try {
        await apiClient.post('/auth/refresh');
        return apiClient(error.config);
      } catch {
        if (!window.location.pathname.startsWith('/login')) {
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;
