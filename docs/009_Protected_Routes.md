# 009 – Protected Routes

## Objective
Implement the client-side route protection layer: a `ProtectedRoute` wrapper component that checks authentication state and redirects unauthenticated users, a token-cookie sync component that mirrors the Zustand JWT token to a browser cookie (for middleware), and proper handling of the auth loading state to prevent flash of unauthenticated content (FOUC).

## Scope
- `components/auth/ProtectedRoute.tsx` — client-side auth guard component
- `components/auth/TokenCookieSync.tsx` — syncs Zustand token to cookie for middleware
- `app/(dashboard)/layout.tsx` — dashboard route group layout wrapping ProtectedRoute
- FOUC prevention during Zustand rehydration
- Admin-only route guard variant

## Out of Scope
- Dashboard UI (010)
- Sidebar and header (011, 012)
- Server Components auth (all protected pages are client-rendered)

## Functional Requirements
1. Any page inside `app/(dashboard)/` must require authentication.
2. Unauthenticated access to dashboard routes redirects to `/login?returnTo=<path>`.
3. During Zustand store rehydration (< 200ms), show a full-screen loading skeleton.
4. After rehydration, if no token exists, redirect immediately — no flicker of dashboard content.
5. If token exists but API returns 401 on first load, clear auth and redirect.
6. A `RequireAdmin` variant redirects non-admin users to `/dashboard` (not login).
7. The Zustand token must be mirrored to `flowpilot-token` cookie on every token change.

## Technical Requirements
- Next.js 15 App Router
- Zustand with `persist` for auth state
- `useEffect` + `useRouter` for client-side redirects
- Cookie API: `document.cookie` for write, read in middleware
- `useAuthStore` from `store/auth.ts`

## Folder Structure
```
frontend/
├── app/
│   └── (dashboard)/
│       └── layout.tsx          # Dashboard group layout
├── components/
│   └── auth/
│       ├── ProtectedRoute.tsx
│       ├── RequireAdmin.tsx
│       └── TokenCookieSync.tsx
└── hooks/
    └── useHydrated.ts          # Detects Zustand rehydration
```

## Files To Create

### `hooks/useHydrated.ts`
```typescript
'use client';

import { useEffect, useState } from 'react';

/**
 * Returns true only after the Zustand persist store has rehydrated
 * from localStorage on the client. Use this to prevent flash of
 * unauthenticated content during initial page load.
 */
export function useHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  return hydrated;
}
```

### `components/auth/TokenCookieSync.tsx`
```tsx
'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/store/auth';

/**
 * Invisible component that syncs the Zustand JWT token to a browser cookie.
 * Required because Next.js middleware (Edge Runtime) cannot access localStorage,
 * but it CAN read cookies.
 *
 * Cookie spec:
 *   name:     flowpilot-token
 *   value:    JWT string or empty
 *   path:     /
 *   SameSite: Lax
 *   Secure:   true in production
 *   HttpOnly: false (must be readable by client JS for deletion)
 *   Max-Age:  3600 (1 hour — matches ACCESS_TOKEN_EXPIRE_MINUTES)
 */
export function TokenCookieSync() {
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    if (token) {
      const secure = window.location.protocol === 'https:' ? '; Secure' : '';
      document.cookie = [
        `flowpilot-token=${token}`,
        'Path=/',
        'SameSite=Lax',
        'Max-Age=3600',
        secure,
      ].join('; ');
    } else {
      // Delete cookie
      document.cookie =
        'flowpilot-token=; Path=/; SameSite=Lax; Max-Age=0';
    }
  }, [token]);

  return null;
}
```

### `components/auth/ProtectedRoute.tsx`
```tsx
'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/auth';
import { useHydrated } from '@/hooks/useHydrated';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Wraps protected pages. Shows a loading screen during rehydration,
 * then redirects unauthenticated users to /login.
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const hydrated = useHydrated();
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (!hydrated) return; // Wait for store to rehydrate

    if (!token || !user) {
      const returnTo = encodeURIComponent(pathname);
      router.replace(`/login?returnTo=${returnTo}`);
    }
  }, [hydrated, token, user, router, pathname]);

  // Loading state: before rehydration OR after rehydration but no auth (pre-redirect)
  if (!hydrated || (!token && !user)) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        aria-label="Loading"
        role="status"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading…</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
```

### `components/auth/RequireAdmin.tsx`
```tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/auth';
import { useHydrated } from '@/hooks/useHydrated';

interface RequireAdminProps {
  children: React.ReactNode;
}

/**
 * Wraps admin-only pages. Redirects non-admin users to /dashboard.
 * Always renders after ProtectedRoute (admin pages are also protected).
 */
export function RequireAdmin({ children }: RequireAdminProps) {
  const router = useRouter();
  const hydrated = useHydrated();
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (!hydrated) return;
    if (user && user.role !== 'admin') {
      router.replace('/dashboard');
    }
  }, [hydrated, user, router]);

  if (!hydrated) return null;
  if (user && user.role !== 'admin') return null;

  return <>{children}</>;
}
```

