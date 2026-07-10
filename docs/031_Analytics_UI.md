# 031 – Analytics UI

## Objective
Build the Analytics page that displays submission statistics, agent distribution, and daily activity trends using Recharts visualizations, summary stats cards, and a date range selector.

## Scope
- `app/(dashboard)/dashboard/analytics/page.tsx` — Analytics page
- `components/analytics/AnalyticsSummaryCards.tsx` — top-line stats grid
- `components/analytics/AgentDistributionChart.tsx` — pie/donut chart by agent
- `components/analytics/DailyActivityChart.tsx` — bar chart of submissions per day
- `hooks/useAnalyticsByAgent.ts` and `hooks/useAnalyticsByDay.ts` — data fetching hooks
- Date range selector (7 / 14 / 30 / 90 days)

## Out of Scope
- Analytics API (030)
- Dashboard metric cards (013)

## Functional Requirements
1. Page shows 4 summary cards (total, completed, failed, avg confidence).
2. Agent distribution shown as a donut chart with legend.
3. Daily activity shown as a bar chart.
4. Date range selector (7, 14, 30, 90 days) updates `by-day` chart.
5. All sections show loading skeletons while fetching.
6. Error states with retry buttons.

## Technical Requirements
- Recharts `PieChart`, `BarChart`, `ResponsiveContainer`
- `useAnalytics` hook from 013 reused for summary
- New hooks for by-agent and by-day data

## Folder Structure
```
frontend/
├── app/
│   └── (dashboard)/
│       └── dashboard/
│           └── analytics/
│               └── page.tsx
└── components/
    └── analytics/
        ├── AnalyticsSummaryCards.tsx
        ├── AgentDistributionChart.tsx
        └── DailyActivityChart.tsx
```

## Files To Create

### `hooks/useAnalyticsByAgent.ts`
```typescript
'use client';
import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

interface AgentBreakdown {
  agent: string;
  count: number;
  avg_confidence: number;
  completed: number;
  failed: number;
}

interface ByAgentResponse { agents: AgentBreakdown[]; }

export function useAnalyticsByAgent() {
  const [data, setData] = useState<AgentBreakdown[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true); setError(null);
    try {
      const res = await api.get<ByAgentResponse>('/analytics/by-agent');
      setData(res.data.agents);
    } catch { setError('Failed to load agent analytics'); }
    finally { setIsLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);
  return { data, isLoading, error, refetch: fetch };
}
```

### `hooks/useAnalyticsByDay.ts`
```typescript
'use client';
import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

interface DayBucket { date: string; count: number; }
interface ByDayResponse { days: number; buckets: DayBucket[]; }

export function useAnalyticsByDay(days: number) {
  const [data, setData] = useState<DayBucket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true); setError(null);
    try {
      const res = await api.get<ByDayResponse>(`/analytics/by-day?days=${days}`);
      setData(res.data.buckets);
    } catch { setError('Failed to load daily analytics'); }
    finally { setIsLoading(false); }
  }, [days]);

  useEffect(() => { fetch(); }, [fetch]);
  return { data, isLoading, error, refetch: fetch };
}
```

### `components/analytics/AgentDistributionChart.tsx`
```tsx
'use client';

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useAnalyticsByAgent } from '@/hooks/useAnalyticsByAgent';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { RefreshCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

const AGENT_COLORS: Record<string, string> = {
  sales: '#3b82f6',
  support: '#22c55e',
  finance: '#a855f7',
  executive: '#f97316',
};

export function AgentDistributionChart() {
  const { data, isLoading, error, refetch } = useAnalyticsByAgent();

  if (error) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 p-8">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={refetch} className="gap-2">
            <RefreshCcw className="h-4 w-4" /> Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle>Agent Distribution</CardTitle></CardHeader>
        <CardContent>
          <div className="h-64 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>Agent Distribution</CardTitle></CardHeader>
        <CardContent className="flex h-64 items-center justify-center">
          <p className="text-sm text-muted-foreground">No data yet</p>
        </CardContent>
      </Card>
    );
  }

  const chartData = data.map((d) => ({
    name: d.agent.charAt(0).toUpperCase() + d.agent.slice(1),
    value: d.count,
    color: AGENT_COLORS[d.agent] ?? '#94a3b8',
  }));

  return (
    <Card>
      <CardHeader><CardTitle>Agent Distribution</CardTitle></CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={110}
              paddingAngle={3}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string) => [value, name]}
              contentStyle={{ borderRadius: '8px', fontSize: '13px' }}
            />
            <Legend
              formatter={(value) => (
                <span className="text-sm">{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

### `components/analytics/DailyActivityChart.tsx`
```tsx
'use client';

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { useAnalyticsByDay } from '@/hooks/useAnalyticsByDay';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RefreshCcw } from 'lucide-react';
import { cn } from '@/lib/utils';

const DATE_RANGES = [7, 14, 30, 90] as const;

interface DailyActivityChartProps {
  days: number;
  onDaysChange: (d: number) => void;
}

