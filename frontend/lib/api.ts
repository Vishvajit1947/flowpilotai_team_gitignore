import axios, { AxiosError, AxiosInstance } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

// ─── Request Interceptor: inject JWT ──────────────────────────────────────────
api.interceptors.request.use((config) => {
  // Read token directly from localStorage (Zustand persist key)
  if (typeof window !== 'undefined') {
    try {
      const raw = localStorage.getItem('flowpilot-auth');
      if (raw) {
        const parsed = JSON.parse(raw) as { state?: { token?: string } };
        const token = parsed?.state?.token;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
    } catch {
      // Ignore parse errors — user not logged in
    }
  }
  return config;
});

// ─── Response Interceptor: handle 401 ─────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      // Clear persisted auth state
      localStorage.removeItem('flowpilot-auth');
      // Redirect to login, preserving intended destination
      const returnTo = encodeURIComponent(window.location.pathname);
      window.location.href = `/login?returnTo=${returnTo}`;
    }
    return Promise.reject(error);
  },
);

export default api;
