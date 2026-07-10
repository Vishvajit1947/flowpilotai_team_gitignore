# 013 – Metric Cards

## Objective
Build the reusable `MetricCard` component and the `MetricsRow` layout used on the main dashboard page to display key performance indicators: total submissions, completed workflows, failed workflows, and average confidence score. Cards fetch data from the analytics summary API and display loading skeletons while fetching.

## Scope
- `components/dashboard/MetricCard.tsx` — single KPI card with icon, value, label, trend
- `components/dashboard/MetricsRow.tsx` — 4-card responsive grid
- `hooks/useAnalytics.ts` — data fetching hook for analytics summary
- Integration on `app/(dashboard)/dashboard/page.tsx`
- Skeleton loading state
- Animated count-up on value reveal

## Out of Scope
- Analytics charts (032)
- Analytics page (031)
- Full analytics API (030)

## Functional Requirements
1. Display 4 metric cards: Total Submissions, Completed, Failed, Avg Confidence.
2. Each card shows: icon, numeric value, label, optional trend badge.
3. While loading, show skeleton cards (gray pulse animation).
4. If API call fails, show error state with retry button.
5. Values animate from 0 to final value over 600ms on first load.
6. Confidence score displayed as percentage (e.g., `87.3%`).

## Technical Requirements
- Framer Motion for count-up animation
- `useAnalytics` hook using `api` Axios instance
- Shadcn `Card` component as base
- Tailwind CSS responsive grid (`grid-cols-1 sm:grid-cols-2 xl:grid-cols-4`)
- Lucide icons

## Folder Structure
```
frontend/
├── components/
│   └── dashboard/
│       ├── MetricCard.tsx
│       └── MetricsRow.tsx
└── hooks/
    └── useAnalytics.ts
```

## Files To Create

### `hooks/useAnalytics.ts`
```typescript
'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { AnalyticsSummary } from '@/types';

interface UseAnalyticsResult {
  data: AnalyticsSummary | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useAnalytics(): UseAnalyticsResult {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.get<AnalyticsSummary>('/analytics/summary');
      setData(res.data);
    } catch {
      setError('Failed to load analytics. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, isLoading, error, refetch: fetch };
}
```

### `components/dashboard/MetricCard.tsx`
```tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  label: string;
  value: number;
  icon: LucideIcon;
  format?: 'number' | 'percent';
  colorClass?: string;
  isLoading?: boolean;
}

function useCountUp(target: number, duration = 600): number {
  const [current, setCurrent] = useState(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (target === 0) {
      setCurrent(0);
      return;
    }
    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(eased * target));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);

  return current;
}

export function MetricCard({
  label,
  value,
  icon: Icon,
  format = 'number',
  colorClass = 'text-primary',
  isLoading = false,
}: MetricCardProps) {
  const animated = useCountUp(isLoading ? 0 : value);

  const displayValue =
    format === 'percent'
      ? `${(isLoading ? 0 : value * 100).toFixed(1)}%`
      : animated.toLocaleString();

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="space-y-3">
            <div className="h-9 w-9 animate-pulse rounded-lg bg-muted" />
            <div className="h-8 w-24 animate-pulse rounded bg-muted" />
            <div className="h-4 w-32 animate-pulse rounded bg-muted" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div
              className={cn(
                'flex h-9 w-9 items-center justify-center rounded-lg',
                'bg-primary/10',
              )}
            >
              <Icon className={cn('h-5 w-5', colorClass)} />
            </div>
            <div>
              <p className="text-2xl font-bold tracking-tight">{displayValue}</p>
              <p className="text-sm text-muted-foreground">{label}</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### `components/dashboard/MetricsRow.tsx`
```tsx
'use client';

import {
  Inbox,
  CheckCircle2,
  XCircle,
  TrendingUp,
  RefreshCcw,
} from 'lucide-react';
import { MetricCard } from './MetricCard';
import { useAnalytics } from '@/hooks/useAnalytics';
import { Button } from '@/components/ui/button';

