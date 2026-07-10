# 033 – Workflow History

## Objective
Build the Workflow History page that shows a paginated, filterable list of all the user's past inbox submissions with their status, agent assignment, confidence score, and a drawer that opens the full workflow timeline for any selected submission.

## Scope
- `app/(dashboard)/dashboard/history/page.tsx` — history page
- `components/history/SubmissionTable.tsx` — paginated table of submissions
- `components/history/SubmissionDrawer.tsx` — slide-in details drawer
- `hooks/useSubmissionHistory.ts` — paginated data fetching
- Status filter (all / completed / failed / processing)

## Out of Scope
- Analytics (031)
- WorkflowViewer component (026 — reused here)

## Functional Requirements
1. Table shows: date, content preview (50 chars), status badge, agent badge, confidence %.
2. Pagination: 20 rows per page with Previous/Next buttons and page indicator.
3. Status filter above table: All, Completed, Failed, Processing, Pending.
4. Clicking a row opens a slide-in drawer with full submission details + workflow timeline.
5. Loading skeleton table while fetching.
6. Empty state when no submissions.

## Technical Requirements
- Next.js 15 App Router
- `GET /api/v1/inbox/?page=N&size=20` for data
- Status filter applied client-side (data fetched all at once for simplicity, since max display is 20)
- Framer Motion for drawer animation
- `WorkflowViewer` from 026

## Folder Structure
```
frontend/
├── app/
│   └── (dashboard)/
│       └── dashboard/
│           └── history/
│               └── page.tsx
├── components/
│   └── history/
│       ├── SubmissionTable.tsx
│       └── SubmissionDrawer.tsx
└── hooks/
    └── useSubmissionHistory.ts
```

## Files To Create

### `hooks/useSubmissionHistory.ts`
```typescript
'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { InboxSubmission, PaginatedResponse } from '@/types';

interface UseSubmissionHistoryResult {
  submissions: InboxSubmission[];
  total: number;
  page: number;
  pages: number;
  isLoading: boolean;
  error: string | null;
  setPage: (p: number) => void;
  refetch: () => void;
}

export function useSubmissionHistory(size = 20): UseSubmissionHistoryResult {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PaginatedResponse<InboxSubmission> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.get<PaginatedResponse<InboxSubmission>>(
        `/inbox/?page=${page}&size=${size}`,
      );
      setData(res.data);
    } catch {
      setError('Failed to load workflow history.');
    } finally {
      setIsLoading(false);
    }
  }, [page, size]);

  useEffect(() => { fetch(); }, [fetch]);

  return {
    submissions: data?.items ?? [],
    total: data?.total ?? 0,
    page,
    pages: data?.pages ?? 1,
    isLoading,
    error,
    setPage,
    refetch: fetch,
  };
}
```

### `components/history/SubmissionDrawer.tsx`
```tsx
'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { InboxSubmission, WorkflowStatus } from '@/types';
import { WorkflowViewer } from '@/components/workflow/WorkflowViewer';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { formatDateTime } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface SubmissionDrawerProps {
  submission: InboxSubmission | null;
  onClose: () => void;
}

const STATUS_STYLES: Record<WorkflowStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  processing: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
};

export function SubmissionDrawer({ submission, onClose }: SubmissionDrawerProps) {
  return (
    <AnimatePresence>
      {submission && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/40"
            onClick={onClose}
          />
          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed inset-y-0 right-0 z-50 flex w-full flex-col bg-card shadow-2xl sm:max-w-lg"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b px-6 py-4">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold">Submission Details</h2>
                <span className={cn('rounded-full px-2.5 py-1 text-xs font-medium', STATUS_STYLES[submission.status])}>
                  {submission.status}
                </span>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close drawer">
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Meta */}
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Submitted</p>
                  <p>{formatDateTime(submission.created_at)}</p>
                </div>
                {submission.assigned_agent && (
                  <div>
                    <p className="text-xs text-muted-foreground">Agent</p>
                    <p className="capitalize">{submission.assigned_agent} Agent</p>
                  </div>
                )}
                {submission.confidence_score !== null && (
                  <div>
                    <p className="text-xs text-muted-foreground">Confidence</p>
                    <p>{(submission.confidence_score * 100).toFixed(1)}%</p>
                  </div>
                )}
                {submission.detected_intent && (
                  <div>
                    <p className="text-xs text-muted-foreground">Intent</p>
                    <p>{submission.detected_intent.replace(/_/g, ' ')}</p>
                  </div>
                )}
              </div>

              <Separator />

              {/* Content */}
              <div>
                <p className="mb-2 text-xs font-medium text-muted-foreground">Original Message</p>
                <p className="text-sm whitespace-pre-wrap rounded-lg bg-muted/50 p-3">
                  {submission.content}
                </p>
              </div>

              {/* Error */}
              {submission.error_message && (
                <>
                  <Separator />
                  <div className="rounded-lg bg-destructive/10 p-3">
                    <p className="text-xs font-medium text-destructive mb-1">Error</p>
                    <p className="text-sm text-destructive">{submission.error_message}</p>
                  </div>
                </>
              )}

              {/* Workflow Timeline */}
              {submission.result?.steps && submission.result.steps.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <p className="mb-4 text-xs font-medium text-muted-foreground">Workflow Timeline</p>
                    <WorkflowViewer steps={submission.result.steps} />
                  </div>
                </>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

### `components/history/SubmissionTable.tsx`
```tsx
'use client';

import { useState } from 'react';
import { InboxSubmission, WorkflowStatus } from '@/types';
import { SubmissionDrawer } from './SubmissionDrawer';
import { useSubmissionHistory } from '@/hooks/useSubmissionHistory';
import { Button } from '@/components/ui/button';
import { formatDateTime, truncate } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { ChevronLeft, ChevronRight, RefreshCcw } from 'lucide-react';

