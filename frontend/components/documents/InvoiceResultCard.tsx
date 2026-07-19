'use client';

import { CheckCircle2, AlertTriangle, Clock, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
