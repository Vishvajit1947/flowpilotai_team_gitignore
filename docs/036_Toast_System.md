# 036 – Toast System

## Objective
Implement a consistent, application-wide toast notification system using `sonner` that provides standardized helper functions for success, error, info, warning, and loading toasts, ensuring all notifications follow the same visual language and behavior.

## Scope
- `lib/toast.ts` — centralized toast helper functions
- Toast types: `success`, `error`, `warning`, `info`, `loading`, `promise`
- Consistent durations per type
- Usage guidelines and examples for all app features

## Out of Scope
- Toaster setup (already in `app/providers.tsx` from 002)
- Push notifications
- In-app notification center

## Functional Requirements
1. `toast.success(message)` — green, 4 second duration.
2. `toast.error(message)` — red, 6 seconds (longer for errors).
3. `toast.warning(message)` — yellow, 5 seconds.
4. `toast.info(message)` — blue, 4 seconds.
5. `toast.loading(message)` — spinner, manual dismiss.
6. `toast.promise(promise, messages)` — auto-transitions loading→success/error.
7. All toasts support optional `description` (subtitle).
8. `toast.dismiss(id)` to dismiss a specific toast.

## Technical Requirements
- `sonner` library (already installed)
- TypeScript type-safe wrapper
- Re-exports `sonner`'s native types

## Folder Structure
```
frontend/
└── lib/
    └── toast.ts
```

## Files To Create

### `lib/toast.ts`
```typescript
import { toast as sonnerToast, ExternalToast } from 'sonner';

type ToastOptions = Omit<ExternalToast, 'description'> & {
  description?: string;
};

// ─── Duration constants ───────────────────────────────────────────────────────
const DURATIONS = {
  success: 4000,
  error: 6000,
  warning: 5000,
  info: 4000,
} as const;

// ─── Toast helper functions ───────────────────────────────────────────────────

export const toast = {
  success(message: string, opts?: ToastOptions) {
    return sonnerToast.success(message, {
      duration: DURATIONS.success,
      ...opts,
    });
  },

  error(message: string, opts?: ToastOptions) {
    return sonnerToast.error(message, {
      duration: DURATIONS.error,
      ...opts,
    });
  },

  warning(message: string, opts?: ToastOptions) {
    return sonnerToast.warning(message, {
      duration: DURATIONS.warning,
      ...opts,
    });
  },

  info(message: string, opts?: ToastOptions) {
    return sonnerToast.info(message, {
      duration: DURATIONS.info,
      ...opts,
    });
  },

  loading(message: string, opts?: ToastOptions) {
    return sonnerToast.loading(message, {
      ...opts,
    });
  },

  /**
   * Promise toast: shows loading → success/error based on promise resolution.
   *
   * @example
   * toast.promise(api.post('/submit'), {
   *   loading: 'Submitting…',
   *   success: 'Submitted successfully!',
   *   error: 'Failed to submit',
   * });
   */
  promise<T>(
    promise: Promise<T>,
    messages: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((err: unknown) => string);
    },
    opts?: ToastOptions,
  ) {
    return sonnerToast.promise(promise, {
      loading: messages.loading,
      success: messages.success,
      error: messages.error,
      ...opts,
    });
  },

  /**
   * Dismiss a specific toast by ID, or all toasts if no ID given.
   */
  dismiss(toastId?: string | number) {
    return sonnerToast.dismiss(toastId);
  },
};

// ─── Common toast messages (shared constants) ─────────────────────────────────

export const TOAST_MESSAGES = {
  auth: {
    loginSuccess: 'Welcome back!',
    loginError: 'Invalid email or password',
    logoutSuccess: 'You have been signed out',
    registerSuccess: 'Account created successfully',
    sessionExpired: 'Your session has expired. Please sign in again.',
  },
  inbox: {
    submitSuccess: 'Submission received — AI is processing it',
    submitError: 'Failed to submit. Please try again.',
    processingComplete: 'Your submission has been processed',
    processingFailed: 'Processing failed — please check the result for details',
  },
  documents: {
    uploadSuccess: 'Document uploaded successfully',
    uploadError: 'Failed to upload document',
    extractSuccess: 'Invoice data extracted successfully',
    extractError: 'Extraction failed. Please try again.',
    extractTimeout: 'Processing timed out. Try a smaller file.',
  },
  admin: {
    resetSuccess: (count: number) => `Demo reset: ${count} submissions deleted`,
    resetError: 'Failed to reset demo data',
    seedSuccess: (count: number) => `Demo seeded: ${count} submissions added`,
    seedError: 'Failed to seed demo data',
  },
  generic: {
    networkError: 'Network error. Please check your connection.',
    serverError: 'Something went wrong. Please try again.',
    saved: 'Changes saved',
    copied: 'Copied to clipboard',
  },
} as const;
```

