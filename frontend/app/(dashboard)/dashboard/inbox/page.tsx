import { InboxForm } from '@/components/inbox/InboxForm';
import { ResultPanel } from '@/components/inbox/ResultPanel';
import { SubmissionHistory } from '@/components/inbox/SubmissionHistory';

export default function InboxPage() {
  return (
    <div className="space-y-4 lg:space-y-6 lg:h-full lg:flex lg:flex-col lg:overflow-hidden">
      <div className="flex-shrink-0">
        <h1 className="text-3xl font-bold tracking-tight">AI Inbox</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Submit text queries or upload business documents. The AI orchestration engine will detect intent, score confidence, and route tasks to specialized agents.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 lg:flex-1 lg:min-h-0">
        <div className="flex flex-col gap-4 lg:min-h-0 lg:h-full">
          <div className="flex-shrink-0">
            <InboxForm />
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto pr-1">
            <SubmissionHistory />
          </div>
        </div>
        <div className="lg:h-full lg:min-h-0">
          <ResultPanel />
        </div>
      </div>
    </div>
  );
}
