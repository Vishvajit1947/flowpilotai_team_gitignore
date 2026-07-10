'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean; // desktop collapse to icon-only
  theme: 'light' | 'dark' | 'system';
}

interface UIActions {
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebarCollapsed: () => void;
  setTheme: (theme: UIState['theme']) => void;
}

export const useUIStore = create<UIState & UIActions>()(
  persist(
    (set) => ({
      sidebarOpen: false,
      sidebarCollapsed: false,
      theme: 'system',

      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebar: () =>
        set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setSidebarCollapsed: (collapsed) =>
        set({ sidebarCollapsed: collapsed }),
      toggleSidebarCollapsed: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'flowpilot-ui',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
      }),
    },
  ),
);
