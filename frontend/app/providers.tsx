'use client';

import { Toaster } from 'sonner';
import { TokenCookieSync } from '@/components/auth/TokenCookieSync';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TokenCookieSync />
      {children}
      <Toaster
        position="bottom-right"
        toastOptions={{
          classNames: {
            toast: 'font-sans',
          },
        }}
      />
    </>
  );
}
