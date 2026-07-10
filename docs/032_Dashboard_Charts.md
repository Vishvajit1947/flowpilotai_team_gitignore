# 032 – Dashboard Charts

## Objective
Add charts to the main dashboard page: a mini activity sparkline showing submissions over the last 7 days, and an agent utilization bar chart showing which agents are most active. These supplement the metric cards (013) to give the dashboard a richer at-a-glance view.

## Scope
- `components/dashboard/ActivitySparkline.tsx` — 7-day trend sparkline
- `components/dashboard/AgentUtilizationBar.tsx` — horizontal bar chart of agent activity
- Integration into `app/(dashboard)/dashboard/page.tsx`

## Out of Scope
- Full analytics page (031)
- Analytics API (030) — reuses existing hooks

## Functional Requirements
1. Sparkline shows submission counts for the last 7 days (area chart, no axes, compact).
2. Agent utilization shows horizontal bars for each agent type with count label.
3. Both charts use existing `useAnalyticsByDay` and `useAnalyticsByAgent` hooks.
4. Loading skeletons for both charts.
5. Charts hidden if all values are zero (show "Start submitting to see trends" message).

## Technical Requirements
- Recharts `AreaChart`, `Bar` (horizontal)
- Existing hooks from 031

## Folder Structure
```
frontend/
└── components/
    └── dashboard/
        ├── ActivitySparkline.tsx
        └── AgentUtilizationBar.tsx
```

## Files To Create

### `components/dashboard/ActivitySparkline.tsx`
```tsx
'use client';

import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts';
import { useAnalyticsByDay } from '@/hooks/useAnalyticsByDay';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp } from 'lucide-react';

export function ActivitySparkline() {
  const { data, isLoading } = useAnalyticsByDay(7);

  const total = data.reduce((acc, b) => acc + b.count, 0);
  const allZero = total === 0;

  const chartData = data.map((b) => ({
    date: new Date(b.date).toLocaleDateString('en-US', { weekday: 'short' }),
    count: b.count,
  }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <TrendingUp className="h-4 w-4 text-primary" />
          7-Day Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-20 animate-pulse rounded bg-muted" />
        ) : allZero ? (
          <div className="flex h-20 items-center justify-center">
            <p className="text-xs text-muted-foreground">
              Start submitting to see trends
            </p>
          </div>
        ) : (
          <>
            <p className="mb-2 text-2xl font-bold">{total} <span className="text-sm font-normal text-muted-foreground">submissions</span></p>
            <ResponsiveContainer width="100%" height={80}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="sparkGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Tooltip
                  contentStyle={{ borderRadius: '6px', fontSize: '12px' }}
                  formatter={(v: number) => [v, 'Submissions']}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  fill="url(#sparkGradient)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </>
        )}
      </CardContent>
    </Card>
  );
}
```

### `components/dashboard/AgentUtilizationBar.tsx`
```tsx
'use client';

import { useAnalyticsByAgent } from '@/hooks/useAnalyticsByAgent';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Bot } from 'lucide-react';
import { cn } from '@/lib/utils';

const AGENT_COLORS: Record<string, string> = {
  sales: 'bg-blue-500',
  support: 'bg-green-500',
  finance: 'bg-purple-500',
  executive: 'bg-orange-500',
};

export function AgentUtilizationBar() {
  const { data, isLoading } = useAnalyticsByAgent();

  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const total = data.reduce((acc, d) => acc + d.count, 0);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Bot className="h-4 w-4 text-primary" />
          Agent Utilization
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-7 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ) : total === 0 ? (
          <div className="flex h-28 items-center justify-center">
            <p className="text-xs text-muted-foreground">No submissions yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {data.map((agent) => (
              <div key={agent.agent}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="font-medium capitalize">{agent.agent}</span>
                  <span className="text-muted-foreground">{agent.count}</span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all duration-500',
                      AGENT_COLORS[agent.agent] ?? 'bg-primary',
                    )}
                    style={{ width: `${(agent.count / maxCount) * 100}%` }}
                    role="progressbar"
                    aria-valuenow={agent.count}
                    aria-valuemax={maxCount}
                    aria-label={`${agent.agent} agent: ${agent.count} submissions`}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### Update `app/(dashboard)/dashboard/page.tsx`
```tsx
import { MetricsRow } from '@/components/dashboard/MetricsRow';
import { ActivitySparkline } from '@/components/dashboard/ActivitySparkline';
import { AgentUtilizationBar } from '@/components/dashboard/AgentUtilizationBar';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Your AI workflow overview at a glance.
        </p>
      </div>
      <MetricsRow />
      <div className="grid gap-6 lg:grid-cols-2">
        <ActivitySparkline />
        <AgentUtilizationBar />
      </div>
    </div>
  );
}
```

## Existing Files To Modify
- `app/(dashboard)/dashboard/page.tsx` — add charts section

## API Contracts
Reuses existing hooks that call `/analytics/by-day?days=7` and `/analytics/by-agent`.

## Database Tables
Not applicable.

## Business Logic
- `ActivitySparkline` passes `days=7` to `useAnalyticsByDay` — hardcoded, no selector.
- `AgentUtilizationBar` uses `maxCount` to normalize bars (widest bar = 100%).
- Both charts hidden (replaced with empty state) when all values are 0.

## Validation Rules
Not applicable.

## Error Handling
- Both charts gracefully degrade — `isLoading` skeleton and `allZero`/no data empty states.
- No error states on dashboard charts (non-critical — full analytics page has error handling).

## UI Behavior
- Sparkline: no axes, no grid, compact area chart with gradient fill
- Agent bars: horizontal progress bars with label and count
- Two-column grid on lg+, stacked on mobile
- Bar width animated via CSS `transition-all duration-500`

## Component Breakdown
| Component | Chart Type |
|-----------|-----------|
| `ActivitySparkline` | Recharts AreaChart |
| `AgentUtilizationBar` | Custom CSS bars |

## State Management
Both components manage local state via hooks. No global state.

## Loading States
- Sparkline: single gray rectangle (h-20)
- Agent bars: 4 gray skeleton bars

## Empty States
- Sparkline: "Start submitting to see trends"
- Agent bars: "No submissions yet"

## Edge Cases
- Single agent used: single bar at 100% width.
- All same count: all bars equal width.
- 0 submissions on some days: those points show as 0 in sparkline.

## Test Cases
1. Sparkline renders area chart with 7 data points.
2. Total count shown above sparkline.
3. Agent bars width proportional to counts.
4. Loading state renders skeletons.
5. Empty state shown when all counts = 0.
6. `role="progressbar"` on agent bars (accessibility).

## Acceptance Criteria
- [ ] Sparkline shows 7-day activity trend
- [ ] Agent bars show correct relative widths
- [ ] Loading skeletons shown while fetching
- [ ] Empty states shown when no data
- [ ] Charts added to dashboard page

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- `role="progressbar"` on agent bar elements
