# 008 – Auth Context

## Objective
Implement the frontend authentication layer: a Zustand store for auth state, an `axios` API client with JWT injection, login/register/logout actions, a React context provider, and server-side token hydration using Next.js middleware — so every page and component can access the current user and auth status.

## Scope
- `store/auth.ts` — Zustand auth store (user, token, loading, error)
- `lib/api.ts` — Axios instance with JWT interceptor and 401 handling
- `app/(auth)/login/page.tsx` — Login form page
- `app/(auth)/register/page.tsx` — Register form page
- `app/(auth)/layout.tsx` — Auth layout (centered card, no sidebar)
- `middleware.ts` — Next.js middleware for token-based route protection
- `hooks/useAuth.ts` — Custom hook wrapping Zustand store

## Out of Scope
- Protected route component (009)
- Dashboard layout (010)
- Password reset
- Social auth

## Functional Requirements
1. Auth state (user object, token) persists in `localStorage` and rehydrates on page load.
2. Every API request automatically includes `Authorization: Bearer <token>` if logged in.
3. When the backend returns 401, automatically clear auth state and redirect to `/login`.
4. Login form: email + password fields, submit button, loading state, error message.
5. Register form: full_name + email + password fields, submit, loading, error.
6. After successful login/register, redirect to `/dashboard`.
7. Logout clears token, user, and redirects to `/login`.
8. `useAuth()` hook exposes: `{ user, token, isAuthenticated, isLoading, login, register, logout }`.

## Technical Requirements
- Zustand 4.5+ with `persist` middleware (localStorage)
- Axios 1.7+ for HTTP client
- Next.js 15 App Router
- TypeScript — all actions and state fully typed
- `User` and `AuthTokens` types from `types/index.ts`

## Folder Structure
```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── layout.tsx
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── register/
│   │       └── page.tsx
│   └── middleware.ts           # (Next.js: must be in app root or src root)
├── middleware.ts                # Route guard middleware
├── store/
│   └── auth.ts                 # Zustand auth store
├── lib/
│   └── api.ts                  # Axios instance
└── hooks/
    └── useAuth.ts              # Auth hook
```

## Files To Create

### `lib/api.ts`
```typescript
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
```

### `store/auth.ts`
```typescript
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
```

### `hooks/useAuth.ts`
```typescript
'use client';

import { useAuthStore } from '@/store/auth';

export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.token);
  const isLoading = useAuthStore((s) => s.isLoading);
  const error = useAuthStore((s) => s.error);
  const login = useAuthStore((s) => s.login);
  const register = useAuthStore((s) => s.register);
  const logout = useAuthStore((s) => s.logout);
  const clearError = useAuthStore((s) => s.clearError);

  return {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
  };
}
```

