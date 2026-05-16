import { useMemo, useState, useCallback } from 'react';
import type { BranchAgent, BranchType, ChatMessage } from '@/types';
import { useChatStore } from '@/state/chatStore';
import { useAgentsStore } from '@/state/agentsStore';
import { useStore } from '@/state/useStore';
import { startResearch, clarifySession, approvePlan, askFollowUp } from '@/api';
import { AgentSidebar, PlanningChain } from '@/agents';
import { ChatPanel } from './ChatPanel';
import { useSSE } from './useSSE';

const BRANCH_ORDER: BranchType[] = [
  'AVANCES',
  'COMERCIAL',
  'RIESGO',
  'PI_NORMATIVA',
  'COMPETITIVO',
  'OPORTUNIDADES',
];

interface ChatViewProps {
  historyBar: React.ReactNode;
}

export function ChatView({ historyBar }: ChatViewProps) {
  const messages = useChatStore((s) => s.messages);
  const addMessage = useChatStore((s) => s.addMessage);
  const addClarification = useChatStore((s) => s.addClarification);

  const agentsMap = useAgentsStore((s) => s.agents);
  const selectedAgentIndex = useAgentsStore((s) => s.selectedAgentIndex);
  const setSelectedAgent = useAgentsStore((s) => s.setSelectedAgent);
  const initializeAgents = useAgentsStore((s) => s.initializeAgents);

  const sessionId = useStore((s) => s.sessionId);
  const sessionStatus = useStore((s) => s.sessionStatus);
  const plan = useStore((s) => s.plan);
  const setSession = useStore((s) => s.setSession);
  const setSessionStatus = useStore((s) => s.setSessionStatus);
  const setPlan = useStore((s) => s.setPlan);

  const report = useStore((s) => s.report);

  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [planApproved, setPlanApproved] = useState(false);
  const [followUpBusy, setFollowUpBusy] = useState(false);

  const executing = sessionStatus === 'EXECUTING';
  const conversationMode = sessionStatus === 'COMPLETED' && Boolean(report);
  useSSE({ sessionId, enabled: executing });

  const orderedAgents = useMemo<BranchAgent[]>(
    () =>
      BRANCH_ORDER.map((bt) => agentsMap[bt]).filter(
        (a): a is BranchAgent => Boolean(a),
      ),
    [agentsMap],
  );

  const handleSend = useCallback(
    async (text: string) => {
      addMessage({ type: 'user', role: 'user', content: text });

      // Modo conversación continua: la sesión ya tiene reporte, así que
      // las preguntas se responden desde el grafo existente sin lanzar
      // una nueva investigación.
      if (conversationMode && sessionId) {
        setFollowUpBusy(true);
        try {
          const res = await askFollowUp(sessionId, text);
          if (res.requiresPermission) {
            addMessage({
              type: 'event',
              role: 'assistant',
              content:
                res.prompt ??
                'Esta pregunta requiere una búsqueda nueva. ¿Desea lanzarla?',
              metadata: { requiresPermission: true },
            });
          } else {
            addMessage({
              type: 'system',
              role: 'assistant',
              content:
                res.answer ??
                (typeof res === 'string' ? res : JSON.stringify(res)),
              metadata: res.sources ? { sources: res.sources } : undefined,
            });
          }
        } catch (err) {
          addMessage({
            type: 'event',
            role: 'assistant',
            content: `No se pudo responder la consulta: ${
              err instanceof Error ? err.message : 'error'
            }`,
          });
        } finally {
          setFollowUpBusy(false);
        }
        return;
      }

      if (sessionId) return; // sesión en curso: solo se registra
      try {
        const res = await startResearch(text);
        setSession(res.sessionId, text);
        if (res.questions.length > 0) {
          addClarification(res.questions);
          setSessionStatus('CLARIFYING');
        }
      } catch (err) {
        addMessage({
          type: 'event',
          role: 'assistant',
          content: `No se pudo iniciar la investigación: ${
            err instanceof Error ? err.message : 'error'
          }`,
        });
      }
    },
    [
      addMessage,
      addClarification,
      sessionId,
      conversationMode,
      setSession,
      setSessionStatus,
    ],
  );

  const handleClarify = useCallback(
    async (messageId: string, answers: Record<string, string>) => {
      if (!sessionId) return;
      try {
        const res = await clarifySession(sessionId, answers);
        useChatStore.setState((state) => ({
          messages: state.messages.map((m: ChatMessage) =>
            m.id === messageId
              ? { ...m, metadata: { ...m.metadata, answered: true } }
              : m,
          ),
        }));
        setPlan(res.plan);
        setSessionStatus('PLANNING');
        addMessage({
          type: 'plan',
          role: 'assistant',
          content: 'Plan de investigación generado.',
          metadata: { plan: res.plan },
        });
      } catch (err) {
        addMessage({
          type: 'event',
          role: 'assistant',
          content: `Error al precisar el alcance: ${
            err instanceof Error ? err.message : 'error'
          }`,
        });
      }
    },
    [sessionId, setPlan, setSessionStatus, addMessage],
  );

  const handleApprovePlan = useCallback(async () => {
    if (!sessionId) return;
    try {
      await approvePlan(sessionId);
      setPlanApproved(true);
      setSessionStatus('EXECUTING');
      initializeAgents(BRANCH_ORDER);
      addMessage({
        type: 'event',
        role: 'assistant',
        content: 'Plan aprobado. Despachando las seis ramas de investigación.',
      });
    } catch (err) {
      addMessage({
        type: 'event',
        role: 'assistant',
        content: `No se pudo aprobar el plan: ${
          err instanceof Error ? err.message : 'error'
        }`,
      });
    }
  }, [sessionId, setSessionStatus, initializeAgents, addMessage]);

  const handleModifyPlan = useCallback(() => {
    addMessage({
      type: 'event',
      role: 'assistant',
      content:
        'Indique los ajustes deseados al plan en el cuadro de consulta.',
    });
  }, [addMessage]);

  const renderThinkingChain = useCallback(
    (msg: ChatMessage) => {
      if (msg.type !== 'plan' || !plan) return null;
      const steps =
        (msg.metadata?.thinkingSteps as never[] | undefined) ?? [];
      return (
        <PlanningChain
          steps={steps}
          branchCount={plan.branches.length}
          ready={!planApproved}
        />
      );
    },
    [plan, planApproved],
  );

  return (
    <div className="atlas-body">
      {historyBar}
      <div className="atlas-plate">
        <ChatPanel
          messages={messages}
          inputDisabled={followUpBusy}
          planApproved={planApproved}
          actionsDisabled={executing}
          conversationMode={conversationMode}
          renderThinkingChain={renderThinkingChain}
          onSend={handleSend}
          onClarify={handleClarify}
          onApprovePlan={handleApprovePlan}
          onModifyPlan={handleModifyPlan}
        />
      </div>
      {sidebarVisible ? (
        <AgentSidebar
          agents={orderedAgents}
          selectedIndex={selectedAgentIndex}
          onSelect={setSelectedAgent}
          onClose={() => setSidebarVisible(false)}
        />
      ) : (
        <button
          type="button"
          className="atlas-spine"
          onClick={() => setSidebarVisible(true)}
          aria-label="Mostrar observatorio de agentes"
        >
          Observatorio de agentes
        </button>
      )}
    </div>
  );
}
