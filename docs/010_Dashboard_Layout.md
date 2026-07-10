# 010 – Dashboard Layout

## Objective
Build the main dashboard shell layout that hosts the persistent sidebar, top header, and main content area for all authenticated pages. This layout uses Next.js App Router route groups and provides a consistent, responsive two-column structure that all dashboard pages inherit.

## Scope
- `app/(dashboard)/dashboard/layout.tsx` — inner dashboard page layout
- Responsive two-column grid: fixed sidebar (240px) + fluid main content
- Sidebar collapse on mobile (< 768px) via slide-in drawer
- Main content scroll area
- Route-group-level layout nesting
- Framer Motion page transition wrapper

## Out of Scope
- Sidebar internals (011)
- Header internals (012)
- Any dashboard page content

## Functional Requirements
1. Layout is a two-panel design: left sidebar (fixed width) + right content area (fluid).
2. On mobile (< 768px), sidebar is hidden by default; hamburger button in header opens it as a slide-in overlay.
3. Sidebar state (open/collapsed) is managed in a Zustand UI store.
4. Content area has its own vertical scroll — sidebar is always visible (sticky).
5. Page transitions use Framer Motion with a subtle fade+slide animation.
6. The layout background uses `bg-background` for the content area and `bg-card` for sidebar.

## Technical Requirements
- Next.js 15 App Router (`app/(dashboard)/dashboard/`)
- Zustand for sidebar open/close state
- Framer Motion for page transitions
- Tailwind CSS for layout
- `usePathname` to detect route changes for animation keys

## Folder Structure
```
frontend/
├── app/
│   └── (dashboard)/
│       ├── layout.tsx                 # ProtectedRoute wrapper (from 009)
│       └── dashboard/
│           ├── layout.tsx             # Sidebar + header shell
│           └── page.tsx               # Dashboard home page (stub)
├── components/
│   └── layout/
│       ├── DashboardShell.tsx         # Client-side layout wrapper
│       └── PageTransition.tsx         # Framer Motion wrapper
└── store/
    └── ui.ts                          # UI state store (sidebar, theme)
```

## Files To Create

### `store/ui.ts`
```typescript
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
```

### `components/layout/PageTransition.tsx`
```tsx
'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { usePathname } from 'next/navigation';

const variants = {
  hidden: { opacity: 0, y: 8 },
  enter: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={pathname}
        variants={variants}
        initial="hidden"
        animate="enter"
        exit="exit"
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className="h-full"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
```

### `components/layout/DashboardShell.tsx`
```tsx
'use client';

import { useEffect } from 'react';
import { useUIStore } from '@/store/ui';
import { Sidebar } from '@/components/layout/Sidebar';   // from 011
import { Header } from '@/components/layout/Header';     // from 012
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
          {children}
        </main>
      </div>
    </div>
  );
}
```

### `app/(dashboard)/dashboard/layout.tsx`
```tsx
import { DashboardShell } from '@/components/layout/DashboardShell';
import { PageTransition } from '@/components/layout/PageTransition';

export default function DashboardPageLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DashboardShell>
      <PageTransition>{children}</PageTransition>
    </DashboardShell>
  );
}
```

### `app/(dashboard)/dashboard/page.tsx` (stub)
```tsx
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to FlowPilot AI. Your AI-powered inbox is ready.
        </p>
      </div>
      {/* Metric cards, charts, etc. added in subsequent tasks */}
    </div>
  );
}
```

## Existing Files To Modify
None — this task creates new files.

## API Contracts
None — layout only.

## Request Examples
Not applicable.

## Response Examples
Not applicable.

## Database Tables
Not applicable.

## Business Logic
- Sidebar collapse state persisted in localStorage via Zustand persist (users keep their preference).
- Mobile sidebar open state is NOT persisted (reset on page load).
- `DashboardShell` is a Client Component because it reads Zustand state; the layout wrapper `app/(dashboard)/dashboard/layout.tsx` is a Server Component.

## Validation Rules
Not applicable.

## Error Handling
- If `Sidebar` or `Header` components throw, Error Boundary (038) wraps the shell.

## UI Behavior
### Desktop (≥ 768px)
- Left column: `w-60` (240px) sidebar, `flex-shrink-0`, never scrolls independently
- Right column: flex column, header fixed top, main area scrollable
- Sidebar can be collapsed to `w-16` (icon-only mode) via button in sidebar

### Mobile (< 768px)
- Sidebar hidden by default
- Header shows hamburger menu button
- Tapping hamburger → sidebar slides in from left with black backdrop
- Tapping backdrop or navigating → sidebar closes
- No sidebar collapse in mobile mode

### Transitions
- Page content fades in (opacity 0→1) and slides up 8px on route change
- Duration: 200ms, ease: easeInOut
- Sidebar width transition: 300ms ease

## Component Breakdown
| Component | Type | Responsibility |
|-----------|------|---------------|
| `DashboardShell` | Client | Layout grid, mobile drawer logic |
| `PageTransition` | Client | Framer Motion route animation |
| Dashboard layout | Server | Compose shell + transition |
| `useUIStore` | Zustand | Sidebar state |

## State Management
```typescript
// UIStore relevant to layout
{
  sidebarOpen: boolean,       // mobile drawer open
  sidebarCollapsed: boolean,  // desktop icon-only mode
}
```

## Loading States
- No layout-level loading states — `ProtectedRoute` (009) handles the pre-auth spinner.
- Individual page content handles its own loading (013, 014, etc.).

## Empty States
Not applicable at layout level.

## Edge Cases
- User resizes browser from mobile to desktop while sidebar is open: `resize` event listener closes mobile sidebar.
- Browser with narrow viewport on desktop: sidebar collapses automatically below 768px breakpoint.
- `overflow-hidden` on the root container prevents double scrollbars.
- Route group `(dashboard)` is purely for layout nesting — it does not appear in URLs.

## Test Cases
1. Desktop layout renders sidebar and main content side by side.
2. Mobile layout hides sidebar by default.
3. Mobile sidebar opens when `sidebarOpen` is set to `true`.
4. Clicking backdrop closes mobile sidebar.
5. `sidebarCollapsed = true` sets sidebar width to `w-16`.
6. Page transition component renders children with motion wrapper.
7. `useUIStore.sidebarCollapsed` persists across page reloads.
8. `useUIStore.sidebarOpen` does NOT persist (resets to false).

## Acceptance Criteria
- [ ] Two-column layout renders on desktop
- [ ] Mobile sidebar works as slide-in drawer
- [ ] Sidebar collapse mode toggles width
- [ ] Page transitions animate on route change
- [ ] No horizontal scroll on any viewport
- [ ] `main` content area scrolls independently

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Responsive behavior verified at 375px, 768px, and 1440px widths
