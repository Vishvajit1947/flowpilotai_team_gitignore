# 037 – Loading States

## Objective
Implement a complete loading state design system: skeleton loaders, full-page loading screen, inline spinners, button loading states, and a `Skeleton` component — ensuring consistent loading UX across the entire application.

## Scope
- `components/ui/skeleton.tsx` — Shadcn Skeleton primitive
- `components/ui/spinner.tsx` — reusable spinner component
- `components/loading/PageLoader.tsx` — full-page loading screen
- `components/loading/TableSkeleton.tsx` — table skeleton
- `components/loading/CardSkeleton.tsx` — generic card skeleton
- Loading state patterns documented for all major views

## Out of Scope
- Individual feature loading states (documented in respective task docs)
- Suspense boundaries (handled by Next.js)

## Functional Requirements
1. `Skeleton` component renders a gray pulse rectangle of configurable size.
2. `Spinner` component renders a spinning circle of configurable size.
3. `PageLoader` renders a full-viewport centered loading screen with branding.
4. `TableSkeleton` renders N skeleton rows matching a table layout.
5. `CardSkeleton` renders a card outline with skeleton content blocks.
6. All loading components accessible (aria attributes).

## Technical Requirements
- Tailwind CSS `animate-pulse` for skeletons
- CSS animation for spinner (not a library)
- All components accept `className` prop

## Folder Structure
```
frontend/
└── components/
    ├── ui/
    │   ├── skeleton.tsx
    │   └── spinner.tsx
    └── loading/
        ├── PageLoader.tsx
        ├── TableSkeleton.tsx
        └── CardSkeleton.tsx
```

## Files To Create

### `components/ui/skeleton.tsx`
```tsx
import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  'aria-label'?: string;
}

export function Skeleton({ className, ...props }: SkeletonProps & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-muted', className)}
      aria-hidden="true"
      {...props}
    />
  );
}
```

### `components/ui/spinner.tsx`
```tsx
import { cn } from '@/lib/utils';
import { cva, type VariantProps } from 'class-variance-authority';

const spinnerVariants = cva(
  'animate-spin rounded-full border-2 border-current border-t-transparent',
  {
    variants: {
      size: {
        sm: 'h-4 w-4',
        md: 'h-6 w-6',
        lg: 'h-8 w-8',
        xl: 'h-12 w-12',
      },
    },
    defaultVariants: { size: 'md' },
  },
);

interface SpinnerProps extends VariantProps<typeof spinnerVariants> {
  className?: string;
  label?: string;
}

export function Spinner({ size, className, label = 'Loading' }: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label={label}
      className={cn(spinnerVariants({ size }), className)}
    />
  );
}
```

### `components/loading/PageLoader.tsx`
```tsx
import { Spinner } from '@/components/ui/spinner';

interface PageLoaderProps {
  message?: string;
}

export function PageLoader({ message = 'Loading…' }: PageLoaderProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background"
      role="status"
      aria-label={message}
    >
      <div className="flex items-center gap-2">
        <span className="text-xl font-bold">FlowPilot</span>
        <span className="text-xl font-bold text-primary">AI</span>
      </div>
      <Spinner size="lg" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
```

### `components/loading/CardSkeleton.tsx`
```tsx
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

interface CardSkeletonProps {
  lines?: number;
  className?: string;
}

export function CardSkeleton({ lines = 3, className }: CardSkeletonProps) {
  return (
    <Card className={className} aria-busy="true" aria-label="Loading">
      <CardHeader>
        <Skeleton className="h-5 w-1/3" />
        <Skeleton className="h-4 w-2/3" />
      </CardHeader>
      <CardContent className="space-y-3">
        {[...Array(lines)].map((_, i) => (
          <Skeleton
            key={i}
            className={`h-4 ${i === lines - 1 ? 'w-2/3' : 'w-full'}`}
          />
        ))}
      </CardContent>
    </Card>
  );
}
```

