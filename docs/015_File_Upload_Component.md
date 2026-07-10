# 015 – File Upload Component

## Objective
Build a reusable drag-and-drop file upload component that uploads files to Supabase Storage, returns a public URL, and integrates with the AI Inbox form. Supports PDF and image files (PNG, JPG, JPEG) up to 10MB with progress feedback.

## Scope
- `components/ui/FileUpload.tsx` — drag-and-drop upload component
- `lib/storage.ts` — Supabase Storage upload helper
- Integration with `InboxForm` (014) to attach file URL to submission
- Accepted file types: `application/pdf`, `image/png`, `image/jpeg`
- Max file size: 10MB
- Upload progress percentage display
- File removal before submission

## Out of Scope
- OCR processing (027)
- Multiple file uploads (v1 is single file)
- Server-side file validation (handled at OCR service level)

## Functional Requirements
1. Drag-and-drop zone accepts PDF and image files.
2. Click to open file picker as alternative to drag-and-drop.
3. Show file type icon, name, and size after selection.
4. Show upload progress bar (0–100%) during upload.
5. Show success state with file name after upload completes.
6. Show error state if upload fails (network or size error).
7. Allow removing the selected file (resets component state).
8. Reject files larger than 10MB with inline error message.
9. Reject unsupported file types with inline error message.
10. Call `onUploadComplete(url: string)` callback on success.

## Technical Requirements
- `@supabase/supabase-js` client for storage upload
- HTML5 File API + `DataTransfer` for drag-and-drop
- `useRef` for hidden file input
- Upload progress via Supabase's `onUploadProgress` option
- UUID v4 for unique file paths (prevent collisions)

## Folder Structure
```
frontend/
├── components/
│   └── ui/
│       └── FileUpload.tsx
└── lib/
    └── storage.ts
```

## Files To Create

### `lib/storage.ts`
```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

const BUCKET_NAME = 'flowpilot-uploads';
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = ['application/pdf', 'image/png', 'image/jpeg'];

export interface UploadResult {
  url: string;
  path: string;
}

export class StorageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'StorageError';
  }
}

export function validateFile(file: File): string | null {
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `File size exceeds 10MB limit (${(file.size / 1024 / 1024).toFixed(1)}MB)`;
  }
  if (!ALLOWED_TYPES.includes(file.type)) {
    return `Unsupported file type: ${file.type}. Allowed: PDF, PNG, JPG`;
  }
  return null;
}

export async function uploadFile(
  file: File,
  userId: string,
  onProgress?: (percent: number) => void,
): Promise<UploadResult> {
  const ext = file.name.split('.').pop() ?? 'bin';
  const uniqueId = crypto.randomUUID();
  const path = `${userId}/${uniqueId}.${ext}`;

  // Simulate progress for small files (Supabase JS doesn't expose XHR progress natively)
  // For a real progress bar, use XMLHttpRequest directly
  let progressInterval: ReturnType<typeof setInterval> | null = null;
  let simulatedProgress = 0;
  if (onProgress) {
    progressInterval = setInterval(() => {
      simulatedProgress = Math.min(simulatedProgress + 10, 90);
      onProgress(simulatedProgress);
    }, 200);
  }

  try {
    const { data, error } = await supabase.storage
      .from(BUCKET_NAME)
      .upload(path, file, {
        cacheControl: '3600',
        upsert: false,
        contentType: file.type,
      });

    if (error) throw new StorageError(error.message);

    if (onProgress) onProgress(100);

    const { data: urlData } = supabase.storage
      .from(BUCKET_NAME)
      .getPublicUrl(data.path);

    return { url: urlData.publicUrl, path: data.path };
  } finally {
    if (progressInterval) clearInterval(progressInterval);
  }
}

export async function deleteFile(path: string): Promise<void> {
  const { error } = await supabase.storage
    .from(BUCKET_NAME)
    .remove([path]);
  if (error) throw new StorageError(error.message);
}
```

