# 039 – Page Animations

## Objective
Implement a polished animation system using Framer Motion for page transitions, component entrance animations, staggered list reveals, and micro-interactions that make the FlowPilot AI dashboard feel fluid and professional.

## Scope
- `lib/animations.ts` — shared animation variants
- `components/ui/animated.tsx` — reusable animated wrapper components
- Page transition (already in 010 — extend here)
- Staggered container for lists and grids
- Fade-in, slide-in, and scale-in variants

## Out of Scope
- Complex gesture animations
- Canvas/SVG animations
- Video or GIF assets

## Functional Requirements
1. `FadeIn` component fades children in from opacity 0.
2. `SlideIn` component slides in from a direction (up/down/left/right).
3. `ScaleIn` component scales in from 95% to 100%.
4. `StaggerContainer` staggers children entrance animations.
5. All animations respect `prefers-reduced-motion` media query.
6. Animation durations: quick (150ms), normal (250ms), slow (400ms).

## Technical Requirements
- Framer Motion `motion`, `AnimatePresence`, `useReducedMotion`
- All variants exported from `lib/animations.ts`
- `useReducedMotion` hook disables animations for accessibility

## Folder Structure
```
frontend/
├── lib/
│   └── animations.ts
└── components/
    └── ui/
        └── animated.tsx
```

## Files To Create

### `lib/animations.ts`
```typescript
import type { Variants, Transition } from 'framer-motion';

// ─── Transition presets ───────────────────────────────────────────────────────
export const transitions = {
  quick: { duration: 0.15, ease: 'easeOut' } satisfies Transition,
  normal: { duration: 0.25, ease: 'easeOut' } satisfies Transition,
  slow: { duration: 0.4, ease: 'easeOut' } satisfies Transition,
  spring: { type: 'spring', damping: 28, stiffness: 300 } satisfies Transition,
  springBouncy: { type: 'spring', damping: 20, stiffness: 400 } satisfies Transition,
} as const;

// ─── Fade ─────────────────────────────────────────────────────────────────────
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transitions.normal },
  exit: { opacity: 0, transition: transitions.quick },
};

// ─── Slide ────────────────────────────────────────────────────────────────────
export const slideUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: transitions.normal },
  exit: { opacity: 0, y: -8, transition: transitions.quick },
};

export const slideDown: Variants = {
  hidden: { opacity: 0, y: -16 },
  visible: { opacity: 1, y: 0, transition: transitions.normal },
  exit: { opacity: 0, y: 8, transition: transitions.quick },
};

export const slideLeft: Variants = {
  hidden: { opacity: 0, x: 24 },
  visible: { opacity: 1, x: 0, transition: transitions.spring },
  exit: { opacity: 0, x: -16, transition: transitions.quick },
};

export const slideRight: Variants = {
  hidden: { opacity: 0, x: -24 },
  visible: { opacity: 1, x: 0, transition: transitions.spring },
  exit: { opacity: 0, x: 16, transition: transitions.quick },
};

// ─── Scale ────────────────────────────────────────────────────────────────────
export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1, transition: transitions.spring },
  exit: { opacity: 0, scale: 0.95, transition: transitions.quick },
};

// ─── Stagger container ────────────────────────────────────────────────────────
export const staggerContainer: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.07,
      delayChildren: 0.05,
    },
  },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: transitions.normal },
};

// ─── Page transition ──────────────────────────────────────────────────────────
export const pageTransition: Variants = {
  hidden: { opacity: 0, y: 8 },
  enter: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeInOut' } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15, ease: 'easeInOut' } },
};
```