## Existing Files To Modify
- Any component currently importing `toast` from `sonner` directly should be updated to import from `@/lib/toast` for consistency.

  Key files to update:
  - `components/inbox/InboxForm.tsx` → `import { toast } from '@/lib/toast'`
  - `hooks/useAdminActions.ts` → `import { toast } from '@/lib/toast'`

## API Contracts
Not applicable — frontend utility only.

## Request Examples
```typescript
import { toast, TOAST_MESSAGES } from '@/lib/toast';

// Simple success
toast.success('Document saved');

// With description
toast.error('Upload failed', { description: 'File exceeds 10MB limit' });

// Promise toast
toast.promise(api.post('/submit', data), {
  loading: 'Submitting…',
  success: 'Your request is being processed',
  error: (err) => err?.response?.data?.detail ?? 'Submission failed',
});

// Loading with manual dismiss
const id = toast.loading('Processing document…');
// later:
toast.dismiss(id);
toast.success('Document processed');

// Using message constants
toast.success(TOAST_MESSAGES.inbox.submitSuccess);
```

## Response Examples
Not applicable.

## Database Tables
Not applicable.

## Business Logic
- Error toasts have longer duration (6s vs 4s) since users need time to read error messages.
- Loading toasts have no auto-dismiss — must be manually dismissed via `toast.dismiss(id)`.
- `TOAST_MESSAGES` centralized constants prevent message drift across the app.

## Validation Rules
Not applicable.

## Error Handling
Not applicable (toast system IS the error feedback mechanism).

## UI Behavior
- All toasts appear bottom-right (configured in providers.tsx).
- Multiple toasts stack vertically.
- User can dismiss any toast manually by clicking it.
- Error toasts stay visible for 6 seconds.
- Toast types use distinct icons (sonner provides these automatically).

## Component Breakdown
Not applicable — utility module.

## State Management
Not applicable.

## Loading States
- `toast.loading()` shows an animated spinner icon.
- `toast.promise()` auto-manages loading → resolved state.

## Empty States
Not applicable.

## Edge Cases
- Calling `toast.dismiss()` with no ID dismisses all active toasts.
- `toast.promise()` where promise resolves very quickly: still shows loading briefly.
- Multiple error toasts: all stack; user should be reasonable about not spamming toasts.

## Test Cases
1. `toast.success()` calls `sonnerToast.success` with `duration: 4000`.
2. `toast.error()` calls `sonnerToast.error` with `duration: 6000`.
3. `toast.promise()` wraps `sonnerToast.promise` correctly.
4. `TOAST_MESSAGES.admin.resetSuccess(5)` returns correct string.
5. `toast.dismiss()` calls `sonnerToast.dismiss()`.

## Acceptance Criteria
- [ ] All toast types work (`success`, `error`, `warning`, `info`, `loading`, `promise`)
- [ ] Durations correct per type
- [ ] `TOAST_MESSAGES` constants available for all feature areas
- [ ] Components using sonner directly updated to use `@/lib/toast`

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- `TOAST_MESSAGES` covers auth, inbox, documents, admin, generic domains