### `components/ui/FileUpload.tsx`
```tsx
'use client';

import { useState, useRef, useCallback } from 'react';
import {
  Upload,
  File,
  FileImage,
  X,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { Button } from './button';
import { Progress } from './progress';
import { cn } from '@/lib/utils';
import { uploadFile, validateFile, deleteFile } from '@/lib/storage';
import { useAuth } from '@/hooks/useAuth';

interface FileUploadProps {
  onUploadComplete: (url: string) => void;
  onRemove?: () => void;
  disabled?: boolean;
}

type UploadState =
  | { status: 'idle' }
  | { status: 'selected'; file: File }
  | { status: 'uploading'; file: File; progress: number }
  | { status: 'done'; file: File; url: string; path: string }
  | { status: 'error'; message: string };

function getFileIcon(type: string) {
  if (type.startsWith('image/')) return FileImage;
  return File;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function FileUpload({ onUploadComplete, onRemove, disabled }: FileUploadProps) {
  const [state, setState] = useState<UploadState>({ status: 'idle' });
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { user } = useAuth();

  const processFile = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setState({ status: 'error', message: validationError });
        return;
      }

      setState({ status: 'uploading', file, progress: 0 });
      try {
        const result = await uploadFile(file, user!.id, (p) =>
          setState((prev) =>
            prev.status === 'uploading' ? { ...prev, progress: p } : prev,
          ),
        );
        setState({ status: 'done', file, url: result.url, path: result.path });
        onUploadComplete(result.url);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Upload failed';
        setState({ status: 'error', message });
      }
    },
    [user, onUploadComplete],
  );

  const handleRemove = useCallback(async () => {
    if (state.status === 'done') {
      try {
        await deleteFile(state.path);
      } catch {
        // Best-effort delete
      }
    }
    setState({ status: 'idle' });
    if (inputRef.current) inputRef.current.value = '';
    onRemove?.();
  }, [state, onRemove]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  // ── Idle / Drag Zone ────────────────────────────────────────────────────────
  if (state.status === 'idle' || state.status === 'error') {
    return (
      <div className="space-y-2">
        <div
          role="button"
          tabIndex={disabled ? -1 : 0}
          aria-label="Upload file — drag and drop or click to browse"
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => !disabled && inputRef.current?.click()}
          onKeyDown={(e) => e.key === 'Enter' && !disabled && inputRef.current?.click()}
          className={cn(
            'flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed p-8 text-center transition-colors',
            isDragOver
              ? 'border-primary bg-primary/5'
              : 'border-muted-foreground/25 hover:border-primary/50',
            disabled && 'cursor-not-allowed opacity-50',
          )}
        >
          <Upload className="h-8 w-8 text-muted-foreground" />
          <div>
            <p className="text-sm font-medium">Drop file here or click to browse</p>
            <p className="text-xs text-muted-foreground">PDF, PNG, JPG up to 10MB</p>
          </div>
        </div>
        {state.status === 'error' && (
          <div className="flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {state.message}
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          className="sr-only"
          onChange={handleFileChange}
          disabled={disabled}
          aria-hidden="true"
        />
      </div>
    );
  }

  const FileIcon = 'file' in state ? getFileIcon(state.file.type) : File;

  // ── Uploading ────────────────────────────────────────────────────────────────
  if (state.status === 'uploading') {
    return (
      <div className="space-y-2 rounded-lg border p-4">
        <div className="flex items-center gap-3">
          <FileIcon className="h-8 w-8 flex-shrink-0 text-muted-foreground" />
          <div className="flex-1 min-w-0">
            <p className="truncate text-sm font-medium">{state.file.name}</p>
            <p className="text-xs text-muted-foreground">{formatBytes(state.file.size)}</p>
          </div>
        </div>
        <Progress value={state.progress} className="h-1.5" />
        <p className="text-xs text-muted-foreground">Uploading… {state.progress}%</p>
      </div>
    );
  }

  // ── Done ─────────────────────────────────────────────────────────────────────
  if (state.status === 'done') {
    return (
      <div className="flex items-center gap-3 rounded-lg border bg-green-50 dark:bg-green-900/10 p-4">
        <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-green-500" />
        <div className="flex-1 min-w-0">
          <p className="truncate text-sm font-medium">{state.file.name}</p>
          <p className="text-xs text-muted-foreground">{formatBytes(state.file.size)} · Uploaded</p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="flex-shrink-0 h-7 w-7"
          onClick={handleRemove}
          aria-label="Remove file"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return null;
}
```

