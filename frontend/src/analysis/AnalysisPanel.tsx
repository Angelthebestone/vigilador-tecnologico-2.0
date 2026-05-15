import { useState, type ReactNode } from 'react';

export type AnalysisSubTab = 'grafo' | 'metricas' | 'recomendaciones';

interface AnalysisPanelProps {
  graph: ReactNode;
  metrics: ReactNode;
  recommendations: ReactNode;
  defaultTab?: AnalysisSubTab;
}

const TABS: Array<{ id: AnalysisSubTab; label: string }> = [
  { id: 'grafo', label: 'Grafo' },
  { id: 'metricas', label: 'Métricas' },
  { id: 'recomendaciones', label: 'Recomendaciones' },
];

export function AnalysisPanel({
  graph,
  metrics,
  recommendations,
  defaultTab = 'grafo',
}: AnalysisPanelProps) {
  const [active, setActive] = useState<AnalysisSubTab>(defaultTab);

  const panes: Record<AnalysisSubTab, ReactNode> = {
    grafo: graph,
    metricas: metrics,
    recomendaciones: recommendations,
  };

  return (
    <div className="analysis">
      <div
        className="analysis__subtabs"
        role="tablist"
        aria-label="Sub-vistas de análisis"
      >
        {TABS.map((tab, i) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active === tab.id}
            className="analysis__subtab"
            onClick={() => setActive(tab.id)}
          >
            {String(i + 1).padStart(2, '0')} · {tab.label}
          </button>
        ))}
      </div>
      <div className="analysis__panes">
        {TABS.map((tab) => (
          <div
            key={tab.id}
            className="analysis__pane"
            role="tabpanel"
            hidden={active !== tab.id}
          >
            {panes[tab.id]}
          </div>
        ))}
      </div>
    </div>
  );
}
