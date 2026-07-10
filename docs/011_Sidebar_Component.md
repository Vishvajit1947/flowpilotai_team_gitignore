# 011 – Sidebar Component

## Objective
Build the full navigation sidebar component with route links, active state highlighting, user profile section, logout button, and desktop collapse-to-icon mode. The sidebar drives all primary navigation within the FlowPilot AI dashboard.

## Scope
- `components/layout/Sidebar.tsx` — main sidebar component
- `components/layout/NavItem.tsx` — individual nav link with icon, label, active state
- Navigation item configuration array
- Collapsed mode (icon-only with tooltips)
- User avatar + name at bottom
- Logout button

## Out of Scope
- Mobile drawer behavior (handled in 010 DashboardShell)
- Header component (012)
- Theme toggle (040)

## Functional Requirements
1. Display navigation links: Dashboard, AI Inbox, Document Intelligence, Analytics, Workflow History.
2. Highlight the active route using `usePathname()`.
3. In collapsed mode, show only icons with Radix Tooltip showing label on hover.
4. Show current user's name and email at the bottom.
5. Logout button at the bottom that calls `useAuth().logout()`.
6. Collapse toggle button at the top of the sidebar.
7. Navigation links close the mobile sidebar (call `setSidebarOpen(false)`) on click.

## Technical Requirements
- Next.js `Link` for navigation
- `usePathname` from `next/navigation` for active detection
- Radix UI Tooltip for collapsed mode
- Lucide React icons
- Zustand `useUIStore` for collapsed state
- `useAuth` hook for user data and logout

## Folder Structure
```
frontend/
└── components/
    └── layout/
        ├── Sidebar.tsx
        └── NavItem.tsx
```

## Files To Create

### `components/layout/NavItem.tsx`
```tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface NavItemProps {
  href: string;
  label: string;
  icon: LucideIcon;
  collapsed?: boolean;
  onClick?: () => void;
}

export function NavItem({
  href,
  label,
  icon: Icon,
  collapsed = false,
  onClick,
}: NavItemProps) {
  const pathname = usePathname();
  const isActive =
    href === '/dashboard'
      ? pathname === '/dashboard'
      : pathname.startsWith(href);

  const linkContent = (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
        'hover:bg-accent hover:text-accent-foreground',
        isActive
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground',
        collapsed && 'justify-center px-2',
      )}
      aria-current={isActive ? 'page' : undefined}
    >
      <Icon className="h-5 w-5 flex-shrink-0" />
      {!collapsed && <span>{label}</span>}
    </Link>
  );

  if (collapsed) {
    return (
      <TooltipProvider delayDuration={100}>
        <Tooltip>
          <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
          <TooltipContent side="right">
            <p>{label}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return linkContent;
}
```

### `components/layout/Sidebar.tsx`
```tsx
'use client';

import {
  LayoutDashboard,
  Inbox,
  FileText,
  BarChart3,
  History,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from 'lucide-react';
import { useUIStore } from '@/store/ui';
import { useAuth } from '@/hooks/useAuth';
import { NavItem } from './NavItem';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/inbox', label: 'AI Inbox', icon: Inbox },
  {
    href: '/dashboard/documents',
    label: 'Document Intelligence',
    icon: FileText,
  },
  { href: '/dashboard/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/dashboard/history', label: 'Workflow History', icon: History },
] as const;

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebarCollapsed, setSidebarOpen } =
    useUIStore();
  const { user, logout } = useAuth();

  const handleNavClick = () => {
    // Close mobile drawer on navigation
    setSidebarOpen(false);
  };

  return (
    <div className="flex h-full flex-col">
      {/* ── Logo + Collapse Button ─────────────────────────────────────── */}
      <div
        className={cn(
          'flex h-16 items-center border-b px-4',
          sidebarCollapsed ? 'justify-center' : 'justify-between',
        )}
      >
        {!sidebarCollapsed && (
          <span className="text-lg font-bold tracking-tight">
            FlowPilot <span className="text-primary">AI</span>
          </span>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebarCollapsed}
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="hidden md:flex"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* ── Navigation Links ──────────────────────────────────────────── */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.href}
            href={item.href}
            label={item.label}
            icon={item.icon}
            collapsed={sidebarCollapsed}
            onClick={handleNavClick}
          />
        ))}
      </nav>

      <Separator />

      {/* ── User Profile + Logout ─────────────────────────────────────── */}
      <div className={cn('p-3 space-y-2', sidebarCollapsed && 'flex flex-col items-center')}>
        {user && !sidebarCollapsed && (
          <div className="flex items-center gap-3 rounded-lg px-3 py-2">
            <Avatar className="h-8 w-8 flex-shrink-0">
              <AvatarFallback className="text-xs">
                {getInitials(user.full_name)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user.full_name}</p>
              <p className="truncate text-xs text-muted-foreground">{user.email}</p>
            </div>
          </div>
        )}
        <Button
          variant="ghost"
          size={sidebarCollapsed ? 'icon' : 'sm'}
          className={cn(
            'text-muted-foreground hover:text-destructive w-full',
            !sidebarCollapsed && 'justify-start gap-3',
          )}
          onClick={logout}
          aria-label="Sign out"
        >
          <LogOut className="h-4 w-4 flex-shrink-0" />
          {!sidebarCollapsed && <span>Sign out</span>}
        </Button>
      </div>
    </div>
  );
}
```

