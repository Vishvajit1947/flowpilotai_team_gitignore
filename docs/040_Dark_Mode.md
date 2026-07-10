# 040 – Dark Mode

## Objective
Implement full dark mode support using the `class` strategy (Tailwind's `darkMode: ['class']`), a theme toggle component, system preference detection, and persistence in the Zustand UI store — ensuring all existing components automatically support both themes.

## Scope
- `components/ui/ThemeToggle.tsx` — sun/moon toggle button
- `components/ThemeProvider.tsx` — client-side theme applicator
- Theme persistence in `useUIStore` (already has `theme` field from 010)
- System preference detection via `matchMedia`
- Integration into `Header` component (012)

## Out of Scope
- Per-page themes
- High-contrast mode

## Functional Requirements
1. Theme options: `light`, `dark`, `system`.
2. `system` follows OS preference (`prefers-color-scheme`).
3. On page load, apply saved theme before first paint (no flash).
4. Toggle cycles: `light → dark → system → light`.
5. Theme persisted in `useUIStore` (Zustand + localStorage).
6. Applies `dark` class to `<html>` element.

## Technical Requirements
- Tailwind `darkMode: ['class']` (already configured in 001)
- `next-themes` package OR custom implementation using Zustand + `document.documentElement`
- `useEffect` for client-side application
- `suppressHydrationWarning` on `<html>` (already in 002)

## Folder Structure
```
frontend/
└── components/
    ├── ThemeProvider.tsx
    └── ui/
        └── ThemeToggle.tsx
```

## Files To Create

### `components/ThemeProvider.tsx`
```tsx
'use client';

import { useEffect } from 'react';
import { useUIStore } from '@/store/ui';

/**
 * Applies the theme class to the <html> element based on Zustand store value.
 * Also listens for system theme changes when theme = 'system'.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useUIStore((s) => s.theme);

  useEffect(() => {
    const root = document.documentElement;

    function applyTheme(t: 'light' | 'dark' | 'system') {
      const isDark =
        t === 'dark' ||
        (t === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
      root.classList.toggle('dark', isDark);
    }

    applyTheme(theme);

    // Listen for system preference changes when in 'system' mode
    if (theme === 'system') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      const handler = () => applyTheme('system');
      mq.addEventListener('change', handler);
      return () => mq.removeEventListener('change', handler);
    }
  }, [theme]);

  return <>{children}</>;
}
```

### `components/ui/ThemeToggle.tsx`
```tsx
'use client';

import { Sun, Moon, Monitor } from 'lucide-react';
import { useUIStore } from '@/store/ui';
import { Button } from './button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './dropdown-menu';

const THEME_ICONS = {
  light: Sun,
  dark: Moon,
  system: Monitor,
};

const THEME_LABELS = {
  light: 'Light',
  dark: 'Dark',
  system: 'System',
};

export function ThemeToggle() {
  const theme = useUIStore((s) => s.theme);
  const setTheme = useUIStore((s) => s.setTheme);

  const Icon = THEME_ICONS[theme];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Current theme: ${THEME_LABELS[theme]}`}>
          <Icon className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {(['light', 'dark', 'system'] as const).map((t) => {
          const ThemeIcon = THEME_ICONS[t];
          return (
            <DropdownMenuItem
              key={t}
              onClick={() => setTheme(t)}
              className="gap-2"
            >
              <ThemeIcon className="h-4 w-4" />
              <span>{THEME_LABELS[t]}</span>
              {theme === t && (
                <span className="ml-auto text-xs text-muted-foreground">✓</span>
              )}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

### Add inline script to prevent flash (add to `app/layout.tsx`)
```tsx
// Add this <script> tag inside <head> before any other content
// to apply dark class before first paint:
<script
  dangerouslySetInnerHTML={{
    __html: `
      (function() {
        try {
          var stored = localStorage.getItem('flowpilot-ui');
          var theme = stored ? JSON.parse(stored).state?.theme : 'system';
          var isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
          if (isDark) document.documentElement.classList.add('dark');
        } catch(e) {}
      })();
    `,
  }}
/>
```

## Existing Files To Modify

### `app/layout.tsx` — add ThemeProvider + anti-flash script
```tsx
import { ThemeProvider } from '@/components/ThemeProvider';

// In RootLayout, wrap Providers with ThemeProvider:
export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Anti-flash inline script */}
        <script dangerouslySetInnerHTML={{ __html: ANTI_FLASH_SCRIPT }} />
      </head>
      <body className={inter.variable}>
        <Providers>
          <ThemeProvider>
            {children}
          </ThemeProvider>
        </Providers>
      </body>
    </html>
  );
}
```

### `components/layout/Header.tsx` — add ThemeToggle
```tsx
import { ThemeToggle } from '@/components/ui/ThemeToggle';

// In actions section, add ThemeToggle before notification bell:
<ThemeToggle />
<TooltipProvider>...Bell...</TooltipProvider>
<DropdownMenu>...User menu...</DropdownMenu>
```

### `app/providers.tsx` — remove Toaster duplication if needed

## API Contracts
Not applicable.

## Database Tables
Not applicable.

## Business Logic
1. Theme stored in `useUIStore.theme` (persisted to localStorage key `flowpilot-ui`).
2. Anti-flash script reads from the same localStorage key before React hydration.
3. `system` mode: listens for OS theme changes via `matchMedia` event listener.
4. Cleanup: event listener removed when theme changes away from `system`.

## Validation Rules
- `theme` must be `'light'`, `'dark'`, or `'system'`.

## Error Handling
- Anti-flash script is in a try/catch — silently fails in restricted environments.
- `matchMedia` not available in SSR: `useEffect` ensures client-only execution.

## UI Behavior
- Header shows sun icon (light), moon icon (dark), or monitor icon (system).
- Clicking opens 3-option dropdown with checkmark on current selection.
- Theme change is instant — no transition needed (Tailwind handles color transitions).
- Dark mode: dark CSS variable values from `globals.css` (set in 002).

## Component Breakdown
| Component | Responsibility |
|-----------|---------------|
| `ThemeProvider` | Applies dark class to `<html>` |
| `ThemeToggle` | UI dropdown for theme selection |
| Anti-flash script | Prevents flash before React loads |

## State Management
Reads/writes `useUIStore.theme`. Persisted via Zustand persist middleware.

## Loading States
Not applicable.

## Empty States
Not applicable.

## Edge Cases
- First visit (no localStorage): `system` is default → follows OS preference.
- localStorage disabled: anti-flash script silently fails; theme defaults to light.
- User changes OS dark mode preference: only applies if current theme is `system`.
- SSR: `document` not available → all theme application in `useEffect`.

## Test Cases
1. Default theme is `system`.
2. Selecting `dark` adds `dark` class to `document.documentElement`.
3. Selecting `light` removes `dark` class.
4. Selecting `system` follows OS preference.
5. OS preference change triggers re-apply when theme is `system`.
6. Theme persists across page reloads (localStorage).
7. Anti-flash script adds `dark` class before React hydration.
8. Dropdown shows checkmark on active theme.

## Acceptance Criteria
- [ ] `dark` and `light` modes fully styled
- [ ] `system` mode follows OS preference
- [ ] Theme persists across page reloads
- [ ] No flash of wrong theme on load (anti-flash script)
- [ ] ThemeToggle in Header with dropdown
- [ ] All CSS variables defined for both themes (already in 002)

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Anti-flash script tested: no visible flash in Chrome DevTools slow network
