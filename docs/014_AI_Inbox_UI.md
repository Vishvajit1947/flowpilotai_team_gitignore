# 014 – AI Inbox UI

## Objective
Build the complete AI Inbox page UI — a two-panel layout with a text/file input form on the left and a live results panel on the right. Users submit text messages or uploaded files, the UI posts to the backend, polls for workflow completion, and displays the agent's response with intent, confidence score, assigned agent, and structured result.

## Scope
- `app/(dashboard)/dashboard/inbox/page.tsx` — inbox page
- `components/inbox/InboxForm.tsx` — submission form (text + file)
- `components/inbox/ResultPanel.tsx` — displays workflow result
- `components/inbox/SubmissionHistory.tsx` — recent submissions list
- `hooks/useInboxSubmit.ts` — submit + poll hook
- `store/inbox.ts` — Zustand store for submission state

## Out of Scope
- File upload component (015 — referenced here but built there)
- Backend submit API (016)
- Intent detection logic (017)
- Agent implementations (021-024)

## Functional Requirements
1. Text area (min 3 chars, max 5000 chars) with character counter.
2. Optional file attachment (delegated to FileUpload component from 015).
3. Submit button disabled when text is empty or while processing.
4. After submission, show processing state with spinner and status message.
5. Poll `GET /api/v1/inbox/{id}` every 2 seconds until status is `completed` or `failed`.
6. On completion, show: detected intent, confidence bar, assigned agent badge, result content.
7. On failure, show error message from `error_message` field.
8. Recent submissions list below the form (last 5, newest first).

## Technical Requirements
- Next.js 15 App Router (`'use client'`)
- Axios for API calls
- Zustand for submission list state
- Framer Motion for result panel slide-in
- Polling via `setInterval` with automatic cleanup

## Folder Structure
```
frontend/
├── app/
│   └── (dashboard)/
│       └── dashboard/
│           └── inbox/
│               └── page.tsx
├── components/
│   └── inbox/
│       ├── InboxForm.tsx
│       ├── ResultPanel.tsx
│       └── SubmissionHistory.tsx
├── hooks/
│   └── useInboxSubmit.ts
└── store/
    └── inbox.ts
```

## Files To Create

### `store/inbox.ts`
```typescript
import { create } from 'zustand';
import { InboxSubmission } from '@/types';

interface InboxState {
  submissions: InboxSubmission[];
  currentSubmission: InboxSubmission | null;
  isPolling: boolean;
}

interface InboxActions {
  addSubmission: (s: InboxSubmission) => void;
  updateSubmission: (s: InboxSubmission) => void;
  setCurrentSubmission: (s: InboxSubmission | null) => void;
  setPolling: (v: boolean) => void;
}

export const useInboxStore = create<InboxState & InboxActions>((set) => ({
  submissions: [],
  currentSubmission: null,
  isPolling: false,

  addSubmission: (s) =>
    set((state) => ({ submissions: [s, ...state.submissions].slice(0, 20) })),
  updateSubmission: (s) =>
    set((state) => ({
      submissions: state.submissions.map((sub) => (sub.id === s.id ? s : sub)),
      currentSubmission:
        state.currentSubmission?.id === s.id ? s : state.currentSubmission,
    })),
  setCurrentSubmission: (s) => set({ currentSubmission: s }),
  setPolling: (v) => set({ isPolling: v }),
}));
```

