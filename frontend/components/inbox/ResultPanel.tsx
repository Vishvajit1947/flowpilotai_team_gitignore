'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useInboxStore } from '@/store/inbox';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, XCircle, Clock, Brain, Square, CheckSquare, Sparkles, Building, Mail, User, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDateTime } from '@/lib/utils';
import { WorkflowViewer } from '@/components/workflow/WorkflowViewer';
import type { AgentType, WorkflowStatus } from '@/types';

const AGENT_COLORS: Record<AgentType, string> = {
  sales: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  support: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  finance: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  executive: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
};

const STATUS_ICONS: Record<WorkflowStatus, React.ReactNode> = {
  pending: <Clock className="h-4 w-4 text-muted-foreground animate-pulse" />,
  processing: (
    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
  ),
  completed: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  failed: <XCircle className="h-4 w-4 text-destructive" />,
};

export function ResultPanel() {
  const currentSubmission = useInboxStore((s) => s.currentSubmission);
  const isPolling = useInboxStore((s) => s.isPolling);
  const toggleActionItem = useInboxStore((s) => s.toggleActionItem);

  // Render styled structured data based on agent type
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const renderStructuredData = (agentType: string, data: Record<string, any>) => {
    if (!data) return null;

    if (agentType === 'sales') {
      return (
        <div className="grid grid-cols-2 gap-3 bg-muted/30 p-3 rounded-lg border text-sm">
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Company Name</span>
            <span className="font-semibold flex items-center gap-1.5"><Building className="h-3.5 w-3.5 text-muted-foreground" /> {data.company_name || 'Unknown'}</span>
          </div>
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Contact Name</span>
            <span className="font-semibold flex items-center gap-1.5"><User className="h-3.5 w-3.5 text-muted-foreground" /> {data.contact_name || 'Unknown'}</span>
          </div>
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Contact Email</span>
            <span className="font-semibold flex items-center gap-1.5"><Mail className="h-3.5 w-3.5 text-muted-foreground" /> {data.contact_email || 'None'}</span>
          </div>
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Deal Estimate</span>
            <span className="font-bold text-blue-600 dark:text-blue-400">{data.deal_size_estimate || 'Unknown'}</span>
          </div>
          <div className="col-span-2 space-y-1 border-t pt-2 mt-1">
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground font-medium">Lead Qualification Score</span>
              <span className="font-bold text-foreground">{data.lead_score ?? 50}/100</span>
            </div>
            <Progress value={data.lead_score ?? 50} className="h-1.5" />
          </div>
        </div>
      );
    }

    if (agentType === 'support') {
      const severityColors: Record<string, string> = {
        critical: 'text-red-600 bg-red-50 dark:bg-red-950/20 dark:text-red-400',
        high: 'text-orange-600 bg-orange-50 dark:bg-orange-950/20 dark:text-orange-400',
        medium: 'text-blue-600 bg-blue-50 dark:bg-blue-950/20 dark:text-blue-400',
        low: 'text-green-600 bg-green-50 dark:bg-green-950/20 dark:text-green-400',
      };

      return (
        <div className="grid grid-cols-2 gap-3 bg-muted/30 p-3 rounded-lg border text-sm">
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Issue Type</span>
            <span className="font-semibold capitalize">{data.issue_type || 'Inquiry'}</span>
          </div>
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Severity</span>
            <Badge className={cn('text-[10px] uppercase font-bold border', severityColors[data.severity] || 'bg-muted')}>
              {data.severity || 'medium'}
            </Badge>
          </div>
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Product Area</span>
            <span className="font-semibold">{data.product_area || 'General'}</span>
          </div>
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">SLA Recommendation</span>
            <span className="font-semibold flex items-center gap-1.5"><Clock className="h-3.5 w-3.5 text-muted-foreground" /> {data.sla_recommendation || '24h'}</span>
          </div>
          {data.response_draft && (
            <div className="col-span-2 space-y-1 border-t pt-2 mt-1">
              <span className="text-xs text-muted-foreground block font-medium">Suggested Customer Response</span>
              <p className="text-xs italic bg-background p-2 rounded border leading-relaxed text-muted-foreground">
                &ldquo;{data.response_draft}&rdquo;
              </p>
            </div>
          )}
        </div>
      );
    }

    if (agentType === 'finance') {
      return (
        <div className="grid grid-cols-2 gap-3 bg-muted/30 p-3 rounded-lg border text-sm">
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Vendor Name</span>
            <span className="font-semibold flex items-center gap-1.5"><Building className="h-3.5 w-3.5 text-muted-foreground" /> {data.vendor_name || 'Unknown'}</span>
          </div>
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Invoice Number</span>
            <span className="font-semibold font-mono">{data.invoice_number || 'N/A'}</span>
          </div>
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Due Date</span>
            <span className="font-semibold">{data.due_date || 'N/A'}</span>
          </div>
          <div className="space-y-0.5">
            <span className="text-xs text-muted-foreground block font-medium">Total Amount Due</span>
            <span className="font-bold text-purple-600 dark:text-purple-400">{data.total_amount_due || 'Unknown'}</span>
          </div>
          {data.tax_amount && (
            <div className="space-y-0.5">
              <span className="text-xs text-muted-foreground block font-medium">Tax Amount</span>
              <span className="font-semibold">{data.tax_amount}</span>
            </div>
          )}
        </div>
      );
    }

    // Default fallback list
    return (
      <div className="bg-muted/30 p-3 rounded-lg border text-sm space-y-1.5 max-h-[160px] overflow-y-auto font-mono text-xs">
        {Object.entries(data).map(([key, val]) => (
          <div key={key} className="flex justify-between">
            <span className="text-muted-foreground">{key}:</span>
            <span className="font-semibold truncate max-w-[200px]">{JSON.stringify(val)}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <AnimatePresence mode="wait">
      {!currentSubmission ? (
        <motion.div
          key="empty"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed p-12 text-center h-[400px] lg:h-full"
        >
          <Brain className="h-12 w-12 text-muted-foreground/40 animate-pulse" />
          <div>
            <p className="font-medium text-muted-foreground">No submission yet</p>
            <p className="text-sm text-muted-foreground/70">
              Submit a message or document to start the AI workflow
            </p>
          </div>
        </motion.div>
      ) : (
        <motion.div
          key={currentSubmission.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className="lg:h-full lg:flex lg:flex-col lg:min-h-0"
        >
          <Card className="shadow-sm border-border lg:h-full lg:flex lg:flex-col lg:min-h-0">
            <CardHeader className="pb-3 border-b flex-shrink-0">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary animate-pulse" /> Workflow Analysis
                </CardTitle>
                <div className="flex items-center gap-2">
                  {STATUS_ICONS[currentSubmission.status]}
                  <span className="text-sm font-medium capitalize text-muted-foreground">
                    {currentSubmission.status}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6 pt-4 lg:flex-1 lg:overflow-y-auto pr-1">
              {/* Agent + Intent metadata */}
              {(currentSubmission.assigned_agent || currentSubmission.detected_intent) && (
                <div className="flex flex-wrap gap-2">
                  {currentSubmission.assigned_agent && (
                    <span
                      className={cn(
                        'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider',
                        AGENT_COLORS[currentSubmission.assigned_agent as AgentType] || 'bg-muted text-muted-foreground',
                      )}
                    >
                      {String(currentSubmission.assigned_agent).toUpperCase()} Agent
                    </span>
                  )}
                  {currentSubmission.detected_intent && (
                    <Badge variant="outline" className="text-xs uppercase tracking-wider font-semibold">
                      Intent: {currentSubmission.detected_intent}
                    </Badge>
                  )}
                </div>
              )}

              {/* Confidence Score Bar */}
              {currentSubmission.confidence_score !== null && currentSubmission.confidence_score !== undefined && (
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    <span>Confidence Score</span>
                    <span className="font-bold">
                      {(currentSubmission.confidence_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <Progress
                    value={currentSubmission.confidence_score * 100}
                    className="h-2"
                  />
                  {currentSubmission.confidence_score < 0.5 && (
                    <p className="text-xs text-yellow-600 bg-yellow-50 dark:bg-yellow-950/20 dark:text-yellow-400 p-2.5 rounded flex gap-1.5 items-start">
                      <AlertTriangle className="h-4 w-4 flex-shrink-0 text-yellow-500" />
                      <span>Low confidence classification. Workflow routed to Executive Agent for audit.</span>
                    </p>
                  )}
                </div>
              )}

              {/* Execution Steps */}
              {currentSubmission.result?.steps && currentSubmission.result.steps.length > 0 && (
                <div className="border-t pt-4">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                    Execution Steps
                  </h4>
                  <WorkflowViewer steps={currentSubmission.result.steps} />
                </div>
              )}

              {/* Result Content */}
              {currentSubmission.status === 'completed' && currentSubmission.result?.agent_response && (
                <div className="border-t pt-4 space-y-4">
                  {/* Summary */}
                  {currentSubmission.result.agent_response.summary && (
                    <div className="space-y-1.5">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Agent Summary
                      </h4>
                      <p className="text-sm leading-relaxed text-foreground bg-muted/20 p-3 rounded border">
                        {currentSubmission.result.agent_response.summary}
                      </p>
                    </div>
                  )}

                  {/* Extracted Structured Data */}
                  {currentSubmission.result.agent_response.structured_data && (
                    <div className="space-y-1.5">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Extracted Parameters
                      </h4>
                      {renderStructuredData(
                        currentSubmission.assigned_agent || '',
                        currentSubmission.result.agent_response.structured_data
                      )}
                    </div>
                  )}

                  {/* Checklist of Action Items */}
                  {currentSubmission.result.agent_response.action_items && currentSubmission.result.agent_response.action_items.length > 0 && (
                    <div className="space-y-2 border bg-card p-4 rounded-lg shadow-sm">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-primary flex items-center gap-1.5">
                        <CheckSquare className="h-4 w-4" /> Recommended Tasks
                      </h4>
                      <div className="space-y-2 mt-2">
                        {currentSubmission.result.agent_response.action_items.map((item: string, index: number) => {
                          const isCompleted = (currentSubmission.result?.agent_response?.completed_action_items || []).includes(index);
                          return (
                            <button
                              key={`${item}-${index}`}
                              type="button"
                              onClick={() => toggleActionItem(currentSubmission.id, index)}
                              className={cn(
                                "flex items-start gap-3 w-full text-left p-2 rounded-md transition-all duration-150 group border border-transparent",
                                isCompleted
                                  ? "bg-green-50/40 text-muted-foreground dark:bg-green-950/10"
                                  : "hover:bg-muted/50 hover:border-border"
                              )}
                            >
                              <span className="flex-shrink-0 mt-0.5">
                                {isCompleted ? (
                                  <CheckSquare className="h-4 w-4 text-green-500 fill-green-50 dark:fill-green-950" />
                                ) : (
                                  <Square className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                                )}
                              </span>
                              <span className={cn(
                                "text-sm",
                                isCompleted && "line-through text-muted-foreground/75"
                              )}>
                                {item}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Error Details */}
              {currentSubmission.status === 'failed' && (
                <div className="border-t pt-4 space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-destructive">
                    Execution Failure
                  </h4>
                  <div className="rounded-lg bg-destructive/5 border border-destructive/10 p-4">
                    <p className="text-sm text-destructive">
                      {currentSubmission.error_message ?? 'An unknown error occurred during workflow execution.'}
                    </p>
                  </div>
                </div>
              )}

              {/* Polling / Loading Info */}
              {isPolling && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground animate-pulse">
                  <Clock className="h-3 w-3" />
                  <span>Polling for workflow updates...</span>
                </div>
              )}

              <div className="text-[10px] text-muted-foreground border-t pt-3 flex justify-between">
                <span>ID: {currentSubmission.id}</span>
                <span>Submitted {formatDateTime(currentSubmission.created_at)}</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
