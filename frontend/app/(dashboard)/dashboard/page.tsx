'use client';

import { MetricsRow } from '@/components/dashboard/MetricsRow';
import { ActivitySparkline } from '@/components/dashboard/ActivitySparkline';
import { AgentUtilizationBar } from '@/components/dashboard/AgentUtilizationBar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function DashboardPage() {
  return (
    <div className="space-y-8 pb-16 md:pb-24 animate-in fade-in-50 duration-300">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Dashboard</h1>
        <p className="text-muted-foreground mt-1.5">
          Welcome back. Your AI-powered inbox orchestration is running smoothly.
        </p>
      </div>

      {/* Dynamic Metrics Cards Row */}
      <MetricsRow />

      {/* Dynamic Charts Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ActivitySparkline />
        <AgentUtilizationBar />
      </div>

      {/* Feature showcase callout card */}
      <Card className="bg-[#001e2b] text-white border-0 shadow-lg relative overflow-hidden rounded-xl">
        <div className="absolute right-0 bottom-0 top-0 w-1/3 bg-gradient-to-l from-[#00a35c]/10 to-transparent pointer-events-none" />
        <CardHeader className="relative z-10">
          <CardTitle className="text-xl text-white font-bold">One data platform. Unlimited AI potential.</CardTitle>
          <CardDescription className="text-white/70 max-w-xl mt-1.5 text-sm">
            FlowPilot AI automatically classifies incoming documents, scores confidence levels, and invokes specialized agent pipelines.
          </CardDescription>
        </CardHeader>
        <CardContent className="relative z-10 pt-2 pb-6">
          <a
            href="/dashboard/inbox"
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#00ed64] hover:bg-[#00b545] text-[#001e2b] text-sm font-semibold rounded-full shadow transition-all cursor-pointer"
          >
            Explore AI Inbox
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
