import { create } from 'zustand';
import { InboxSubmission } from '@/types';

interface InboxState {
  submissions: InboxSubmission[];
  currentSubmission: InboxSubmission | null;
  isPolling: boolean;
}

interface InboxActions {
  addSubmission: (s: InboxSubmission) => void;
  updateSubmission: (s: InboxSubmission) => void;
  setCurrentSubmission: (s: InboxSubmission | null) => void;
  setPolling: (v: boolean) => void;
  toggleActionItem: (submissionId: string, itemIndex: number) => void;
}

export const useInboxStore = create<InboxState & InboxActions>((set) => ({
  submissions: [],
  currentSubmission: null,
  isPolling: false,

  addSubmission: (s) =>
    set((state) => ({ submissions: [s, ...state.submissions].slice(0, 20) })),
  updateSubmission: (s) =>
    set((state) => ({
      submissions: state.submissions.map((sub) => (sub.id === s.id ? s : sub)),
      currentSubmission:
        state.currentSubmission?.id === s.id ? s : state.currentSubmission,
    })),
  setCurrentSubmission: (s) => set({ currentSubmission: s }),
  setPolling: (v) => set({ isPolling: v }),

  toggleActionItem: (submissionId, itemIndex) =>
    set((state) => {
      const updateSub = (sub: InboxSubmission): InboxSubmission => {
        if (sub.id !== submissionId || !sub.result) return sub;
        const agentResponse = sub.result.agent_response;
        if (!agentResponse) return sub;
        
        const currentCompleted = agentResponse.completed_action_items || [];
        const completed = currentCompleted.includes(itemIndex)
          ? currentCompleted.filter((i: number) => i !== itemIndex)
          : [...currentCompleted, itemIndex];
          
        return {
          ...sub,
          result: {
            ...sub.result,
            agent_response: {
              ...agentResponse,
              completed_action_items: completed,
            },
          },
        };
      };

      return {
        submissions: state.submissions.map(updateSub),
        currentSubmission: state.currentSubmission ? updateSub(state.currentSubmission) : null,
      };
    }),
}));