export function MetricsRow() {
  const { data, isLoading, error, refetch } = useAnalytics();

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" size="sm" onClick={refetch} className="gap-2">
          <RefreshCcw className="h-4 w-4" />
          Retry
        </Button>
      </div>
    );
  }

  const metrics = [
    {
      label: 'Total Submissions',
      value: data?.total_submissions ?? 0,
      icon: Inbox,
      colorClass: 'text-blue-500',
    },
    {
      label: 'Completed',
      value: data?.completed ?? 0,
      icon: CheckCircle2,
      colorClass: 'text-green-500',
    },
    {
      label: 'Failed',
      value: data?.failed ?? 0,
      icon: XCircle,
      colorClass: 'text-red-500',
    },
    {
      label: 'Avg Confidence',
      value: data?.avg_confidence ?? 0,
      icon: TrendingUp,
      format: 'percent' as const,
      colorClass: 'text-purple-500',
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <MetricCard key={metric.label} {...metric} isLoading={isLoading} />
      ))}
    </div>
  );
}
```

### Update `app/(dashboard)/dashboard/page.tsx`
```tsx
import { MetricsRow } from '@/components/dashboard/MetricsRow';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to FlowPilot AI. Your AI-powered inbox is ready.
        </p>
      </div>
      <MetricsRow />
      {/* Charts added in 032 */}
    </div>
  );
}
```

## Existing Files To Modify
- `app/(dashboard)/dashboard/page.tsx` — add `<MetricsRow />`

## API Contracts

### `GET /api/v1/analytics/summary`
```
Method: GET
Path:   /api/v1/analytics/summary
Auth:   Bearer token required

Response 200:
{
  "total_submissions": 142,
  "completed": 128,
  "failed": 14,
  "avg_confidence": 0.873,
  "by_agent": {
    "sales": 45,
    "support": 61,
    "finance": 22,
    "executive": 14
  },
  "by_day": [
    { "date": "2024-01-15", "count": 18 },
    ...
  ]
}
```

## Request Examples
```bash
curl http://localhost:8000/api/v1/analytics/summary \
  -H "Authorization: Bearer <token>"
```

## Response Examples
```json
{
  "total_submissions": 142,
  "completed": 128,
  "failed": 14,
  "avg_confidence": 0.873,
  "by_agent": { "sales": 45, "support": 61, "finance": 22, "executive": 14 },
  "by_day": [{ "date": "2024-01-15", "count": 18 }]
}
```

## Database Tables
Not applicable — reads via API (analytics API defined in 030).

## Business Logic
- `avg_confidence` is stored as `0.873` (float 0–1); display multiplies by 100 → `87.3%`.
- Count-up animation uses ease-out cubic curve for a natural deceleration.
- Count-up only runs once on mount; no re-animation on polling/refresh.

## Validation Rules
- `value` prop must be a non-negative number; negative values display as-is.

## Error Handling
| Scenario | UI |
|----------|-----|
| API loading | Skeleton pulse cards |
| API error | Error banner with retry button |
| API returns zeros | Cards show 0 (valid state) |

## UI Behavior
- 4 cards in a responsive grid: 1 col on mobile, 2 on sm, 4 on xl.
- Each card: icon with colored background, large bold value, muted label.
- Hover: subtle shadow increase.
- Loading: pulse skeleton fills exact card dimensions.
- Error: replaces entire grid with a bordered error box + retry button.

## Component Breakdown
| Component | Props |
|-----------|-------|
| `MetricCard` | label, value, icon, format, colorClass, isLoading |
| `MetricsRow` | none (self-contained with hook) |

## State Management
- `useAnalytics` hook manages fetch state locally (no global store).
- Count-up animation uses `useState` + `useEffect` + `requestAnimationFrame`.

## Loading States
- Skeleton: 3 gray rectangles per card mimicking icon, value, label.
- Skeleton uses Tailwind `animate-pulse`.

## Empty States
- No zero-state message — cards showing `0` is valid and expected for new accounts.

## Edge Cases
- `avg_confidence` of `0` on new account: displays `0.0%` (valid).
- Very large numbers (e.g., 1,000,000): `toLocaleString()` formats with commas.
- Count-up with `value = 0`: animation skips immediately to `0`.
- Rapid re-renders: `cancelAnimationFrame` cleanup in `useCountUp` prevents memory leaks.

## Test Cases
1. `MetricCard` renders label, value, and icon.
2. `MetricCard` with `isLoading=true` renders skeleton.
3. Count-up starts at 0 and reaches target value after 600ms.
4. `format="percent"` shows value multiplied by 100 with `%` suffix.
5. `useAnalytics` returns data from successful API call.
6. `useAnalytics` returns error string on network failure.
7. Retry button in error state calls `refetch`.
8. `MetricsRow` renders 4 cards.

## Acceptance Criteria
- [ ] 4 metric cards display correct values from API
- [ ] Skeleton loading state shown during fetch
- [ ] Error state with retry button shown on failure
- [ ] Count-up animation plays on load
- [ ] Confidence score formatted as percentage
- [ ] Responsive grid layout works at all breakpoints

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- `requestAnimationFrame` cleanup prevents memory leaks