## Existing Files To Modify
- `frontend/.env.local.example` — add Supabase public keys:
  ```
  NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
  NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
  ```
- `frontend/package.json` — add `@supabase/supabase-js`
- `components/inbox/InboxForm.tsx` (from 014) — enable the file attachment button and integrate `FileUpload`

## API Contracts
Direct Supabase Storage API — not a backend endpoint.

### Supabase Storage Upload
```
POST https://{project}.supabase.co/storage/v1/object/{bucket}/{path}
Authorization: Bearer {anon_key}
Content-Type: {file.type}
Body: binary file data
```

## Request Examples
```typescript
// Usage in InboxForm
<FileUpload
  onUploadComplete={(url) => setFileUrl(url)}
  onRemove={() => setFileUrl(undefined)}
  disabled={isSubmitting}
/>
```

## Response Examples
Supabase `getPublicUrl` returns:
```json
{
  "data": {
    "publicUrl": "https://abc.supabase.co/storage/v1/object/public/flowpilot-uploads/user-id/uuid.pdf"
  }
}
```

## Database Tables
Not applicable — files stored in Supabase Storage, not the PostgreSQL database.

## Business Logic
- File path structure: `{userId}/{uuid}.{ext}` — user-scoped to prevent cross-user file access.
- Upload is client-to-Supabase Storage directly (not proxied through FastAPI) to avoid backend memory pressure.
- Public URLs are returned because they're needed by the OCR service running server-side.
- On component removal, the file is deleted from storage (best-effort — no retry).

## Validation Rules
| Rule | Error Message |
|------|---------------|
| Size > 10MB | "File size exceeds 10MB limit (X.XMB)" |
| Unsupported MIME type | "Unsupported file type: X. Allowed: PDF, PNG, JPG" |

## Error Handling
| Scenario | UI |
|----------|-----|
| Oversized file | Inline error below drop zone |
| Wrong file type | Inline error below drop zone |
| Upload network error | Inline error: Supabase error message |
| Delete fails | Silent (best-effort) |

## UI Behavior
- Idle: dashed border drop zone
- Drag over: solid primary border + light blue background
- Uploading: file details + progress bar
- Done: green background + file name + remove button
- Error: red inline message below drop zone (reverts to idle visually)
- Component goes back to idle after remove

## Component Breakdown
| State | Visual |
|-------|--------|
| idle | Drop zone |
| error | Drop zone + error message |
| uploading | File card + progress bar |
| done | File card + green tick + remove button |

## State Management
Local `useState` with union type — no global store.

## Loading States
- `uploading` state: Progress bar + percentage text
- Progress is simulated (10% increments every 200ms) capped at 90%; jumps to 100% on completion

## Empty States
- No attached file: shows drop zone (idle state)

## Edge Cases
- User drops multiple files: only first file processed (`e.dataTransfer.files[0]`).
- File with no extension: path uses `'bin'` fallback extension.
- `user` is null: prevented by ProtectedRoute; `user!.id` is safe here.
- Upload during form submit: `disabled` prop prevents new uploads.
- Large PDF: progress bar visible for multiple seconds.

## Test Cases
1. Dropping a valid PDF triggers upload.
2. Dropping a file > 10MB shows size error.
3. Dropping a `.txt` file shows type error.
4. Upload progress updates from 0 to 100.
5. `onUploadComplete` called with public URL on success.
6. Remove button calls `deleteFile` and resets state.
7. File input click opens OS file picker.
8. `aria-label` present on drop zone for screen readers.

## Acceptance Criteria
- [ ] Drag-and-drop accepts PDF, PNG, JPG files
- [ ] Files > 10MB rejected with error
- [ ] Unsupported types rejected with error
- [ ] Upload progress displayed
- [ ] Success state shows file name + remove button
- [ ] `onUploadComplete(url)` called with Supabase public URL
- [ ] File deleted from storage on remove

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Supabase bucket `flowpilot-uploads` must exist with public access enabled
- Environment variables documented
