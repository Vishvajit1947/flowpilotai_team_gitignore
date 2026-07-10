# 012 – Header Component

## Objective
Build the top navigation header bar that contains the mobile hamburger menu button, page title, user avatar dropdown menu (profile, settings, logout), and a notification bell placeholder. The header is persistent across all dashboard pages.

## Scope
- `components/layout/Header.tsx` — main header component
- `components/layout/PageTitle.tsx` — dynamic title derived from current route
- Mobile hamburger button wired to sidebar drawer
- User dropdown menu (Radix DropdownMenu)
- Notification bell icon (UI placeholder — no backend in v1)

## Out of Scope
- Dark mode toggle (040)
- Notification system backend
- Breadcrumb navigation

## Functional Requirements
1. Show hamburger button on mobile (< 768px) that opens the sidebar.
2. Show current page title derived from the URL path.
3. Show user avatar with initials, clicking opens dropdown menu.
4. Dropdown items: "Profile" (shows user email), "Sign out".
5. Sign out triggers `logout()` from `useAuth`.
6. Notification bell icon present (non-functional in v1, shows tooltip "Coming soon").

## Technical Requirements
- Radix UI `DropdownMenu` for user menu
- Lucide React icons: `Menu`, `Bell`, `LogOut`, `User`
- `usePathname` for page title derivation
- `useAuth` for user data and logout action
- `useUIStore` for sidebar toggle

## Folder Structure
```
frontend/
└── components/
    └── layout/
        ├── Header.tsx
        └── PageTitle.tsx
```

## Files To Create

### `components/layout/PageTitle.tsx`
```tsx
'use client';

import { usePathname } from 'next/navigation';

const ROUTE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/dashboard/inbox': 'AI Inbox',
  '/dashboard/documents': 'Document Intelligence',
  '/dashboard/analytics': 'Analytics',
  '/dashboard/history': 'Workflow History',
  '/dashboard/admin': 'Admin',
};

export function PageTitle() {
  const pathname = usePathname();

  // Find the most specific matching route
  const title =
    ROUTE_TITLES[pathname] ??
    Object.entries(ROUTE_TITLES)
      .filter(([route]) => pathname.startsWith(route))
      .sort((a, b) => b[0].length - a[0].length)[0]?.[1] ??
    'FlowPilot AI';

  return (
    <h1 className="text-lg font-semibold truncate max-w-[200px] sm:max-w-none">
      {title}
    </h1>
  );
}
```

### `components/layout/Header.tsx`
```tsx
'use client';

import { Menu, Bell, LogOut, User } from 'lucide-react';
import { useUIStore } from '@/store/ui';
import { useAuth } from '@/hooks/useAuth';
import { PageTitle } from './PageTitle';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function Header() {
  const { toggleSidebar } = useUIStore();
  const { user, logout } = useAuth();

  return (
    <header className="flex h-16 items-center gap-4 border-b bg-card px-4 md:px-6">
      {/* ── Hamburger (mobile only) ──────────────────────────────────── */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={toggleSidebar}
        aria-label="Open navigation menu"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* ── Page Title ──────────────────────────────────────────────── */}
      <div className="flex-1">
        <PageTitle />
      </div>

      {/* ── Actions ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Notification Bell */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Notifications (coming soon)"
              >
                <Bell className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Notifications coming soon</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* User Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full"
              aria-label="User menu"
            >
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs bg-primary text-primary-foreground">
                  {user ? getInitials(user.full_name) : 'U'}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">
                  {user?.full_name}
                </p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user?.email}
                </p>
              </div>
            </DropdownMenuLabel>

            <DropdownMenuSeparator />

            <DropdownMenuItem disabled className="gap-2">
              <User className="h-4 w-4" />
              <span>Profile settings</span>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              onClick={logout}
              className="gap-2 text-destructive focus:text-destructive"
            >
              <LogOut className="h-4 w-4" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
```

## Existing Files To Modify
- `components/ui/dropdown-menu.tsx` — must be created (Radix DropdownMenu wrapper)

