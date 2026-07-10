# 029 – Document Intelligence Page

## Objective
Build the Document Intelligence page where users can upload invoices and documents, trigger AI-powered extraction via the `/documents/extract-invoice` endpoint, and view structured results in a formatted data card with line items table and payment recommendation.

## Scope
- `app/(dashboard)/dashboard/documents/page.tsx` — Document Intelligence page
- `components/documents/InvoiceExtractor.tsx` — upload form + extraction trigger
- `components/documents/InvoiceResultCard.tsx` — structured result display
- `hooks/useInvoiceExtraction.ts` — extraction API hook

## Out of Scope
- File upload component (015 — reused here)
- Backend extraction endpoint (028)
- Inbox submission creation

## Functional Requirements
1. File upload zone (reuses `FileUpload` from 015) for PDF/image upload.
2. "Extract Data" button triggers extraction API call.
3. Show loading state during extraction (up to 45 seconds).
4. Display extracted invoice data in organized sections.
5. Show line items in a responsive table.
6. Color-coded payment recommendation badge (green/yellow/red).
7. Show confidence score as progress bar.
8. Allow user to upload a new document (resets state).

## Technical Requirements
- Next.js 15 App Router (`'use client'`)
- Reuses `FileUpload` component from 015
- Axios via `api` client
- Local state for extraction result

## Folder Structure
```
frontend/
├── app/
│   └── (dashboard)/
│       └── dashboard/
│           └── documents/
│               └── page.tsx
├── components/
│   └── documents/
│       ├── InvoiceExtractor.tsx
│       └── InvoiceResultCard.tsx
└── hooks/
    └── useInvoiceExtraction.ts
```

## Files To Create

### `hooks/useInvoiceExtraction.ts`
```typescript
'use client';

import { useState, useCallback } from 'react';
import api from '@/lib/api';

interface LineItem {
  description?: string;
  quantity?: number;
  unit_price?: number;
  total?: number;
}

export interface InvoiceResult {
  document_type: string;
  vendor_name?: string;
  vendor_contact?: string;
  invoice_number?: string;
  invoice_date?: string;
  due_date?: string;
  payment_terms?: string;
  currency: string;
  subtotal?: number;
  tax_amount?: number;
  total_amount?: number;
  line_items: LineItem[];
  payment_recommendation: 'approve' | 'hold' | 'review';
  anomalies: string[];
  action_items: string[];
  summary: string;
  confidence: number;
  raw_text_length: number;
}

interface UseInvoiceExtractionResult {
  extract: (fileUrl: string) => Promise<void>;
  result: InvoiceResult | null;
  isLoading: boolean;
  error: string | null;
  reset: () => void;
}

export function useInvoiceExtraction(): UseInvoiceExtractionResult {
  const [result, setResult] = useState<InvoiceResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const extract = useCallback(async (fileUrl: string) => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.post<InvoiceResult>('/documents/extract-invoice', {
        file_url: fileUrl,
      });
      setResult(res.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Extraction failed. Please try again.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return { extract, result, isLoading, error, reset };
}
```

### `components/documents/InvoiceExtractor.tsx`
```tsx
'use client';

import { useState } from 'react';
import { FileText, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { FileUpload } from '@/components/ui/FileUpload';
import { useInvoiceExtraction } from '@/hooks/useInvoiceExtraction';
import { InvoiceResultCard } from './InvoiceResultCard';

export function InvoiceExtractor() {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const { extract, result, isLoading, error, reset } = useInvoiceExtraction();

  const handleExtract = async () => {
    if (!fileUrl) return;
    await extract(fileUrl);
  };

  const handleReset = () => {
    setFileUrl(null);
    reset();
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Upload Document
          </CardTitle>
          <CardDescription>
            Upload a PDF or image of an invoice, receipt, or purchase order
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FileUpload
            onUploadComplete={(url) => setFileUrl(url)}
            onRemove={() => { setFileUrl(null); reset(); }}
            disabled={isLoading}
          />

          <div className="flex justify-end gap-3">
            {(fileUrl || result) && (
              <Button variant="outline" onClick={handleReset} disabled={isLoading}>
                Upload new document
              </Button>
            )}
            <Button
              onClick={handleExtract}
              disabled={!fileUrl || isLoading}
              className="gap-2"
            >
              {isLoading ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Extracting… (up to 45s)
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Extract Data
                </>
              )}
            </Button>
          </div>

          {error && (
            <div className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {result && <InvoiceResultCard result={result} />}
    </div>
  );
}
```

