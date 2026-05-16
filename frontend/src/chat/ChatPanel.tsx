import { useEffect, useRef, type ReactNode } from 'react';
import type { ChatMessage } from '@/types';
import { StateBlock } from '@/components';
import { ChatMessageItem } from './ChatMessageItem';
import { InputBar } from './InputBar';

interface ChatPanelProps {
  messages: ChatMessage[];
  inputDisabled?: boolean;
  planApproved?: boolean;
  actionsDisabled?: boolean;
  /** Sesión completada con reporte: el input pasa a modo seguimiento. */
  conversationMode?: boolean;
  /** Render prop: cadena de pensamiento del planner para un mensaje tipo plan. */
  renderThinkingChain?: (message: ChatMessage) => ReactNode;
  onSend: (text: string) => void;
  onClarify?: (messageId: string, answers: Record<string, string>) => void;
  onApprovePlan?: () => void;
  onModifyPlan?: () => void;
}

export function ChatPanel({
  messages,
  inputDisabled = false,
  planApproved = false,
  actionsDisabled = false,
  conversationMode = false,
  renderThinkingChain,
  onSend,
  onClarify,
  onApprovePlan,
  onModifyPlan,
}: ChatPanelProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length]);

  return (
    <div className="chat">
      {messages.length === 0 ? (
        <div className="chat__empty">
          <StateBlock
            kind="empty"
            glyph="CUADERNO SIN ABRIR"
            title="Aún no hay registros en esta sesión"
            hint="Formule una consulta para abrir una nueva lámina de investigación. El sistema responderá con preguntas de precisión antes de trazar el plan."
          />
        </div>
      ) : (
        <div className="chat__log" role="log" aria-live="polite">
          {messages.map((msg, i) => (
            <ChatMessageItem
              key={msg.id}
              message={msg}
              index={i}
              planApproved={planApproved}
              actionsDisabled={actionsDisabled}
              thinkingChain={renderThinkingChain?.(msg)}
              onClarify={(answers) => onClarify?.(msg.id, answers)}
              onApprovePlan={onApprovePlan}
              onModifyPlan={onModifyPlan}
            />
          ))}
          <div ref={endRef} />
        </div>
      )}
      <InputBar
        disabled={inputDisabled}
        conversationMode={conversationMode}
        onSend={onSend}
      />
    </div>
  );
}