### `components/ui/animated.tsx`
```tsx
'use client';

import React from 'react';
import { motion, useReducedMotion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import {
  fadeIn,
  slideUp,
  slideDown,
  slideLeft,
  slideRight,
  scaleIn,
  staggerContainer,
  staggerItem,
} from '@/lib/animations';

// ─── FadeIn ───────────────────────────────────────────────────────────────────
interface FadeInProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}

export function FadeIn({ children, className, delay = 0 }: FadeInProps) {
  const reduced = useReducedMotion();
  if (reduced) return <div className={className}>{children}</div>;

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      exit="exit"
      variants={fadeIn}
      transition={{ delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ─── SlideIn ──────────────────────────────────────────────────────────────────
type Direction = 'up' | 'down' | 'left' | 'right';
const SLIDE_VARIANTS = { up: slideUp, down: slideDown, left: slideLeft, right: slideRight };

interface SlideInProps {
  children: React.ReactNode;
  direction?: Direction;
  className?: string;
  delay?: number;
}

export function SlideIn({ children, direction = 'up', className, delay = 0 }: SlideInProps) {
  const reduced = useReducedMotion();
  if (reduced) return <div className={className}>{children}</div>;

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      exit="exit"
      variants={SLIDE_VARIANTS[direction]}
      transition={{ delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ─── ScaleIn ──────────────────────────────────────────────────────────────────
interface ScaleInProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}

export function ScaleIn({ children, className, delay = 0 }: ScaleInProps) {
  const reduced = useReducedMotion();
  if (reduced) return <div className={className}>{children}</div>;

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      exit="exit"
      variants={scaleIn}
      transition={{ delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ─── StaggerList ──────────────────────────────────────────────────────────────
interface StaggerListProps {
  children: React.ReactNode;
  className?: string;
  as?: React.ElementType;
}

export function StaggerList({ children, className, as: Tag = 'div' }: StaggerListProps) {
  const reduced = useReducedMotion();

  if (reduced) {
    return <Tag className={className}>{children}</Tag>;
  }

  const MotionTag = motion(Tag);

  return (
    <MotionTag
      initial="hidden"
      animate="visible"
      variants={staggerContainer}
      className={className}
    >
      {children}
    </MotionTag>
  );
}

// ─── StaggerItem ──────────────────────────────────────────────────────────────
interface StaggerItemProps {
  children: React.ReactNode;
  className?: string;
}

export function StaggerItem({ children, className }: StaggerItemProps) {
  const reduced = useReducedMotion();
  if (reduced) return <div className={className}>{children}</div>;

  return (
    <motion.div variants={staggerItem} className={className}>
      {children}
    </motion.div>
  );
}
```

## Existing Files To Modify
- `components/layout/PageTransition.tsx` (from 010) — import `pageTransition` from `lib/animations.ts`
- `components/workflow/WorkflowStep.tsx` — already uses Framer Motion; standardize to `staggerItem` variant
- `components/dashboard/MetricsRow.tsx` — wrap cards in `StaggerList` / `StaggerItem`

## API Contracts
Not applicable.

## Database Tables
Not applicable.

## Business Logic
- `useReducedMotion()` from Framer Motion detects `@media (prefers-reduced-motion: reduce)` — returns static fallback (plain div) when motion is reduced.
- Animation delay is additive with stagger delay — don't combine `StaggerItem` with explicit `delay` prop.
- All `exit` animations are shorter than `initial`/`animate` to feel snappy on removal.

## Validation Rules
Not applicable.

## Error Handling
- If Framer Motion fails to load (SSR edge case): `motion.div` falls back to regular div in non-JS environments.

## UI Behavior
- `FadeIn`: opacity 0 → 1 over 250ms.
- `SlideIn up`: opacity 0 + y=16 → opacity 1 + y=0 over 250ms.
- `ScaleIn`: opacity 0 + scale=0.95 → opacity 1 + scale=1 with spring.
- `StaggerList/Item`: children animate in 70ms apart.
- `prefers-reduced-motion`: all components render as plain divs (no animation).

## Component Breakdown
| Component | Animation |
|-----------|-----------|
| `FadeIn` | Fade opacity |
| `SlideIn` | Slide from direction |
| `ScaleIn` | Scale + fade |
| `StaggerList` | Container for stagger |
| `StaggerItem` | Individual staggered item |

## State Management
Not applicable.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- `delay` prop negative value: Framer Motion ignores negative delays.
- SSR: `motion.div` renders without animation on server; client hydration adds animation.
- Nested `StaggerList` components: inner list resets stagger timing.

## Test Cases
1. `FadeIn` renders children.
2. `SlideIn direction="left"` uses `slideLeft` variants.
3. `StaggerList` with 4 children renders all 4.
4. With `prefers-reduced-motion: reduce`, components render plain divs.
5. `pageTransition` variants have correct keys (`hidden`, `enter`, `exit`).
6. `useReducedMotion()` returns `true` in reduced-motion environments.

## Acceptance Criteria
- [ ] All 5 animation components created
- [ ] `prefers-reduced-motion` supported
- [ ] Animation variants in `lib/animations.ts`
- [ ] MetricsRow uses stagger animation
- [ ] PageTransition uses exported variants

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Reduced motion tested (browser dev tools)
