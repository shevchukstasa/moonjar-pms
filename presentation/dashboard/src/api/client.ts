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

let csrfToken: string | null = null;
export const setCsrfToken = (token: string) => { csrfToken = token; };

apiClient.interceptors.request.use((config) => {
  if (csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method || '')) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
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