### `hooks/useInboxSubmit.ts`
```typescript
'use client';

import { useCallback, useRef } from 'react';
import api from '@/lib/api';
import { InboxSubmission } from '@/types';
import { useInboxStore } from '@/store/inbox';

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 120_000; // 2 minutes max

export function useInboxSubmit() {
  const { addSubmission, updateSubmission, setCurrentSubmission, setPolling } =
    useInboxStore();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    pollRef.current = null;
    timeoutRef.current = null;
    setPolling(false);
  }, [setPolling]);

  const pollStatus = useCallback(
    (id: string) => {
      setPolling(true);
      pollRef.current = setInterval(async () => {
        try {
          const res = await api.get<InboxSubmission>(`/inbox/${id}`);
          const updated = res.data;
          updateSubmission(updated);

          if (
            updated.status === 'completed' ||
            updated.status === 'failed'
          ) {
            stopPolling();
          }
        } catch {
          stopPolling();
        }
      }, POLL_INTERVAL_MS);

      // Safety timeout
      timeoutRef.current = setTimeout(() => {
        stopPolling();
      }, POLL_TIMEOUT_MS);
    },
    [setPolling, updateSubmission, stopPolling],
  );

  const submit = useCallback(
    async (content: string, fileUrl?: string): Promise<void> => {
      const res = await api.post<InboxSubmission>('/inbox/submit', {
        content,
        file_url: fileUrl ?? null,
      });
      const submission = res.data;
      addSubmission(submission);
      setCurrentSubmission(submission);
      pollStatus(submission.id);
    },
    [addSubmission, setCurrentSubmission, pollStatus],
  );

  return { submit, stopPolling };
}
```

### `components/inbox/InboxForm.tsx`
```tsx
'use client';

import { useState, useRef } from 'react';
import { Send, Paperclip } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useInboxSubmit } from '@/hooks/useInboxSubmit';
import { useInboxStore } from '@/store/inbox';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

const MAX_CHARS = 5000;
const MIN_CHARS = 3;

export function InboxForm() {
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { submit } = useInboxSubmit();
  const isPolling = useInboxStore((s) => s.isPolling);

  const charCount = content.length;
  const isOverLimit = charCount > MAX_CHARS;
  const canSubmit = charCount >= MIN_CHARS && !isOverLimit && !isSubmitting && !isPolling;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setIsSubmitting(true);
    try {
      await submit(content.trim());
      setContent('');
    } catch {
      toast.error('Failed to submit. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="relative">
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Describe your request, paste an email, or ask a question…"
          className={cn(
            'min-h-[160px] resize-none pr-4 pb-8',
            isOverLimit && 'border-destructive focus-visible:ring-destructive',
          )}
          disabled={isSubmitting || isPolling}
          aria-label="Message input"
          aria-describedby="char-counter"
        />
        <span
          id="char-counter"
          className={cn(
            'absolute bottom-3 right-3 text-xs',
            isOverLimit ? 'text-destructive' : 'text-muted-foreground',
          )}
        >
          {charCount}/{MAX_CHARS}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="gap-2 text-muted-foreground"
          disabled
          aria-label="Attach file (coming in next step)"
        >
          <Paperclip className="h-4 w-4" />
          Attach file
        </Button>

        <Button
          type="submit"
          disabled={!canSubmit}
          className="gap-2"
        >
          {isSubmitting || isPolling ? (
            <>
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Processing…
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              Send to AI
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
```