const STATUS_FILTERS: { label: string; value: WorkflowStatus | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
  { label: 'Processing', value: 'processing' },
  { label: 'Pending', value: 'pending' },
];

const STATUS_COLORS: Record<WorkflowStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  processing: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
};

const AGENT_COLORS: Record<string, string> = {
  sales: 'bg-blue-100 text-blue-700',
  support: 'bg-green-100 text-green-700',
  finance: 'bg-purple-100 text-purple-700',
  executive: 'bg-orange-100 text-orange-700',
};

export function SubmissionTable() {
  const { submissions, total, page, pages, isLoading, error, setPage, refetch } =
    useSubmissionHistory();
  const [statusFilter, setStatusFilter] = useState<WorkflowStatus | 'all'>('all');
  const [selectedSubmission, setSelectedSubmission] = useState<InboxSubmission | null>(null);

  const filtered = statusFilter === 'all'
    ? submissions
    : submissions.filter((s) => s.status === statusFilter);

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border p-12">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" size="sm" onClick={refetch} className="gap-2">
          <RefreshCcw className="h-4 w-4" /> Retry
        </Button>
      </div>
    );
  }

  return (
    <>
      {/* Filter Bar */}
      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((f) => (
          <Button
            key={f.value}
            variant={statusFilter === f.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter(f.value)}
            className="h-8 text-xs"
          >
            {f.label}
          </Button>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Submitted</th>
              <th className="px-4 py-3 text-left font-medium">Content</th>
              <th className="px-4 py-3 text-left font-medium">Status</th>
              <th className="px-4 py-3 text-left font-medium hidden sm:table-cell">Agent</th>
              <th className="px-4 py-3 text-right font-medium hidden md:table-cell">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i} className="border-b">
                  {[1,2,3,4,5].map((j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 w-full animate-pulse rounded bg-muted" />
                    </td>
                  ))}
                </tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-muted-foreground">
                  No submissions found
                </td>
              </tr>
            ) : (
              filtered.map((s) => (
                <tr
                  key={s.id}
                  className="border-b cursor-pointer hover:bg-muted/40 transition-colors"
                  onClick={() => setSelectedSubmission(s)}
                >
                  <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                    {formatDateTime(s.created_at)}
                  </td>
                  <td className="px-4 py-3 max-w-xs">
                    <span className="truncate block">{truncate(s.content, 50)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', STATUS_COLORS[s.status])}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    {s.assigned_agent && (
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium capitalize', AGENT_COLORS[s.assigned_agent])}>
                        {s.assigned_agent}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right hidden md:table-cell text-xs">
                    {s.confidence_score !== null
                      ? `${(s.confidence_score * 100).toFixed(0)}%`
                      : '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {total} total submissions
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm">Page {page} of {pages}</span>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPage(page + 1)}
              disabled={page === pages}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <SubmissionDrawer
        submission={selectedSubmission}
        onClose={() => setSelectedSubmission(null)}
      />
    </>
  );
}
```

### `app/(dashboard)/dashboard/history/page.tsx`
```tsx
import { SubmissionTable } from '@/components/history/SubmissionTable';

export default function HistoryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Workflow History</h1>
        <p className="text-muted-foreground">
          Review all past AI-processed submissions and their outcomes.
        </p>
      </div>
      <SubmissionTable />
    </div>
  );
}
```

## Existing Files To Modify
None.

## API Contracts
- `GET /api/v1/inbox/?page=N&size=20` — see 016

## Database Tables
Not applicable.

## Business Logic
- Status filter applied client-side after fetching page data (20 rows max, acceptable).
- Drawer shows full workflow timeline from `submission.result.steps`.
- Clicking a row opens the drawer — row acts as a button.

## Validation Rules
Not applicable.

## Error Handling
| Scenario | UI |
|----------|-----|
| API error | Error message + retry |
| No submissions | "No submissions found" in table |
| Filtered to zero | "No submissions found" |

## UI Behavior
- Table: 5 columns (date, content, status, agent, confidence)
- Agent and confidence columns hidden on small screens
- Row hover: `bg-muted/40`
- Drawer: slides in from right, backdrop overlay, spring animation
- Drawer close: click backdrop, click X button

## Component Breakdown
| Component | Responsibility |
|-----------|---------------|
| `SubmissionTable` | Paginated table + filter |
| `SubmissionDrawer` | Detail slide-in drawer |
| `useSubmissionHistory` | Data fetching with pagination |

## State Management
- `page`: pagination state in hook
- `statusFilter`: local state in `SubmissionTable`
- `selectedSubmission`: local state for drawer

## Loading States
- Table: 5 skeleton rows with pulse animation

## Empty States
- No submissions: centered "No submissions found" in table
- Status filter produces no results: same empty state

## Edge Cases
- Content with newlines: `truncate()` cuts at 50 chars regardless.
- 0 confidence (unknown intent): shows "—" not "0%".
- Null assigned_agent: agent cell empty.
- Drawer opened then navigated away: `AnimatePresence` handles cleanup.

## Test Cases
1. Table renders with 5 skeleton rows while loading.
2. Table renders submissions list.
3. Clicking "Failed" filter shows only failed submissions.
4. Clicking a row opens drawer with submission details.
5. Clicking backdrop closes drawer.
6. Pagination buttons navigate pages.
7. Empty state shown when no submissions.
8. WorkflowViewer renders in drawer when steps available.

## Acceptance Criteria
- [ ] Paginated table with all columns
- [ ] Status filter works
- [ ] Drawer opens on row click with full details
- [ ] WorkflowViewer renders in drawer
- [ ] Pagination controls work
- [ ] Empty state displayed when no data

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Drawer accessible (`aria-label` on close button)