### `components/loading/TableSkeleton.tsx`
```tsx
import { Skeleton } from '@/components/ui/skeleton';

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export function TableSkeleton({ rows = 5, columns = 5 }: TableSkeletonProps) {
  return (
    <div className="rounded-xl border overflow-hidden" aria-busy="true" aria-label="Loading table">
      <table className="w-full">
        <thead className="border-b bg-muted/50">
          <tr>
            {[...Array(columns)].map((_, i) => (
              <th key={i} className="px-4 py-3">
                <Skeleton className="h-4 w-16" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...Array(rows)].map((_, rowIdx) => (
            <tr key={rowIdx} className="border-b">
              {[...Array(columns)].map((_, colIdx) => (
                <td key={colIdx} className="px-4 py-3">
                  <Skeleton className={`h-4 ${colIdx === 0 ? 'w-24' : 'w-full'}`} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

## Existing Files To Modify
- `components/auth/ProtectedRoute.tsx` — replace inline spinner with `<Spinner size="lg" />` and `<PageLoader />` for full-page auth loading
- Any component with inline `animate-pulse` div that could be replaced with `<Skeleton />`

## API Contracts
Not applicable — UI components only.

## Request Examples
```tsx
// Spinner
<Spinner size="sm" />  // inline in buttons
<Spinner size="md" />  // default
<Spinner size="lg" />  // auth loading
<Spinner size="xl" />  // page-level loading

// Skeleton
<Skeleton className="h-4 w-32" />          // text line
<Skeleton className="h-9 w-9 rounded-lg" /> // icon
<Skeleton className="h-64 w-full" />        // chart area

// Page loader
<PageLoader message="Authenticating…" />

// Card skeleton
<CardSkeleton lines={4} />

// Table skeleton
<TableSkeleton rows={10} columns={5} />
```

## Response Examples
Not applicable.

## Database Tables
Not applicable.

## Business Logic
- `Skeleton` has `aria-hidden="true"` — screen readers skip decorative loading shapes.
- Containers using skeletons should have `aria-busy="true"` and `aria-label="Loading"`.
- `PageLoader` is `fixed` with `z-50` — appears above everything.

## Validation Rules
Not applicable.

## Error Handling
Not applicable.

## UI Behavior
- Skeleton: gray rectangle with pulsing opacity animation.
- Spinner: rotating circle with 2px border, transparent top segment.
- PageLoader: full-screen centered with brand name + large spinner + message.
- CardSkeleton: card shape with skeleton header (title + description) + N content lines.
- TableSkeleton: bordered table with skeleton headers and rows.

## Component Breakdown
| Component | Use Case |
|-----------|---------|
| `Skeleton` | Individual text/image placeholders |
| `Spinner` | Inline button/action loading |
| `PageLoader` | Auth loading, full-page transitions |
| `CardSkeleton` | Card section loading |
| `TableSkeleton` | Table data loading |

## State Management
Not applicable — pure presentational.

## Loading States
These components ARE the loading state system.

## Empty States
Not applicable.

## Edge Cases
- `lines=0` in `CardSkeleton`: renders just the header skeletons (valid).
- `rows=0` in `TableSkeleton`: renders just the header row.
- `PageLoader` `z-50`: ensure nothing has higher z-index that would obscure it.

## Test Cases
1. `Skeleton` renders with `animate-pulse` class.
2. `Spinner` renders with correct size class for each variant.
3. `PageLoader` renders with brand name and message.
4. `CardSkeleton` renders correct number of lines.
5. `TableSkeleton` renders correct rows × columns.
6. `Spinner` has `role="status"`.
7. `TableSkeleton` has `aria-busy="true"`.

## Acceptance Criteria
- [ ] All 5 loading components created
- [ ] Spinner has 4 size variants
- [ ] PageLoader shows brand name
- [ ] All components have appropriate aria attributes
- [ ] `Skeleton` used consistently (no inline `animate-pulse` divs)

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Consistent usage across all loading states in the app
