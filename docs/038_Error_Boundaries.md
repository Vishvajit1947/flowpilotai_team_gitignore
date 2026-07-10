# 038 – Error Boundaries

## Objective
Implement React Error Boundaries that catch unhandled rendering errors, display user-friendly fallback UIs, and log errors to the console (and optionally to a monitoring service). Covers global, page-level, and section-level boundaries.

## Scope
- `components/errors/ErrorBoundary.tsx` — reusable class-based error boundary
- `components/errors/GlobalError.tsx` — `app/global-error.tsx` (Next.js global error UI)
- `app/error.tsx` — Next.js route-level error boundary
- `components/errors/SectionError.tsx` — small inline error for card sections

## Out of Scope
- Backend error handling (003)
- API error handling in hooks (per-feature)
- Toast notifications (036)

## Functional Requirements
1. `ErrorBoundary` catches React rendering errors and shows fallback UI.
2. Fallback shows: error title, optional message, "Try again" reset button.
3. `app/global-error.tsx` handles root-level errors (replaces entire HTML).
4. `app/error.tsx` handles page-level errors with a "Go to Dashboard" option.
5. `SectionError` is a small inline error for individual sections/cards.
6. Reset button clears error state (attempts re-render).
7. Errors logged to `console.error`.

## Technical Requirements
- React class component (required for `componentDidCatch`)
- Next.js `'use client'` directive
- TypeScript
- `app/global-error.tsx` and `app/error.tsx` per Next.js App Router spec

## Folder Structure
```
frontend/
├── app/
│   ├── global-error.tsx
│   └── error.tsx
└── components/
    └── errors/
        ├── ErrorBoundary.tsx
        ├── SectionError.tsx
        └── ErrorFallback.tsx
```

## Files To Create

### `components/errors/ErrorFallback.tsx`
```tsx
import { AlertCircle, RefreshCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorFallbackProps {
  title?: string;
  message?: string;
  onReset?: () => void;
  showHomeButton?: boolean;
}

export function ErrorFallback({
  title = 'Something went wrong',
  message = 'An unexpected error occurred. Please try again.',
  onReset,
  showHomeButton = false,
}: ErrorFallbackProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
        <AlertCircle className="h-6 w-6 text-destructive" />
      </div>
      <div>
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      </div>
      <div className="flex gap-3">
        {onReset && (
          <Button onClick={onReset} variant="outline" className="gap-2">
            <RefreshCcw className="h-4 w-4" />
            Try again
          </Button>
        )}
        {showHomeButton && (
          <Button asChild>
            <a href="/dashboard">Go to Dashboard</a>
          </Button>
        )}
      </div>
    </div>
  );
}
```

### `components/errors/ErrorBoundary.tsx`
```tsx
'use client';

import React from 'react';
import { ErrorFallback } from './ErrorFallback';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  title?: string;
  message?: string;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <ErrorFallback
          title={this.props.title ?? 'Something went wrong'}
          message={this.props.message ?? this.state.error?.message}
          onReset={this.handleReset}
        />
      );
    }
    return this.props.children;
  }
}
```

### `components/errors/SectionError.tsx`
```tsx
import { AlertCircle, RefreshCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SectionErrorProps {
  message?: string;
  onRetry?: () => void;
}

export function SectionError({
  message = 'Failed to load this section',
  onRetry,
}: SectionErrorProps) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3">
      <div className="flex items-center gap-2">
        <AlertCircle className="h-4 w-4 flex-shrink-0 text-destructive" />
        <p className="text-sm text-destructive">{message}</p>
      </div>
      {onRetry && (
        <Button variant="ghost" size="sm" onClick={onRetry} className="gap-1.5 text-destructive hover:text-destructive">
          <RefreshCcw className="h-3 w-3" />
          Retry
        </Button>
      )}
    </div>
  );
}
```

