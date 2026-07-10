# 026 – Workflow Viewer

## Objective
Build the frontend Workflow Viewer component that visualizes the LangGraph pipeline execution as an interactive step-by-step timeline, showing each node's name, status, execution time, and data. Used in both the AI Inbox result panel and the Workflow History page.

## Scope
- `components/workflow/WorkflowViewer.tsx` — main timeline component
- `components/workflow/WorkflowStep.tsx` — individual step card
- Step data rendering for each node type (intent, confidence, router, agent)
- Animated step reveal as workflow completes in real time

## Out of Scope
- Backend workflow (025)
- Workflow History page (033)
- Workflow history API (030)

## Functional Requirements
1. Render each step from `submission.result.steps` as a timeline entry.
2. Each step shows: node name (formatted), status icon, step data summary.
3. Completed steps show in green, failed steps in red, in-progress in blue pulse.
4. Step data shows key fields (intent, score, agent, etc.) in a compact key-value grid.
5. Steps animate in sequentially (staggered entrance) when first rendered.
6. Collapsible raw data toggle per step for debugging.
7. Empty state when no steps available.

## Technical Requirements
- Framer Motion for staggered animations
- Lucide icons for status indicators
- Shadcn `Collapsible` for step detail toggle
- TypeScript: props typed against `WorkflowStep` interface from types

## Folder Structure
```
frontend/
└── components/
    └── workflow/
        ├── WorkflowViewer.tsx
        └── WorkflowStep.tsx
```

## Files To Create

### `components/workflow/WorkflowStep.tsx`
```tsx
'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, XCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface StepData {
  step_name: string;
  status: 'completed' | 'failed' | 'started';
  data: Record<string, unknown>;
  error?: string | null;
}

interface WorkflowStepProps {
  step: StepData;
  index: number;
  isLast: boolean;
}

const NODE_LABELS: Record<string, string> = {
  ocr_node: 'Document OCR',
  intent_node: 'Intent Detection',
  confidence_node: 'Confidence Scoring',
  router_node: 'Agent Routing',
  sales_agent_node: 'Sales Agent',
  support_agent_node: 'Support Agent',
  finance_agent_node: 'Finance Agent',
  executive_agent_node: 'Executive Agent',
  persist_node: 'Result Saved',
};

export function WorkflowStep({ step, index, isLast }: WorkflowStepProps) {
  const [expanded, setExpanded] = useState(false);

  const label = NODE_LABELS[step.step_name] ?? step.step_name;
  const isCompleted = step.status === 'completed';
  const isFailed = step.status === 'failed';

  const dataEntries = Object.entries(step.data ?? {}).filter(
    ([, v]) => v !== null && v !== undefined,
  );

  return (
    <motion.div
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.08, duration: 0.3 }}
      className="flex gap-4"
    >
      {/* ── Connector line + icon ───────────────────────────────────────── */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border-2',
            isCompleted && 'border-green-500 bg-green-50 dark:bg-green-900/20',
            isFailed && 'border-destructive bg-destructive/10',
            !isCompleted && !isFailed && 'border-blue-500 bg-blue-50 dark:bg-blue-900/20',
          )}
        >
          {isCompleted && <CheckCircle2 className="h-4 w-4 text-green-500" />}
          {isFailed && <XCircle className="h-4 w-4 text-destructive" />}
          {!isCompleted && !isFailed && (
            <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
          )}
        </div>
        {!isLast && <div className="mt-1 w-0.5 flex-1 bg-border" />}
      </div>

      {/* ── Step content ────────────────────────────────────────────────── */}
      <div className="mb-4 flex-1 rounded-lg border bg-card p-4">
        <div className="flex items-center justify-between">
          <p className="font-medium">{label}</p>
          {dataEntries.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setExpanded(!expanded)}
              aria-label={expanded ? 'Collapse step details' : 'Expand step details'}
            >
              {expanded ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
            </Button>
          )}
        </div>

        {/* Compact data summary */}
        {dataEntries.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {dataEntries.slice(0, expanded ? undefined : 3).map(([key, value]) => (
              <span
                key={key}
                className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs"
              >
                <span className="text-muted-foreground capitalize">
                  {key.replace(/_/g, ' ')}:
                </span>
                <span className="font-medium">
                  {typeof value === 'number'
                    ? value.toFixed(2)
                    : String(value)}
                </span>
              </span>
            ))}
          </div>
        )}

        {/* Error display */}
        {isFailed && step.error && (
          <p className="mt-2 text-xs text-destructive">{step.error}</p>
        )}
      </div>
    </motion.div>
  );
}
```

