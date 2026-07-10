# 002 – Frontend Scaffold

## Objective
Build the complete Next.js 15 App Router scaffolding including global layout, CSS variables, Shadcn UI theme initialization, font loading, and the root application shell so every subsequent frontend task has a consistent base to extend.

## Scope
- App Router root layout (`app/layout.tsx`)
- Global CSS with Tailwind directives and CSS variable theme
- Shadcn UI component library initialization (`components/ui/`)
- Inter font via `next/font/google`
- TypeScript path aliases (`@/`)
- Global providers wrapper (theme, toast)
- `app/page.tsx` redirect to `/dashboard`
- `app/not-found.tsx` 404 page
- `lib/utils.ts` shared utility (`cn`)
- `types/index.ts` global TypeScript types

## Out of Scope
- Authentication flow (005, 006, 007)
- Dashboard layout (010)
- Any page-specific components

## Functional Requirements
1. Navigating to `/` redirects immediately to `/dashboard`.
2. The global font (Inter) loads with no layout shift (font-display: swap, preload).
3. The CSS theme provides both light and dark mode variables.
4. `cn()` utility correctly merges Tailwind classes.
5. A `<Providers>` component wraps the entire app and can be extended.
6. `app/not-found.tsx` renders a user-friendly 404 with a "Go Home" link.

## Technical Requirements
- Next.js 15 App Router
- `next/font/google` for Inter
- Tailwind CSS with `tailwind-merge` + `clsx`
- Shadcn UI (manually configured — no CLI dependency)
- CSS custom properties for theming (no JS-in-CSS)
- `tailwindcss-animate` plugin for Shadcn transitions

## Folder Structure
```
frontend/
├── app/
│   ├── layout.tsx            # Root layout
│   ├── page.tsx              # Root redirect → /dashboard
│   ├── not-found.tsx         # 404 page
│   ├── globals.css           # Global styles + CSS variables
│   └── providers.tsx         # App-wide React providers
├── components/
│   └── ui/                   # Shadcn primitive components
│       ├── button.tsx
│       ├── card.tsx
│       ├── input.tsx
│       ├── label.tsx
│       ├── badge.tsx
│       ├── separator.tsx
│       ├── avatar.tsx
│       ├── dialog.tsx
│       ├── dropdown-menu.tsx
│       ├── tooltip.tsx
│       ├── tabs.tsx
│       ├── progress.tsx
│       └── switch.tsx
├── lib/
│   └── utils.ts              # cn() helper
├── types/
│   └── index.ts              # Shared TypeScript types
└── styles/
    └── fonts.css             # Font face declarations (if needed)
```

## Files To Create

### `app/globals.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 224.3 76.3% 48%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground font-sans antialiased;
  }
}
```

### `app/layout.tsx`
```tsx
import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: {
    default: 'FlowPilot AI',
    template: '%s | FlowPilot AI',
  },
  description: 'AI-powered inbox orchestration and workflow automation',
  robots: 'noindex, nofollow', // SaaS app — no public indexing
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

### `app/providers.tsx`
```tsx
'use client';

import { Toaster } from 'sonner';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Toaster
        position="bottom-right"
        toastOptions={{
          classNames: {
            toast: 'font-sans',
          },
        }}
      />
    </>
  );
}
```

### `app/page.tsx`
```tsx
import { redirect } from 'next/navigation';

export default function RootPage() {
  redirect('/dashboard');
}
```

### `app/not-found.tsx`
```tsx
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-4">
      <div className="text-center">
        <h1 className="text-8xl font-bold text-muted-foreground">404</h1>
        <h2 className="mt-4 text-2xl font-semibold">Page not found</h2>
        <p className="mt-2 text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
      </div>
      <Button asChild>
        <Link href="/dashboard">Go to Dashboard</Link>
      </Button>
    </div>
  );
}
```

### `lib/utils.ts`
```typescript
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(date));
}

export function formatDateTime(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}

export function formatCurrency(amount: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount);
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '…';
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
```