### `app/error.tsx`
```tsx
'use client';

import { useEffect } from 'react';
import { AlertCircle, RefreshCcw, LayoutDashboard } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error('[Page Error]', error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 p-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
        <AlertCircle className="h-8 w-8 text-destructive" />
      </div>
      <div>
        <h2 className="text-2xl font-bold">Page Error</h2>
        <p className="mt-2 text-muted-foreground">
          Something went wrong loading this page.
        </p>
        {error.digest && (
          <p className="mt-1 text-xs text-muted-foreground/60">
            Error ID: {error.digest}
          </p>
        )}
      </div>
      <div className="flex gap-3">
        <Button onClick={reset} variant="outline" className="gap-2">
          <RefreshCcw className="h-4 w-4" />
          Try again
        </Button>
        <Button asChild>
          <a href="/dashboard" className="gap-2 inline-flex items-center">
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </a>
        </Button>
      </div>
    </div>
  );
}
```

### `app/global-error.tsx`
```tsx
'use client';

import { useEffect } from 'react';
import { AlertCircle, RefreshCcw } from 'lucide-react';

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

// Note: global-error.tsx replaces the root layout — must include <html> and <body>
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    console.error('[Global Error]', error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          gap: '24px',
          padding: '32px',
          textAlign: 'center',
          fontFamily: 'system-ui, sans-serif',
        }}>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>
            FlowPilot AI — Critical Error
          </h1>
          <p style={{ color: '#666' }}>
            A critical error occurred. Please refresh the page.
          </p>
          {error.digest && (
            <p style={{ fontSize: '12px', color: '#999' }}>
              Error ID: {error.digest}
            </p>
          )}
          <button
            onClick={reset}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: '1px solid #ddd',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            Refresh Page
          </button>
        </div>
      </body>
    </html>
  );
}
```

## Existing Files To Modify
- `components/layout/DashboardShell.tsx` — wrap `<main>` content in `<ErrorBoundary>`
- Sections with external data fetching — wrap in `<ErrorBoundary>` per card

## API Contracts
Not applicable.

## Database Tables
Not applicable.

## Business Logic
- `ErrorBoundary` resets on button click — clears `hasError` state and attempts re-render.
- `app/error.tsx` provides a `reset` function from Next.js that re-tries the segment.
- `global-error.tsx` must include `<html>` and `<body>` tags since it replaces the root layout.

## Validation Rules
Not applicable.

## Error Handling
This component IS the error handling.

## UI Behavior
- `ErrorFallback`: centered card with red icon, title, message, try-again button.
- `SectionError`: compact inline banner with retry.
- `app/error.tsx`: centered page-level error with digest ID.
- `global-error.tsx`: plain HTML (no Tailwind) since root layout CSS may be unavailable.

## Component Breakdown
| Component | Scope |
|-----------|-------|
| `ErrorBoundary` | Any React subtree |
| `ErrorFallback` | Visual fallback UI |
| `SectionError` | Inline section errors |
| `app/error.tsx` | Route-level errors |
| `app/global-error.tsx` | Root-level critical errors |

## State Management
- `ErrorBoundary` uses class-based state: `{ hasError, error }`.
- Reset clears state and re-renders children.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- Error in error boundary itself: React will catch this at the next higher boundary.
- `global-error.tsx` has no CSS → must use inline styles.
- `error.digest` may be undefined in development — rendered conditionally.
- Calling `reset()` multiple times is safe.

## Test Cases
1. Throwing in a child component triggers `ErrorBoundary` fallback.
2. Reset button clears error state.
3. `SectionError` renders message and retry button.
4. `app/error.tsx` renders with error digest.
5. `ErrorBoundary.componentDidCatch` calls `console.error`.
6. Custom `fallback` prop renders instead of default.

## Acceptance Criteria
- [ ] `ErrorBoundary` component catches rendering errors
- [ ] Reset button clears error and retries
- [ ] `app/error.tsx` route-level error page with Next.js reset
- [ ] `app/global-error.tsx` critical error with `<html>` tag
- [ ] `SectionError` inline error with retry

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Error boundaries added around major sections in DashboardShell
