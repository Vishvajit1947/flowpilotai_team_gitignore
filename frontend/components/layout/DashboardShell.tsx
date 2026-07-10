'use client';

import { useEffect } from 'react';
import { useUIStore } from '@/store/ui';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { AdminBanner } from '@/components/admin/AdminBanner';
import { ErrorBoundary } from '@/components/errors/ErrorBoundary';
import { cn } from '@/lib/utils';

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const { sidebarOpen, sidebarCollapsed, setSidebarOpen } = useUIStore();

  // Close mobile sidebar on resize to desktop
  useEffect(() => {
    const handler = () => {
      if (window.innerWidth >= 768) {
        setSidebarOpen(false);
      }
    };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, [setSidebarOpen]);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* ── Desktop Sidebar ─────────────────────────────────────────────── */}
      <aside
        className={cn(
          'hidden md:flex flex-col flex-shrink-0 border-r bg-card transition-all duration-300',
          sidebarCollapsed ? 'w-16' : 'w-60',
        )}
      >
        <Sidebar />
      </aside>

      {/* ── Mobile Sidebar Overlay ──────────────────────────────────────── */}
      {sidebarOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/50 md:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
          {/* Drawer */}
          <aside className="fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r bg-card shadow-xl md:hidden">
            <Sidebar />
          </aside>
        </>
      )}

      {/* ── Main Content ────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main
          id="main-content"
          className="flex-1 overflow-y-auto p-6"
          tabIndex={-1}
        >
          <div className="mb-6">
            <AdminBanner />
          </div>
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
