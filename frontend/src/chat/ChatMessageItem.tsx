import type { ReactNode } from 'react';
import type { ChatMessage, ResearchPlan, FinalReport } from '@/types';
import { ClarificationInput, type ClarificationQuestion } from './ClarificationInput';
import { PlanBlock } from './PlanBlock';
import { ReportSummary } from './ReportSummary';

interface ChatMessageItemProps {
  message: ChatMessage;
  index: number;
  /** Slot de cadena de pensamiento del planner para mensajes tipo "plan". */
  thinkingChain?: ReactNode;
  planApproved?: boolean;
  actionsDisabled?: boolean;
  onClarify?: (answers: Record<string, string>) => void;
  onApprovePlan?: () => void;
  onModifyPlan?: () => void;
}

function folio(index: number): string {
  return `№ ${String(index + 1).padStart(3, '0')}`;
}

function roleLabel(message: ChatMessage): string {
  if (message.type === 'user') return 'Consulta';
  if (message.type === 'event') return 'Registro';
  if (message.type === 'plan') return 'Plan';
  if (message.type === 'report') return 'Síntesis';
  if (message.type === 'clarification') return 'Aclaración';
  return 'Bitácora';
}

export function ChatMessageItem({
  message,
  index,
  thinkingChain,
  planApproved = false,
  actionsDisabled = false,
  onClarify,
  onApprovePlan,
  onModifyPlan,
}: ChatMessageItemProps) {
  const meta = message.metadata ?? {};

  let content: ReactNode;

  if (message.type === 'clarification') {
    const questions = (meta.questions as ClarificationQuestion[]) ?? [];
    content = (
      <ClarificationInput
        questions={questions}
        answered={Boolean(meta.answered)}
        onSubmit={(answers) => onClarify?.(answers)}
      />
    );
  } else if (message.type === 'plan' && meta.plan) {
    content = (
      <PlanBlock
        plan={meta.plan as ResearchPlan}
        thinkingChain={thinkingChain}
        approved={planApproved}
        disabled={actionsDisabled}
        onApprove={() => onApprovePlan?.()}
        onModify={() => onModifyPlan?.()}
      />
    );
  } else if (message.type === 'report' && meta.report) {
    content = <ReportSummary report={meta.report as FinalReport} />;
  } else {
    content = <p className="msg__text">{message.content}</p>;
  }

  return (
    <div className={`msg msg--${message.type}`}>
      <div className="msg__gutter">{folio(index)}</div>
      <div className="msg__body">
        <div className="msg__role">{roleLabel(message)}</div>
        {content}
      </div>
    </div>
  );
}