### `components/workflow/WorkflowViewer.tsx`
```tsx
'use client';

import { WorkflowStep } from './WorkflowStep';
import { GitBranch } from 'lucide-react';

interface Step {
  step_name: string;
  status: 'completed' | 'failed' | 'started';
  data: Record<string, unknown>;
  error?: string | null;
}

interface WorkflowViewerProps {
  steps: Step[];
  className?: string;
}

export function WorkflowViewer({ steps, className }: WorkflowViewerProps) {
  if (!steps || steps.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-8 text-center">
        <GitBranch className="h-8 w-8 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">No workflow steps recorded</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {steps.map((step, i) => (
        <WorkflowStep
          key={`${step.step_name}-${i}`}
          step={step}
          index={i}
          isLast={i === steps.length - 1}
        />
      ))}
    </div>
  );
}
```

## Existing Files To Modify
- `components/inbox/ResultPanel.tsx` (014) — add `<WorkflowViewer steps={submission.result?.steps ?? []} />` section

## API Contracts
No backend calls — reads from `submission.result.steps` array already in state.

## Request Examples
```tsx
<WorkflowViewer
  steps={[
    { step_name: "intent_node", status: "completed", data: { intent: "sales_lead", from_cache: false } },
    { step_name: "confidence_node", status: "completed", data: { score: 0.88 } },
    { step_name: "router_node", status: "completed", data: { agent: "sales", escalated: false } },
    { step_name: "sales_agent_node", status: "completed", data: { lead_score: 87, urgency: "hot" } },
  ]}
/>
```

## Response Examples
Renders a vertical timeline with 4 steps, each with an icon, label, and data pills.

## Database Tables
Not applicable — reads from existing submission data.

## Business Logic
- Node name → human-readable label via `NODE_LABELS` map.
- Data keys formatted: underscores replaced with spaces, capitalized.
- Max 3 data pills shown collapsed; all shown when expanded.
- Steps with `status = "failed"` show red styling and `step.error` text.

## Validation Rules
- `steps` prop is nullable — empty state shown if null/undefined/empty.

## Error Handling
- Unknown `step_name` falls back to the raw name.
- Missing `step.data` renders no pills.

## UI Behavior
- Vertical timeline with connecting line between steps
- Each step: circular status icon + card
- Steps animate in sequentially (80ms stagger)
- Expand/collapse per step for full data
- Failed step: red icon, red border, error text

## Component Breakdown
| Component | Props |
|-----------|-------|
| `WorkflowViewer` | steps[], className? |
| `WorkflowStep` | step, index, isLast |

## State Management
Local `useState` for step expand/collapse. No global state.

## Loading States
No loading state — component only renders when steps data is available.

## Empty States
- `steps = []` or `steps = undefined`: shows empty state with icon and message.

## Edge Cases
- `step.data` is an empty object: no pills shown, no expand button.
- `step.data` value is `0` (falsy but valid): shown correctly — filter checks `!== null && !== undefined`.
- Very long node names not in `NODE_LABELS`: displayed as-is (no truncation needed — all known names are short).

## Test Cases
1. `WorkflowViewer` renders correct number of steps.
2. Completed step shows green icon.
3. Failed step shows red icon and error text.
4. Data pills render for each key-value pair.
5. Expand button shows all data entries.
6. Empty steps array shows empty state.
7. Steps animate with stagger delay.
8. Last step has no connecting line.

## Acceptance Criteria
- [ ] All known node names mapped to human-readable labels
- [ ] Completed/failed/in-progress states render correctly
- [ ] Data pills show key step metrics
- [ ] Expand/collapse per step works
- [ ] Animation plays on render
- [ ] Empty state displays when no steps

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Accessible: icon buttons have `aria-label`
