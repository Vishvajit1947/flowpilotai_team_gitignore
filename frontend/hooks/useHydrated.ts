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