## Existing Files To Modify
None — new files only.

## API Contracts
None — UI component.

## Request Examples
Not applicable.

## Response Examples
Not applicable.

## Database Tables
Not applicable.

## Business Logic
- Active route detection: exact match for `/dashboard`, prefix match for all others (e.g., `/dashboard/inbox/123` highlights the Inbox nav item).
- `getInitials` extracts up to 2 initials from the user's full name.
- Nav clicks close the mobile drawer (`setSidebarOpen(false)`) — this is a no-op on desktop.

## Validation Rules
Not applicable.

## Error Handling
- If `user` is null (shouldn't happen inside ProtectedRoute), the user profile section is hidden.

## UI Behavior
### Expanded Mode (default)
- Logo text left-aligned, collapse button right-aligned in header
- Nav items: icon + label, full width
- User card: avatar + name + email
- Logout: icon + "Sign out" text

### Collapsed Mode (desktop only)
- Logo hidden, collapse button centered
- Nav items: icon only, centered
- Tooltips show label on hover (Radix Tooltip, side=right, 100ms delay)
- Logout: icon only

### Active State
- Active link: `bg-primary/10 text-primary`
- Inactive link: `text-muted-foreground`, hover: `bg-accent`

## Component Breakdown
| Component | Props | Purpose |
|-----------|-------|---------|
| `Sidebar` | none | Full sidebar with state |
| `NavItem` | href, label, icon, collapsed, onClick | Single nav link |

## State Management
- Reads `sidebarCollapsed` from `useUIStore`
- Reads `user` from `useAuth`
- Calls `toggleSidebarCollapsed`, `setSidebarOpen`, `logout`

## Loading States
No loading states — sidebar is always immediately visible once layout mounts.

## Empty States
- If `NAV_ITEMS` were empty: nav `<nav>` renders empty (not possible given static config).

## Edge Cases
- Long user names: truncated with `truncate` Tailwind class.
- Long email addresses: truncated with `truncate` class.
- Nav click on currently active route: harmless (no redirect, drawer closes).
- Collapsed sidebar on initial load: persisted in localStorage — user preference retained.

## Test Cases
1. All 5 nav items render with correct labels and icons.
2. Active nav item has `aria-current="page"` attribute.
3. In collapsed mode, nav labels are hidden.
4. Tooltips render in collapsed mode on hover.
5. Logout button calls `logout()` action.
6. `getInitials("Alice Smith")` returns `"AS"`.
7. `getInitials("Madonna")` returns `"M"`.
8. Nav click calls `setSidebarOpen(false)`.
9. Collapse button toggles `sidebarCollapsed` state.

## Acceptance Criteria
- [ ] All 5 navigation routes link correctly
- [ ] Active route highlighted correctly
- [ ] Collapsed mode shows icons with tooltips
- [ ] User name/email displayed at bottom
- [ ] Logout button functional
- [ ] Mobile drawer closes on nav click
- [ ] Collapse toggle persists across page reloads

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- WCAG 2.1 AA: `aria-current`, `aria-label` on icon buttons