### `components/inbox/ResultPanel.tsx`
```tsx
'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useInboxStore } from '@/store/inbox';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, XCircle, Clock, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDateTime } from '@/lib/utils';
import type { AgentType, WorkflowStatus } from '@/types';

const AGENT_COLORS: Record<AgentType, string> = {
  sales: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  support: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  finance: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  executive: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
};

const STATUS_ICONS: Record<WorkflowStatus, React.ReactNode> = {
  pending: <Clock className="h-4 w-4 text-muted-foreground" />,
  processing: (
    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
  ),
  completed: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  failed: <XCircle className="h-4 w-4 text-destructive" />,
};

export function ResultPanel() {
  const currentSubmission = useInboxStore((s) => s.currentSubmission);
  const isPolling = useInboxStore((s) => s.isPolling);

  return (
    <AnimatePresence mode="wait">
      {!currentSubmission ? (
        <motion.div
          key="empty"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed p-12 text-center"
        >
          <Brain className="h-12 w-12 text-muted-foreground/40" />
          <div>
            <p className="font-medium text-muted-foreground">No submission yet</p>
            <p className="text-sm text-muted-foreground/70">
              Submit a message to see the AI&apos;s analysis
            </p>
          </div>
        </motion.div>
      ) : (
        <motion.div
          key={currentSubmission.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
        >
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Analysis Result</CardTitle>
                <div className="flex items-center gap-2">
                  {STATUS_ICONS[currentSubmission.status]}
                  <span className="text-sm capitalize text-muted-foreground">
                    {currentSubmission.status}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Agent + Intent */}
              {currentSubmission.assigned_agent && (
                <div className="flex flex-wrap gap-2">
                  <span
                    className={cn(
                      'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
                      AGENT_COLORS[currentSubmission.assigned_agent],
                    )}
                  >
                    {currentSubmission.assigned_agent.charAt(0).toUpperCase() +
                      currentSubmission.assigned_agent.slice(1)}{' '}
                    Agent
                  </span>
                  {currentSubmission.detected_intent && (
                    <Badge variant="outline">{currentSubmission.detected_intent}</Badge>
                  )}
                </div>
              )}

              {/* Confidence Score */}
              {currentSubmission.confidence_score !== null && (
                <div className="space-y-1.5">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Confidence</span>
                    <span className="font-medium">
                      {(currentSubmission.confidence_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <Progress
                    value={currentSubmission.confidence_score * 100}
                    className="h-2"
                  />
                </div>
              )}

              {/* Result Content */}
              {currentSubmission.status === 'completed' && currentSubmission.result && (
                <div className="rounded-lg bg-muted/50 p-4">
                  <pre className="whitespace-pre-wrap text-sm font-sans">
                    {typeof currentSubmission.result === 'string'
                      ? currentSubmission.result
                      : JSON.stringify(currentSubmission.result, null, 2)}
                  </pre>
                </div>
              )}

              {/* Error */}
              {currentSubmission.status === 'failed' && (
                <div className="rounded-lg bg-destructive/10 p-4">
                  <p className="text-sm text-destructive">
                    {currentSubmission.error_message ?? 'An error occurred during processing.'}
                  </p>
                </div>
              )}

              {/* Processing indicator */}
              {isPolling && currentSubmission.status === 'processing' && (
                <p className="text-xs text-muted-foreground">
                  Processing your request…
                </p>
              )}

              <p className="text-xs text-muted-foreground">
                Submitted {formatDateTime(currentSubmission.created_at)}
              </p>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

### `components/inbox/SubmissionHistory.tsx`
```tsx
'use client';

import { useInboxStore } from '@/store/inbox';
import { formatDateTime } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-700',
  processing: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
};

