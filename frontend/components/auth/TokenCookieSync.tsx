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