export function DailyActivityChart({ days, onDaysChange }: DailyActivityChartProps) {
  const { data, isLoading, error, refetch } = useAnalyticsByDay(days);

  // Abbreviate date labels
  const chartData = data.map((b) => ({
    date: new Date(b.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    count: b.count,
  }));

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>Daily Activity</CardTitle>
          <div className="flex gap-1">
            {DATE_RANGES.map((d) => (
              <Button
                key={d}
                variant={days === d ? 'default' : 'outline'}
                size="sm"
                onClick={() => onDaysChange(d)}
                className="h-7 px-3 text-xs"
              >
                {d}d
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="flex flex-col items-center gap-3 py-8">
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="outline" size="sm" onClick={refetch} className="gap-2">
              <RefreshCcw className="h-4 w-4" /> Retry
            </Button>
          </div>
        ) : isLoading ? (
          <div className="h-64 animate-pulse rounded bg-muted" />
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} margin={{ top: 4, right: 4, left: -16, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                interval={days > 30 ? 6 : days > 14 ? 3 : 1}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{ borderRadius: '8px', fontSize: '13px' }}
                formatter={(v: number) => [v, 'Submissions']}
              />
              <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
```

### `components/analytics/AnalyticsSummaryCards.tsx`
```tsx
'use client';

import { Inbox, CheckCircle2, XCircle, TrendingUp } from 'lucide-react';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { useAnalytics } from '@/hooks/useAnalytics';
import { Button } from '@/components/ui/button';
import { RefreshCcw } from 'lucide-react';

export function AnalyticsSummaryCards() {
  const { data, isLoading, error, refetch } = useAnalytics();

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-8">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" size="sm" onClick={refetch} className="gap-2">
          <RefreshCcw className="h-4 w-4" /> Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="Total Submissions" value={data?.total_submissions ?? 0} icon={Inbox} isLoading={isLoading} colorClass="text-blue-500" />
      <MetricCard label="Completed" value={data?.completed ?? 0} icon={CheckCircle2} isLoading={isLoading} colorClass="text-green-500" />
      <MetricCard label="Failed" value={data?.failed ?? 0} icon={XCircle} isLoading={isLoading} colorClass="text-red-500" />
      <MetricCard label="Avg Confidence" value={data?.avg_confidence ?? 0} icon={TrendingUp} format="percent" isLoading={isLoading} colorClass="text-purple-500" />
    </div>
  );
}
```

### `app/(dashboard)/dashboard/analytics/page.tsx`
```tsx
'use client';

import { useState } from 'react';
import { AnalyticsSummaryCards } from '@/components/analytics/AnalyticsSummaryCards';
import { AgentDistributionChart } from '@/components/analytics/AgentDistributionChart';
import { DailyActivityChart } from '@/components/analytics/DailyActivityChart';

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">
          Insights into your AI workflow performance.
        </p>
      </div>
      <AnalyticsSummaryCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <AgentDistributionChart />
        <DailyActivityChart days={days} onDaysChange={setDays} />
      </div>
    </div>
  );
}
```

## Existing Files To Modify
None.

## API Contracts
- `GET /api/v1/analytics/summary` — see 030
- `GET /api/v1/analytics/by-agent` — see 030
- `GET /api/v1/analytics/by-day?days=N` — see 030

## Database Tables
Not applicable — frontend only.

## Business Logic
- Date range selector (7/14/30/90) updates `days` state which refetches `by-day` data.
- `DailyActivityChart` receives `days` as a prop — parent page owns the state.
- X-axis tick interval adjusts based on date range to avoid label crowding.

## Validation Rules
Not applicable.

## Error Handling
| Scenario | UI |
|----------|-----|
| API error (any chart) | Error message + retry button in that chart card |
| Loading | Gray pulse skeleton inside card |
| No data | Empty state message inside card |

## UI Behavior
- Summary cards: same as 013 (reused `MetricCard`)
- Donut chart: innerRadius donut with legend
- Bar chart: blue bars with rounded tops, grid lines
- Date range: button group top-right of bar chart card
- Two charts side by side on lg+, stacked on mobile

## Component Breakdown
| Component | Responsibility |
|-----------|---------------|
| `AnalyticsSummaryCards` | Reuses MetricCard for summary |
| `AgentDistributionChart` | Recharts PieChart |
| `DailyActivityChart` | Recharts BarChart + date selector |

## State Management
- `days: number` — owned by page, passed to `DailyActivityChart`
- Each chart manages its own loading/error via hook

## Loading States
- Per-chart: gray pulse rectangle filling chart area height (h-64)

## Empty States
- Charts with no data: centered "No data yet" message
- Summary cards showing 0 are valid (not empty state)

## Edge Cases
- All 0 values: bar chart renders empty bars, donut renders nothing → handled by `data.length === 0` check.
- 90-day range with many submissions: XAxis tick interval set to every 6 days.
- Recharts responsive container on mobile: `ResponsiveContainer width="100%"`.

## Test Cases
1. Page renders all 3 chart sections.
2. Summary cards show correct values.
3. Donut chart renders one segment per agent.
4. Selecting "14d" button refetches with `days=14`.
5. Error state shows retry button.
6. Retry button triggers refetch.
7. Empty agent data shows "No data yet".

## Acceptance Criteria
- [ ] Summary cards display correctly
- [ ] Agent distribution donut chart renders
- [ ] Daily bar chart renders
- [ ] Date range selector updates chart data
- [ ] Loading skeletons shown per chart
- [ ] Error + retry per chart

## Definition of Done
- All acceptance criteria checked
- No TypeScript errors
- Recharts charts responsive on all viewports
