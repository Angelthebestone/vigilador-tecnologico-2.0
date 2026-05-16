import { useState } from 'react';
import { useStore } from '@/state/useStore';
import { useHistoryStore } from '@/state/historyStore';
import { useChatStore } from '@/state/chatStore';
import { useAgentsStore } from '@/state/agentsStore';
import { ChatView } from '@/chat';
import { AnalysisView } from '@/analysis';
import { HistoryBar, SessionTimeline } from '@/history';
import { TabNav, ConnectionStatus } from '@/components';

type MainTab = 'chat' | 'analisis' | 'memoria';

const TABS = [
  { id: 'chat' as const, label: 'Chat' },
  { id: 'analisis' as const, label: 'Análisis' },
  { id: 'memoria' as const, label: 'Memoria' },
];

const FOLIO: Record<MainTab, string> = {
  chat: 'I',
  analisis: 'II',
  memoria: 'III',
};

export function MainLayout() {
  const [tab, setTab] = useState<MainTab>('chat');
  const [historyCollapsed, setHistoryCollapsed] = useState(false);

  const sseStatus = useStore((s) => s.sseStatus);
  const clearSession = useStore((s) => s.clearSession);

  const sessions = useHistoryStore((s) => s.sessions);
  const activeSessionId = useHistoryStore((s) => s.activeSessionId);
  const selectSession = useHistoryStore((s) => s.selectSession);
  const newSession = useHistoryStore((s) => s.newSession);

  const removeSession = useHistoryStore((s) => s.removeSession);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const resetAgents = useAgentsStore((s) => s.resetAgents);

  function handleNew() {
    newSession();
    clearSession();
    clearMessages();
    resetAgents();
  }

  function handleSelect(id: string) {
    selectSession(id);
  }

  async function handleDelete(id: string) {
    try {
      await removeSession(id);
      if (activeSessionId === id) {
        clearSession();
        clearMessages();
        resetAgents();
      }
    } catch {
      // error handled by store
    }
  }

  const historyBar = (
    <HistoryBar
      sessions={sessions}
      activeSessionId={activeSessionId}
      collapsed={historyCollapsed}
      onToggle={() => setHistoryCollapsed((v) => !v)}
      onSelect={handleSelect}
      onNew={handleNew}
      onDelete={handleDelete}
    />
  );

  return (
    <div className="atlas-shell">
      <header className="atlas-masthead">
        <div className="atlas-mark">
          <span className="atlas-mark__kicker">Observatorio tecnológico</span>
          <span className="atlas-mark__title">
            Vigilador <em>Atlas</em>
          </span>
        </div>
        <div className="atlas-masthead__nav">
          <TabNav
            tabs={TABS}
            active={tab}
            onChange={(id) => setTab(id as MainTab)}
          />
          <div className="atlas-masthead__meta">
            <span className="atlas-folio">Lám. {FOLIO[tab]}</span>
            <ConnectionStatus status={sseStatus} />
          </div>
        </div>
      </header>

      {tab === 'chat' && <ChatView historyBar={historyBar} />}
      {tab === 'analisis' && <AnalysisView historyBar={historyBar} />}
      {tab === 'memoria' && (
        <div className="atlas-body">
          {historyBar}
          <div className="atlas-plate">
            <SessionTimeline />
          </div>
        </div>
      )}
    </div>
  );
}
