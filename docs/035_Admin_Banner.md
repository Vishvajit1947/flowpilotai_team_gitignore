# 035 – Admin Banner

## Objective
Build the frontend admin control panel as a dismissible banner/panel visible only to users with `role = 'admin'`. It provides buttons to reset demo data and seed demo submissions, showing confirmation dialogs before destructive operations.

## Scope
- `components/admin/AdminBanner.tsx` — admin-only control panel
- `hooks/useAdminActions.ts` — API calls for admin operations
- Integration into dashboard layout (conditionally rendered for admins)
- Confirmation dialog before reset (destructive)

## Out of Scope
- Admin API endpoints (034)
- User management UI
- Access control logic (handled by 009)

## Functional Requirements
1. Banner only visible to users with `role = 'admin'`.
2. "Reset Demo" button: opens confirmation dialog, then calls `POST /admin/reset-demo`.
3. "Seed Demo" button: calls `POST /admin/seed-demo` immediately (non-destructive).
4. After operations: toast notification (success or error).
5. Loading state on each button while operation in progress.
6. Banner dismissible (close button, persists dismissed state in session).

## Technical Requirements
- `useAuth` hook to check `user.role === 'admin'`
- Shadcn `Dialog` for confirmation
- `sonner` toast for feedback
- Axios via `api` client

## Folder Structure
```
frontend/
├── components/
│   └── admin/
│       └── AdminBanner.tsx
└── hooks/
    └── useAdminActions.ts
```

## Files To Create

### `hooks/useAdminActions.ts`
```typescript
'use client';

import { useState } from 'react';
import api from '@/lib/api';
import { toast } from 'sonner';

export function useAdminActions() {
  const [isResetting, setIsResetting] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);

  const resetDemo = async () => {
    setIsResetting(true);
    try {
      const res = await api.post<{ deleted_rows: number }>('/admin/reset-demo');
      toast.success(`Demo reset: ${res.data.deleted_rows} submissions deleted`);
    } catch {
      toast.error('Failed to reset demo data');
    } finally {
      setIsResetting(false);
    }
  };

  const seedDemo = async () => {
    setIsSeeding(true);
    try {
      const res = await api.post<{ seeded_rows: number }>('/admin/seed-demo');
      toast.success(`Demo seeded: ${res.data.seeded_rows} submissions added`);
    } catch {
      toast.error('Failed to seed demo data');
    } finally {
      setIsSeeding(false);
    }
  };

  return { resetDemo, seedDemo, isResetting, isSeeding };
}
```

### `components/admin/AdminBanner.tsx`
```tsx
'use client';

import { useState } from 'react';
import { Shield, Trash2, Sparkles, X, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useAdminActions } from '@/hooks/useAdminActions';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export function AdminBanner() {
  const { user } = useAuth();
  const { resetDemo, seedDemo, isResetting, isSeeding } = useAdminActions();
  const [dismissed, setDismissed] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  // Only show for admin users
  if (!user || user.role !== 'admin' || dismissed) return null;

  const handleReset = async () => {
    setConfirmOpen(false);
    await resetDemo();
  };

  return (
    <>
      <div className="flex items-center justify-between rounded-lg border border-orange-200 bg-orange-50 px-4 py-3 dark:border-orange-800/50 dark:bg-orange-900/20">
        <div className="flex items-center gap-3">
          <Shield className="h-5 w-5 flex-shrink-0 text-orange-500" />
          <div>
            <p className="text-sm font-medium text-orange-700 dark:text-orange-300">
              Admin Controls
            </p>
            <p className="text-xs text-orange-600/70 dark:text-orange-400/70">
              You have administrator access
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={seedDemo}
            disabled={isSeeding || isResetting}
            className="gap-2 border-orange-200 text-orange-700 hover:bg-orange-100 dark:border-orange-700 dark:text-orange-300"
          >
            {isSeeding ? (
              <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : (
              <Sparkles className="h-3 w-3" />
            )}
            Seed Demo
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setConfirmOpen(true)}
            disabled={isResetting || isSeeding}
            className="gap-2 border-red-200 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400"
          >
            {isResetting ? (
              <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : (
              <Trash2 className="h-3 w-3" />
            )}
            Reset Demo
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-orange-500"
            onClick={() => setDismissed(true)}
            aria-label="Dismiss admin banner"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Confirm Reset Dialog */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Confirm Demo Reset
            </DialogTitle>
            <DialogDescription>
              This will permanently delete ALL inbox submissions from the database.
              Users and their accounts will not be affected. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleReset} disabled={isResetting}>
              {isResetting ? 'Resetting…' : 'Yes, reset all submissions'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

## Files To Modify

### `components/layout/DashboardShell.tsx` (from 010) — add AdminBanner inside main area
```tsx
// Add AdminBanner import
import { AdminBanner } from '@/components/admin/AdminBanner';

// Inside the <main> element, add AdminBanner at the top:
<main id="main-content" className="flex-1 overflow-y-auto p-6" tabIndex={-1}>
  <div className="mb-6">
    <AdminBanner />
  </div>
  {children}
</main>
```

## API Contracts
- `POST /api/v1/admin/reset-demo` — see 034
- `POST /api/v1/admin/seed-demo` — see 034

## Database Tables
Not applicable — frontend only.

## Business Logic
- Banner only renders for `user.role === 'admin'` — zero-render for regular users.
- `dismissed` state is `useState` (session-scoped) — reappears on page reload (intentional for accessibility).
- Reset requires confirmation dialog — "Seed" does not (non-destructive).

## Validation Rules
- Role check: `user?.role === 'admin'` — must both be truthy.

## Error Handling
| Scenario | UI |
|----------|-----|
| Reset API error | Toast: "Failed to reset demo data" |
| Seed API error | Toast: "Failed to seed demo data" |
| Non-admin (fallback) | Component returns `null` |

## UI Behavior
- Orange-themed banner (admin warning color)
- Dismiss button (X) hides until page reload
- Confirmation modal for destructive reset
- Seed is instant (no confirmation)
- Both buttons disabled while either operation is in-progress
- Loading spinners replace icons during operation

## Component Breakdown
| Component | Responsibility |
|-----------|---------------|
| `AdminBanner` | UI + dialog trigger |
| `useAdminActions` | API calls + loading state |

## State Management
- `dismissed`: local `useState`
- `confirmOpen`: local `useState`
- `isResetting`, `isSeeding`: from hook

## Loading States
- Seed/Reset buttons: spinner replaces icon, text may change

## Empty States
Not applicable.

## Edge Cases
- Admin user logs out and back in: banner reappears (session-scoped dismiss).
- Regular user visits admin page: returns `null` — no flash.
- Both buttons simultaneously clicked: both disabled when either is loading.
- Dialog X button cancels reset without action.

## Test Cases
1. Admin user sees banner.
2. Regular user (`role='user'`) sees no banner.
3. Dismiss X hides banner.
4. "Seed Demo" calls API without confirmation.
5. "Reset Demo" opens confirmation dialog.
6. Confirming reset calls `POST /admin/reset-demo`.
7. Cancelling confirmation closes dialog without API call.
8. Success toast shown after seed.
9. Error toast shown on API failure.

## Acceptance Criteria
- [ ] Banner only visible to admin users
- [ ] Confirmation dialog required before reset
- [ ] Toast feedback after operations
- [ ] Loading states on buttons
- [ ] Dismiss button works

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Dialog component (`components/ui/dialog.tsx`) created (Radix Dialog wrapper)
