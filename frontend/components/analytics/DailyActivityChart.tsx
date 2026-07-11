'use client';

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { useAnalyticsByDay } from '@/hooks/useAnalyticsByDay';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RefreshCcw } from 'lucide-react';

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
