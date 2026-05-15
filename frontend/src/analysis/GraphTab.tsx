import { useEffect, useState } from 'react';
import type { GraphData, Source } from '@/types';
import { getGraph, getSources } from '@/api';
import { KnowledgeGraph } from '@/graph';

interface GraphTabProps {
  sessionId: string | null;
}

/** Se remonta vía `key={sessionId}`, por eso el estado inicial es por sesión. */
export function GraphTab({ sessionId }: GraphTabProps) {
  const [data, setData] = useState<GraphData | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(sessionId));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let active = true;

    Promise.all([
      getGraph(sessionId),
      getSources(sessionId).catch(() => ({ items: [] as Source[] })),
    ])
      .then(([graph, src]) => {
        if (!active) return;
        setData(graph);
        setSources(src.items);
      })
      .catch((err: unknown) => {
        if (active)
          setError(err instanceof Error ? err.message : 'Error desconocido');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [sessionId]);

  return (
    <KnowledgeGraph
      data={data}
      loading={loading}
      error={error}
      selectedNodeId={selectedNodeId}
      sources={sources}
      onSelectNode={setSelectedNodeId}
    />
  );
}
