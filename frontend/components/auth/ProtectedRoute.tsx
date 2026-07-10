'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import type { Route } from 'next';
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
      router.replace(`/login?returnTo=${returnTo}` as Route);
    }
  }, [hydrated, token, user, router, pathname]);

  // Loading state: before rehydration OR after rehydration but no auth (pre-redirect)
  if (!hydrated || (!token && !user)) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-background"
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