### `types/index.ts`
```typescript
// ─── User / Auth ─────────────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'user';
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: 'bearer';
}

// ─── Inbox / Workflow ─────────────────────────────────────────────────────────
export type AgentType = 'sales' | 'support' | 'finance' | 'executive';

export type WorkflowStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed';

export interface InboxSubmission {
  id: string;
  user_id: string;
  content: string;
  file_url?: string | null;
  detected_intent: string | null;
  confidence_score: number | null;
  assigned_agent: AgentType | null;
  status: WorkflowStatus;
  result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// ─── Analytics ────────────────────────────────────────────────────────────────
export interface AnalyticsSummary {
  total_submissions: number;
  completed: number;
  failed: number;
  avg_confidence: number;
  by_agent: Record<AgentType, number>;
  by_day: DayBucket[];
}

export interface DayBucket {
  date: string;
  count: number;
}

// ─── API ──────────────────────────────────────────────────────────────────────
export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
```

### `components/ui/button.tsx`
```tsx
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground shadow hover:bg-primary/90',
        destructive:
          'bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90',
        outline:
          'border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground',
        secondary:
          'bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-md px-3 text-xs',
        lg: 'h-10 rounded-md px-8',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

### `components/ui/card.tsx`
```tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'rounded-xl border bg-card text-card-foreground shadow',
      className,
    )}
    {...props}
  />
));
Card.displayName = 'Card';

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col space-y-1.5 p-6', className)}
    {...props}
  />
));
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn('font-semibold leading-none tracking-tight', className)}
    {...props}
  />
));
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm text-muted-foreground', className)}
    {...props}
  />
));
CardDescription.displayName = 'CardDescription';

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
));
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center p-6 pt-0', className)}
    {...props}
  />
));
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
```

### `components/ui/input.tsx`
```tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = 'Input';

export { Input };
```

## Existing Files To Modify
- `frontend/package.json` — ensure `tailwindcss-animate` is in dependencies

## API Contracts
None — this task is frontend scaffolding only.

## Request Examples
Not applicable.

## Response Examples
Not applicable.

## Database Tables
Not applicable.

## Business Logic
- Root `/` page uses Next.js `redirect()` (server-side) to avoid flash of content.
- `suppressHydrationWarning` on `<html>` is required for dark mode toggling to prevent hydration mismatch.

## Validation Rules
- All Shadcn components must be typed with `React.forwardRef`.
- `cn()` must always be used for class merging — never string concatenation.

## Error Handling
- If `Inter` font fails to load, browser falls back to `system-ui, sans-serif`.
- 404 page must render without any auth context (it can show before auth loads).

## UI Behavior
- Root page: immediate server redirect, no visible UI rendered.
- 404 page: centered layout, large "404" text, brief message, "Go to Dashboard" button.
- All transitions use `transition-colors` Tailwind utility for hover states.

## Component Breakdown
| Component | Purpose |
|-----------|---------|
| `RootLayout` | Wraps entire app with font, providers, metadata |
| `Providers` | Client-side providers: Toaster |
| `RootPage` | Server component that redirects to /dashboard |
| `NotFound` | 404 error page |
| `Button` | Shadcn button with variant/size support |
| `Card` | Shadcn card with header/content/footer |
| `Input` | Shadcn text input |

## State Management
None at scaffold level — providers extended in later tasks.

## Loading States
Not applicable at this level.

## Empty States
Not applicable at this level.

## Edge Cases
- `suppressHydrationWarning` must be on `<html>` tag, not `<body>`, to avoid React warning when dark mode class is injected.
- `redirect()` in Next.js 15 throws internally — do NOT wrap it in try/catch.
- CSS variable names must exactly match Tailwind config keys.

## Test Cases
1. GET `/` returns 307/308 redirect to `/dashboard`.
2. GET `/nonexistent-page` renders 404 page with "Page not found" text.
3. `cn('px-4', 'px-2')` returns `'px-2'` (tailwind-merge deduplication).
4. `formatCurrency(1234.56)` returns `'$1,234.56'`.
5. `truncate('Hello World', 5)` returns `'Hello…'`.
6. Inter font is included in `<head>` with `rel="preload"`.

## Acceptance Criteria
- [ ] Root `/` redirects to `/dashboard` without rendering any UI
- [ ] 404 page renders correctly with navigation link
- [ ] Inter font loads via `next/font/google` with no CLS
- [ ] CSS variables resolve correctly in both light and dark mode
- [ ] All Shadcn `ui/` components export correctly with TypeScript types
- [ ] `cn()` utility correctly merges and deduplicates Tailwind classes
- [ ] `npm run type-check` passes with zero errors

## Definition of Done
- All acceptance criteria checked
- All Shadcn UI primitive components present in `components/ui/`
- `npm run build` completes without errors
- No TypeScript or ESLint errors