export function SubmissionHistory() {
  const { submissions, setCurrentSubmission } = useInboxStore();

  if (submissions.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-muted-foreground">Recent Submissions</h3>
      <div className="space-y-2">
        {submissions.slice(0, 5).map((s) => (
          <button
            key={s.id}
            onClick={() => setCurrentSubmission(s)}
            className={cn(
              'w-full rounded-lg border p-3 text-left transition-colors',
              'hover:bg-accent hover:border-accent-foreground/20',
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <p className="truncate text-sm">{s.content.slice(0, 60)}…</p>
              <span
                className={cn(
                  'flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                  STATUS_COLORS[s.status],
                )}
              >
                {s.status}
              </span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {formatDateTime(s.created_at)}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
```

### `app/(dashboard)/dashboard/inbox/page.tsx`
```tsx
import { InboxForm } from '@/components/inbox/InboxForm';
import { ResultPanel } from '@/components/inbox/ResultPanel';
import { SubmissionHistory } from '@/components/inbox/SubmissionHistory';

export default function InboxPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">AI Inbox</h1>
        <p className="text-muted-foreground">
          Submit text or documents — AI routes them to the right agent automatically.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <InboxForm />
          <SubmissionHistory />
        </div>
        <ResultPanel />
      </div>
    </div>
  );
}
```

## Existing Files To Modify
- `components/ui/` — add `Textarea`, `Badge`, `Progress` Shadcn components (see below)

### `components/ui/textarea.tsx`
```tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      'flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
      className,
    )}
    {...props}
  />
));
Textarea.displayName = 'Textarea';
export { Textarea };
```

## API Contracts

### `POST /api/v1/inbox/submit`
```
Method: POST
Auth:   Bearer token
Body:   { "content": "string", "file_url": "string|null" }
Response 201: InboxSubmission object
```

### `GET /api/v1/inbox/{id}`
```
Method: GET
Auth:   Bearer token
Response 200: InboxSubmission object with updated status/result
```

## Request Examples
```json
POST /api/v1/inbox/submit
{ "content": "We have a new enterprise lead from Acme Corp…", "file_url": null }
```

## Response Examples
```json
{
  "id": "uuid",
  "status": "processing",
  "content": "We have a new enterprise lead from Acme Corp…",
  "detected_intent": null,
  "confidence_score": null,
  "assigned_agent": null,
  "result": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

## Database Tables
Reads/writes `inbox_submissions` via API.

## Business Logic
- Polling stops when `status` is `completed` or `failed`.
- Polling safety timeout of 2 minutes prevents infinite polling.
- At most 20 recent submissions stored in Zustand (in-memory, not persisted).
- Clicking a history item updates `currentSubmission` to show its result.

## Validation Rules
- Content: min 3 chars, max 5000 chars (client-side); backend re-validates.
- Submit blocked while already processing (`isPolling === true`).

## Error Handling
| Scenario | UI |
|----------|-----|
| Submit fails (network) | Toast: "Failed to submit. Please try again." |
| Poll fails | Polling stops, last known status shown |
| Workflow fails | Red error box with `error_message` |
| 2-minute timeout | Polling stops, status stays as-is |

## UI Behavior
- Two-column layout on lg+, single column on mobile.
- Form occupies full left column; result panel on the right.
- Result panel slides in from the right when a new submission is created.
- Processing status shows spinning indicator.

## Component Breakdown
| Component | Responsibility |
|-----------|---------------|
| `InboxForm` | Text input + submit |
| `ResultPanel` | Display submission result |
| `SubmissionHistory` | Recent submissions list |
| `useInboxSubmit` | POST + polling logic |
| `useInboxStore` | State management |

## State Management
```typescript
{
  submissions: InboxSubmission[],   // last 20
  currentSubmission: InboxSubmission | null,
  isPolling: boolean,
}
```

## Loading States
- Submit button: spinner + "Processing…"
- ResultPanel during polling: spinner icon + "Processing your request…"
- Polling uses existing submission data updated in-place

## Empty States
- No current submission: dashed border box with brain icon and helper text
- No history: history section hidden entirely

## Edge Cases
- User navigates away during polling: polling continues in background (acceptable); on return, store still has latest submission.
- Rapid form submits: button disabled while `isPolling` prevents double submission.
- Very long `content` in history list: truncated at 60 chars with ellipsis.
- `result` field is an object: stringified with JSON.stringify for display.

## Test Cases
1. Form submits content via POST to `/inbox/submit`.
2. Submit button disabled when content < 3 chars.
3. Submit button disabled while `isPolling = true`.
4. Polling calls GET `/inbox/{id}` every 2 seconds.
5. Polling stops when status becomes `completed`.
6. Polling stops when status becomes `failed`.
7. Polling stops after 2 minutes (safety timeout).
8. ResultPanel shows empty state when no submission.
9. ResultPanel shows agent badge and confidence bar on completed submission.
10. Clicking history item updates `currentSubmission`.

## Acceptance Criteria
- [ ] Form submits text content to API
- [ ] Polling mechanism updates result in real time
- [ ] Result panel displays intent, agent, confidence, result
- [ ] Error state displays backend error message
- [ ] Recent submissions list shows last 5
- [ ] No double submissions possible

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Polling cleanup on component unmount (no memory leaks)
