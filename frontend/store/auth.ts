import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { User, AuthTokens } from '@/types';
import api from '@/lib/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

interface AuthActions {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  fetchCurrentUser: () => Promise<void>;
  updateUser: (updatedUser: Partial<User>) => void;
}

export type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // ─── State ───────────────────────────────────────────────────────────
      user: null,
      token: null,
      isLoading: false,
      error: null,

      // ─── Actions ─────────────────────────────────────────────────────────
      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const { data } = await api.post<AuthTokens>('/auth/login', {
            email,
            password,
          });
          set({ token: data.access_token });

          // Fetch user profile after setting token
          await get().fetchCurrentUser();
          set({ isLoading: false });
        } catch (err: unknown) {
          const message = extractErrorMessage(err, 'Login failed');
          set({ isLoading: false, error: message, token: null, user: null });
          throw err; // Allow the form to catch and handle
        }
      },

      register: async (email: string, password: string, fullName: string) => {
        set({ isLoading: true, error: null });
        try {
          const { data } = await api.post<AuthTokens>('/auth/register', {
            email,
            password,
            full_name: fullName,
          });
          set({ token: data.access_token });
          await get().fetchCurrentUser();
          set({ isLoading: false });
        } catch (err: unknown) {
          const message = extractErrorMessage(err, 'Registration failed');
          set({ isLoading: false, error: message, token: null, user: null });
          throw err;
        }
      },

      logout: () => {
        set({ user: null, token: null, error: null, isLoading: false });
        // Redirect handled by middleware or calling component
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
      },

      clearError: () => set({ error: null }),

      fetchCurrentUser: async () => {
        try {
          const { data } = await api.get<User>('/auth/me');
          set({ user: data });
        } catch {
          set({ user: null, token: null });
        }
      },

      updateUser: (updatedUser: Partial<User>) => {
        set((state) => {
          if (!state.user) return state;
          return {
            user: {
              ...state.user,
              ...updatedUser,
            },
          };
        });
      },
    }),
    {
      name: 'flowpilot-auth',
      storage: createJSONStorage(() => localStorage),
      // Only persist token and user — not transient UI state
      partialize: (state) => ({
        user: state.user,
        token: state.token,
      }),
    },
  ),
);

// ─── Utility ──────────────────────────────────────────────────────────────────
function extractErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const response = (err as { response?: { data?: { detail?: string } } }).response;
    if (response?.data?.detail) {
      return typeof response.data.detail === 'string'
        ? response.data.detail
        : 'Validation error. Please check your input.';
    }
  }
  return fallback;
}