### `components/ui/dropdown-menu.tsx`
```tsx
'use client';

import * as React from 'react';
import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu';
import { Check, ChevronRight, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';

const DropdownMenu = DropdownMenuPrimitive.Root;
const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;
const DropdownMenuGroup = DropdownMenuPrimitive.Group;
const DropdownMenuPortal = DropdownMenuPrimitive.Portal;
const DropdownMenuSub = DropdownMenuPrimitive.Sub;
const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup;

const DropdownMenuContent = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <DropdownMenuPrimitive.Portal>
    <DropdownMenuPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        'z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md',
        'data-[state=open]:animate-in data-[state=closed]:animate-out',
        'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
        'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
        'data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2',
        className,
      )}
      {...props}
    />
  </DropdownMenuPrimitive.Portal>
));
DropdownMenuContent.displayName = DropdownMenuPrimitive.Content.displayName;

const DropdownMenuItem = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Item> & {
    inset?: boolean;
  }
>(({ className, inset, ...props }, ref) => (
  <DropdownMenuPrimitive.Item
    ref={ref}
    className={cn(
      'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors',
      'focus:bg-accent focus:text-accent-foreground',
      'data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
      inset && 'pl-8',
      className,
    )}
    {...props}
  />
));
DropdownMenuItem.displayName = DropdownMenuPrimitive.Item.displayName;

const DropdownMenuLabel = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Label> & {
    inset?: boolean;
  }
>(({ className, inset, ...props }, ref) => (
  <DropdownMenuPrimitive.Label
    ref={ref}
    className={cn(
      'px-2 py-1.5 text-sm font-semibold',
      inset && 'pl-8',
      className,
    )}
    {...props}
  />
));
DropdownMenuLabel.displayName = DropdownMenuPrimitive.Label.displayName;

const DropdownMenuSeparator = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <DropdownMenuPrimitive.Separator
    ref={ref}
    className={cn('-mx-1 my-1 h-px bg-muted', className)}
    {...props}
  />
));
DropdownMenuSeparator.displayName = DropdownMenuPrimitive.Separator.displayName;

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuGroup,
  DropdownMenuPortal,
  DropdownMenuSub,
  DropdownMenuRadioGroup,
};
```

## API Contracts
None — UI component reads from auth store.

## Request Examples
Not applicable.

## Response Examples
Not applicable.

## Database Tables
Not applicable.

## Business Logic
- Page title resolution: exact path match first, then longest prefix match, then fallback to "FlowPilot AI".
- `getInitials` function: same as Sidebar — consider extracting to `lib/utils.ts` to avoid duplication.

## Validation Rules
Not applicable.

## Error Handling
- If `user` is null (protected route ensures it won't be): avatar shows "U" fallback.

## UI Behavior
- Header height: `h-16` (64px), fixed to top of content area
- Background: `bg-card` with bottom border
- Hamburger: visible only on mobile (`md:hidden`)
- Bell: visible on all viewports, non-functional, tooltip explains
- User dropdown: appears aligned to right edge (`align="end"`)
- "Profile settings" item is `disabled` (not yet implemented)
- "Sign out" text is destructive red color

## Component Breakdown
| Component | Responsibility |
|-----------|---------------|
| `Header` | Overall header bar |
| `PageTitle` | Route-aware title |
| `DropdownMenu` (Radix) | User action menu |

## State Management
- Reads: `useAuth().user`, `useAuth().logout`
- Writes: `useUIStore().toggleSidebar` (mobile only)

## Loading States
- User avatar shows initials immediately (no loading state needed — user is guaranteed by ProtectedRoute).

## Empty States
- No user name in dropdown: shows empty string (guarded by ProtectedRoute).

## Edge Cases
- Very long page titles on mobile: truncated at 200px (`truncate` + `max-w-[200px]`), full on sm+.
- User's `full_name` with only one word: `getInitials` returns single letter.

## Test Cases
1. Header renders with hamburger on mobile viewport.
2. Hamburger click toggles `sidebarOpen`.
3. User initials avatar shows correct letters.
4. Dropdown opens on avatar click.
5. "Sign out" in dropdown calls `logout()`.
6. `PageTitle` shows "Dashboard" on `/dashboard` path.
7. `PageTitle` shows "AI Inbox" on `/dashboard/inbox/123` path (prefix match).
8. Bell tooltip shows "Notifications coming soon".

## Acceptance Criteria
- [ ] Hamburger button shows on mobile, hidden on desktop
- [ ] Page title updates on route change
- [ ] User dropdown shows name, email, sign out
- [ ] Sign out action logs user out
- [ ] Bell icon present with tooltip
- [ ] No TypeScript errors

## Definition of Done
- All acceptance criteria checked
- `DropdownMenu` Radix wrapper complete
- `aria-label` on all icon buttons (accessibility)