### `app/(dashboard)/layout.tsx`
```tsx
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { TokenCookieSync } from '@/components/auth/TokenCookieSync';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <TokenCookieSync />
      {children}
    </ProtectedRoute>
  );
}
```

## Existing Files To Modify
- `app/providers.tsx` — add `<TokenCookieSync />` here as well to ensure cookie is synced on app start, not just within dashboard

```tsx
'use client';

import { Toaster } from 'sonner';
import { TokenCookieSync } from '@/components/auth/TokenCookieSync';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TokenCookieSync />
      {children}
      <Toaster position="bottom-right" toastOptions={{ classNames: { toast: 'font-sans' } }} />
    </>
  );
}
```

## API Contracts
No backend API calls — client-side routing only.

## Request Examples
Not applicable.

## Response Examples
Not applicable.

## Database Tables
Not applicable.

## Business Logic
1. **Rehydration gap**: On initial page load, Zustand's persist middleware reads from localStorage asynchronously. `useHydrated` waits for the `useEffect` to fire (guarantees we're past hydration) before making routing decisions.
2. **Double protection**: The Next.js middleware (cookie-based) is the first line of defense — it redirects server-side before HTML is sent. `ProtectedRoute` is the second line — it handles the case where the cookie is stale but the token is actually expired.
3. **Cookie expiry**: Cookie `Max-Age=3600` matches the JWT expiry. If the JWT expires, the next 401 from the API clears the token in Zustand, which triggers the `useEffect` in `TokenCookieSync` to delete the cookie, which prevents the middleware from letting the user through on the next navigation.

## Validation Rules
- Auth check only: `token && user` both must be truthy.
- Admin check: `user.role === 'admin'`.

## Error Handling
| Scenario | Behavior |
|----------|----------|
| Store not yet hydrated | Show spinner, wait |
| No token after hydration | Redirect to `/login?returnTo=<path>` |
| Token present, user null | Redirect to login (incomplete state) |
| Non-admin on admin route | Redirect to `/dashboard` |

## UI Behavior
- Loading spinner: centered, 32px blue spinning circle with "Loading…" text beneath.
- Redirect happens via `router.replace()` — no history entry added (back button won't return to protected page).
- Flash prevention: content is NOT rendered until `hydrated === true` AND `token && user` are both set.

## Component Breakdown
| Component | Renders |
|-----------|---------|
| `ProtectedRoute` | Spinner OR children (never both) |
| `RequireAdmin` | null OR children |
| `TokenCookieSync` | null (side-effect only) |
| Dashboard layout | ProtectedRoute wrapping all dashboard pages |

## State Management
Reads from Zustand auth store:
- `token: string | null`
- `user: User | null`

Writes: none (reads only).

## Loading States
- Full-screen spinner shown during hydration phase and while redirect is in-flight.
- Spinner is accessible: `role="status"`, `aria-label="Loading"`.
- Spinner disappears immediately once auth is confirmed.

## Empty States
Not applicable — this component either shows content or redirects.

## Edge Cases
- `localStorage` disabled (private browsing some browsers): `createJSONStorage(() => localStorage)` may fail silently; Zustand falls back to in-memory store; user must log in each session.
- Tab in background: cookie expires but Zustand token may still be present in memory; on next API call the 401 interceptor clears state and redirects.
- Very fast navigation: `router.replace` called multiple times is safe — only the last one takes effect.
- SSR: `useEffect` only runs on client — server never sees auth state; all dashboard pages must be client-rendered (mark them `'use client'` or wrap in client component).
- `RequireAdmin` must always be nested inside `ProtectedRoute` — never standalone.

## Test Cases
1. Unauthenticated user navigating to `/dashboard` is redirected to `/login?returnTo=%2Fdashboard`.
2. Authenticated user navigating to `/login` is redirected to `/dashboard`.
3. After `logout()`, navigating to `/dashboard` redirects to `/login`.
4. Spinner is shown during the rehydration window (test with delayed localStorage mock).
5. Non-admin user accessing an admin page is redirected to `/dashboard`.
6. Admin user accessing an admin page sees the content.
7. `TokenCookieSync` sets `flowpilot-token` cookie when token is present.
8. `TokenCookieSync` deletes `flowpilot-token` cookie when token is null.
9. After token set in Zustand, `document.cookie` contains `flowpilot-token`.

## Acceptance Criteria
- [ ] Unauthenticated access to dashboard routes redirects to login
- [ ] Loading spinner shows during rehydration (no FOUC)
- [ ] `flowpilot-token` cookie is kept in sync with Zustand token
- [ ] Admin check redirects non-admins away from admin routes
- [ ] `router.replace()` used (no history pollution)

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- `npm run build` passes
- Middleware and `ProtectedRoute` work in combination without redirect loops
