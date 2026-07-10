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
