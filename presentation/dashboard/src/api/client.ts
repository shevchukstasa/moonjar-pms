import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
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
    if (status === 401 && !error.config._retry) {
      error.config._retry = true;
      try {
        await apiClient.post('/auth/refresh');
        return apiClient(error.config);
      } catch {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;