### `middleware.ts`
```typescript
import { NextRequest, NextResponse } from 'next/server';

const PUBLIC_ROUTES = ['/login', '/register'];
const AUTH_ROUTES = ['/login', '/register'];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // Skip middleware for Next.js internals and static files
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // Read token from cookie (set by auth store hydration — see notes)
  // Middleware runs on the Edge; it cannot access localStorage.
  // We use a cookie mirror approach: when the Zustand store sets the token,
  // also set a cookie named 'flowpilot-token' (httpOnly: false for client access).
  // The middleware only needs to know IF a token exists, not validate it.
  // Full validation happens at the API layer.
  const token = request.cookies.get('flowpilot-token')?.value;

  const isAuthRoute = AUTH_ROUTES.some((r) => pathname.startsWith(r));
  const isPublicRoute = PUBLIC_ROUTES.some((r) => pathname.startsWith(r));

  // Logged-in user visiting login/register → redirect to dashboard
  if (isAuthRoute && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // Unauthenticated user visiting protected route → redirect to login
  if (!isPublicRoute && !token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('returnTo', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

### `app/(auth)/layout.tsx`
```tsx
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
```

### `app/(auth)/login/page.tsx`
```tsx
'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isLoading, error, clearError, isAuthenticated } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const returnTo = searchParams.get('returnTo') ?? '/dashboard';

  useEffect(() => {
    if (isAuthenticated) {
      router.replace(returnTo);
    }
  }, [isAuthenticated, router, returnTo]);

  useEffect(() => {
    return () => clearError();
  }, [clearError]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalError(null);

    if (!email.trim()) {
      setLocalError('Email is required');
      return;
    }
    if (!password) {
      setLocalError('Password is required');
      return;
    }

    try {
      await login(email, password);
      router.replace(returnTo);
    } catch {
      // Error is set in store — displayed via `error`
    }
  }

  const displayError = localError ?? error;

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Sign in</CardTitle>
        <CardDescription>
          Enter your credentials to access FlowPilot AI
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {displayError && (
            <div
              role="alert"
              className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive"
            >
              {displayError}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Signing in…' : 'Sign in'}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{' '}
            <Link
              href="/register"
              className="text-primary underline-offset-4 hover:underline"
            >
              Sign up
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
```

### `app/(auth)/register/page.tsx`
```tsx
'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

export default function RegisterPage() {
  const router = useRouter();
  const { register, isLoading, error, clearError, isAuthenticated } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) router.replace('/dashboard');
  }, [isAuthenticated, router]);

  useEffect(() => () => clearError(), [clearError]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalError(null);

    if (fullName.trim().length < 2) {
      setLocalError('Full name must be at least 2 characters');
      return;
    }
    if (!email.includes('@')) {
      setLocalError('Enter a valid email address');
      return;
    }
    if (password.length < 8) {
      setLocalError('Password must be at least 8 characters');
      return;
    }

    try {
      await register(email, password, fullName);
      router.replace('/dashboard');
    } catch {
      // Error displayed from store
    }
  }

  const displayError = localError ?? error;

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Create account</CardTitle>
        <CardDescription>
          Start automating your workflows with FlowPilot AI
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {displayError && (
            <div role="alert" className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {displayError}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="fullName">Full name</Label>
            <Input
              id="fullName"
              type="text"
              placeholder="Alice Smith"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Min. 8 characters"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Creating account…' : 'Create account'}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link href="/login" className="text-primary underline-offset-4 hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
```

## Existing Files To Modify
- `app/providers.tsx` — no change needed (Zustand store is self-contained)

## API Contracts
Calls these backend endpoints:
- `POST /api/v1/auth/login` — see 007
- `POST /api/v1/auth/register` — see 006
- `GET /api/v1/auth/me` — see 007

## Database Tables
Not applicable — frontend only.

## Business Logic
- Token is stored in Zustand persist (localStorage key `flowpilot-auth`) AND mirrored to a client-readable cookie (`flowpilot-token`) so that Next.js middleware can read it.
- Cookie mirroring: add a `useEffect` in a `TokenCookieSync` component that sets/clears the cookie whenever the Zustand token changes.
- The middleware only checks if the cookie exists — full JWT validation happens on the API server.

## Validation Rules
### Login form
- Email: required, non-empty
- Password: required, non-empty

### Register form
- Full name: min 2 characters
- Email: must contain `@`
- Password: min 8 characters

Client-side validation is a UX aid only — the server re-validates all input.

## Error Handling
| Scenario | UI Response |
|----------|-------------|
| Network error | "Login failed" (fallback message) |
| 401 wrong credentials | Backend detail shown: "Invalid email or password" |
| 409 duplicate email | Backend detail shown: "An account with this email already exists" |
| 422 validation error | "Validation error. Please check your input." |
| Field empty (client) | Inline error above form, submit blocked |

## UI Behavior
- Login/register pages are centered cards on a muted background.
- Submit button shows spinner text `"Signing in…"` / `"Creating account…"` while loading.
- Error appears in a red alert box above the form fields.
- After successful auth, router replaces current history entry with `/dashboard` (back button won't return to login).
- `returnTo` query param preserves the originally intended URL.

## Component Breakdown
| Component | File | Purpose |
|-----------|------|---------|
| `LoginPage` | `app/(auth)/login/page.tsx` | Login form |
| `RegisterPage` | `app/(auth)/register/page.tsx` | Registration form |
| `AuthLayout` | `app/(auth)/layout.tsx` | Centered wrapper |
| `useAuth` | `hooks/useAuth.ts` | Store selector hook |
| `useAuthStore` | `store/auth.ts` | Zustand store |
| `api` | `lib/api.ts` | Axios instance |

## State Management
```typescript
// Zustand auth store shape
{
  user: User | null,
  token: string | null,
  isLoading: boolean,
  error: string | null,
  // + actions
}
```
Persisted to localStorage under key `flowpilot-auth` (only `user` and `token`).

## Loading States
- Form submit button: disabled + text changes to `"Signing in…"` or `"Creating account…"`
- All form inputs: `disabled` attribute while loading
- No skeleton loaders on auth pages

## Empty States
- Error field: hidden when `null`, visible as red alert when non-null
- Forms start empty; no autofill beyond browser's built-in

## Edge Cases
- Page reloads: Zustand persist rehydrates `user` and `token` from localStorage.
- Token expired on page load: first API call returns 401, interceptor clears auth and redirects to `/login`.
- Multiple tabs logged out: localStorage event listener can detect token removal — not implemented in v1 (acceptable limitation).
- SSR: Zustand `persist` requires `typeof window !== 'undefined'` guard — `createJSONStorage(() => localStorage)` handles this correctly.
- `returnTo` URL injection: only internal paths allowed (do not redirect to external URLs). Validate that `returnTo` starts with `/`.

## Test Cases
1. Login with valid credentials stores token in localStorage.
2. Login with invalid credentials shows error message.
3. Register with valid data stores token and user.
4. Register with duplicate email shows "already exists" error.
5. `useAuth().isAuthenticated` returns `true` when token+user are set.
6. `logout()` clears localStorage and redirects.
7. API interceptor adds `Authorization: Bearer <token>` header.
8. API interceptor on 401 clears auth state.
9. Authenticated user visiting `/login` is redirected to `/dashboard`.
10. Unauthenticated user visiting `/dashboard` is redirected to `/login`.

## Acceptance Criteria
- [ ] Login form submits and stores JWT in localStorage
- [ ] Register form submits and stores JWT in localStorage
- [ ] Logout clears all auth state
- [ ] All API requests include Bearer token
- [ ] 401 responses clear auth and redirect to login
- [ ] Middleware protects non-public routes
- [ ] `useAuth()` hook exposes all required fields

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- `npm run build` passes
- Forms handle all error states gracefully