### `components/documents/InvoiceResultCard.tsx`
```tsx
'use client';

import { CheckCircle2, AlertTriangle, Clock, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/utils';
import type { InvoiceResult } from '@/hooks/useInvoiceExtraction';

const RECOMMENDATION_CONFIG = {
  approve: {
    label: 'Approve',
    icon: CheckCircle2,
    className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  },
  review: {
    label: 'Needs Review',
    icon: AlertTriangle,
    className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  },
  hold: {
    label: 'On Hold',
    icon: Clock,
    className: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  },
};

interface InvoiceResultCardProps {
  result: InvoiceResult;
}

export function InvoiceResultCard({ result }: InvoiceResultCardProps) {
  const rec = RECOMMENDATION_CONFIG[result.payment_recommendation] ?? RECOMMENDATION_CONFIG.review;
  const RecIcon = rec.icon;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Extraction Results</CardTitle>
          <span
            className={cn(
              'flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium',
              rec.className,
            )}
          >
            <RecIcon className="h-4 w-4" />
            {rec.label}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Confidence */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <TrendingUp className="h-4 w-4" />
              AI Confidence
            </span>
            <span className="font-medium">{(result.confidence * 100).toFixed(1)}%</span>
          </div>
          <Progress value={result.confidence * 100} className="h-2" />
          <p className="text-xs text-muted-foreground">
            OCR extracted {result.raw_text_length.toLocaleString()} characters
          </p>
        </div>

        <Separator />

        {/* Invoice Details */}
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            { label: 'Vendor', value: result.vendor_name },
            { label: 'Invoice #', value: result.invoice_number },
            { label: 'Invoice Date', value: result.invoice_date },
            { label: 'Due Date', value: result.due_date },
            { label: 'Payment Terms', value: result.payment_terms },
            { label: 'Currency', value: result.currency },
          ].map(({ label, value }) =>
            value ? (
              <div key={label}>
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="text-sm font-medium">{value}</p>
              </div>
            ) : null,
          )}
        </div>

        <Separator />

        {/* Amounts */}
        <div className="rounded-lg bg-muted/50 p-4">
          <div className="space-y-1.5 text-sm">
            {result.subtotal !== null && result.subtotal !== undefined && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Subtotal</span>
                <span>{formatCurrency(result.subtotal, result.currency === 'USD' ? 'USD' : undefined)}</span>
              </div>
            )}
            {result.tax_amount !== null && result.tax_amount !== undefined && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Tax</span>
                <span>{formatCurrency(result.tax_amount)}</span>
              </div>
            )}
            {result.total_amount !== null && result.total_amount !== undefined && (
              <div className="flex justify-between border-t pt-1.5 font-semibold">
                <span>Total</span>
                <span>{formatCurrency(result.total_amount)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Line Items */}
        {result.line_items.length > 0 && (
          <>
            <Separator />
            <div>
              <p className="mb-3 text-sm font-medium">Line Items</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-xs text-muted-foreground">
                      <th className="pb-2 pr-4">Description</th>
                      <th className="pb-2 pr-4 text-right">Qty</th>
                      <th className="pb-2 pr-4 text-right">Unit Price</th>
                      <th className="pb-2 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.line_items.map((item, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-2 pr-4">{item.description ?? '—'}</td>
                        <td className="py-2 pr-4 text-right">{item.quantity ?? '—'}</td>
                        <td className="py-2 pr-4 text-right">
                          {item.unit_price != null ? formatCurrency(item.unit_price) : '—'}
                        </td>
                        <td className="py-2 text-right">
                          {item.total != null ? formatCurrency(item.total) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* Anomalies */}
        {result.anomalies.length > 0 && (
          <>
            <Separator />
            <div>
              <p className="mb-2 text-sm font-medium text-yellow-600">Anomalies Detected</p>
              <ul className="space-y-1">
                {result.anomalies.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-500" />
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}

        {/* Action Items */}
        {result.action_items.length > 0 && (
          <>
            <Separator />
            <div>
              <p className="mb-2 text-sm font-medium">Recommended Actions</p>
              <ol className="space-y-1 text-sm text-muted-foreground">
                {result.action_items.map((a, i) => (
                  <li key={i}>{i + 1}. {a}</li>
                ))}
              </ol>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
```

### `app/(dashboard)/dashboard/documents/page.tsx`
```tsx
import { InvoiceExtractor } from '@/components/documents/InvoiceExtractor';

export default function DocumentsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Document Intelligence</h1>
        <p className="text-muted-foreground">
          Upload invoices and financial documents for AI-powered data extraction.
        </p>
      </div>
      <InvoiceExtractor />
    </div>
  );
}
```

## Existing Files To Modify
None.

## API Contracts
Calls `POST /api/v1/documents/extract-invoice` (see 028).

## Database Tables
Not applicable.

## Business Logic
- After extraction, result stays displayed until user clicks "Upload new document".
- "Extract Data" button disabled until file upload completes.
- Result remains visible even if user removes the uploaded file.

## Validation Rules
- `fileUrl` must be set before extraction button is enabled.
- Error from API shown inline below the button.

## Error Handling
| Scenario | UI |
|----------|-----|
| Upload fails | FileUpload component handles inline |
| Extraction API error | Red alert below button |
| Timeout (45s) | API returns 422 with "timed out" message → shown in alert |
| No text extracted | Results shown with low confidence + review recommendation |

## UI Behavior
- Upload card: shows `FileUpload` component, "Extract Data" button
- Loading: button shows spinner + "Extracting… (up to 45s)"
- Result: full `InvoiceResultCard` below upload card
- "Upload new document" button resets both file and result

## Component Breakdown
| Component | Responsibility |
|-----------|---------------|
| `InvoiceExtractor` | Orchestrates upload → extract flow |
| `InvoiceResultCard` | Displays extraction results |
| `useInvoiceExtraction` | API call management |

## State Management
- `fileUrl`: local state in `InvoiceExtractor`
- `result`, `isLoading`, `error`: managed by `useInvoiceExtraction` hook

## Loading States
- Extract button: spinner + long-form text ("Extracting… (up to 45s)")
- No skeleton — results appear only after completion

## Empty States
- No result yet: only upload card shown
- Result with empty `line_items`: table not rendered
- Result with empty `anomalies`: anomalies section not rendered

## Edge Cases
- User removes file after extraction: result still visible; "Upload new document" resets both.
- Very low confidence (< 0.3): still displayed, payment_recommendation will be "review".
- Large line items table: horizontally scrollable on mobile.

## Test Cases
1. Upload component present on page.
2. "Extract Data" button disabled before file uploaded.
3. After file upload, button enabled.
4. Clicking Extract calls `POST /documents/extract-invoice`.
5. Loading state shown during extraction.
6. Result card renders with payment recommendation badge.
7. Line items table renders for invoices with line items.
8. Anomalies section shows when anomalies present.
9. "Upload new document" resets all state.
10. API error shown in alert box.

## Acceptance Criteria
- [ ] File upload integrated on document page
- [ ] Extraction API called on button click
- [ ] Invoice data displayed in organized card
- [ ] Payment recommendation badge color-coded
- [ ] Line items shown in table
- [ ] Anomalies and action items displayed
- [ ] Reset to upload new document works

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Loading state handles 45-second timeout gracefully
