import { useMemo, useState } from 'react';
import type { GraphData, Source } from '@/types';
import { StateBlock } from '@/components';
import { GraphCanvas } from './GraphCanvas';
import { GraphLegend } from './GraphLegend';
import { SourcesPanel } from './SourcesPanel';

interface KnowledgeGraphProps {
  data: GraphData | null;
  loading: boolean;
  error: string | null;
  selectedNodeId: string | null;
  sources: Source[];
  pathNodeIds?: string[];
  pathEdgeIds?: string[];
  onSelectNode: (id: string | null) => void;
}

export function KnowledgeGraph({
  data,
  loading,
  error,
  selectedNodeId,
  sources,
  pathNodeIds,
  pathEdgeIds,
  onSelectNode,
}: KnowledgeGraphProps) {
  const [showSources, setShowSources] = useState(false);

  const selectedNode = useMemo(
    () => data?.nodes.find((n) => n.id === selectedNodeId) ?? null,
    [data, selectedNodeId],
  );

  // Los nodos SOURCE (fuentes/URLs) recargan el grafo: la fuente de cada nodo
  // ya se ve en el panel lateral al seleccionarlo. Ocultos por defecto; el
  // toggle los revela para inspeccionar contenidos que comparten fuente.
  const visibleData = useMemo<GraphData | null>(() => {
    if (!data || showSources) return data;
    const sourceIds = new Set(
      data.nodes.filter((n) => n.nodeType === 'SOURCE').map((n) => n.id),
    );
    if (sourceIds.size === 0) return data;
    return {
      ...data,
      nodes: data.nodes.filter((n) => !sourceIds.has(n.id)),
      edges: data.edges.filter(
        (e) => !sourceIds.has(e.source) && !sourceIds.has(e.target),
      ),
    };
  }, [data, showSources]);

  const sourceCount = useMemo(
    () => data?.nodes.filter((n) => n.nodeType === 'SOURCE').length ?? 0,
    [data],
  );

  if (loading) {
    return (
      <StateBlock kind="loading" title="Trazando la carta de constelaciones" />
    );
  }
  if (error) {
    return (
      <StateBlock
        kind="error"
        title="No se pudo construir el grafo"
        hint={error}
      />
    );
  }
  if (!data || data.nodes.length === 0) {
    return (
      <StateBlock
        kind="empty"
        glyph="CARTA EN BLANCO"
        title="No se encontraron hallazgos para esta investigación"
        hint="El grafo de conocimiento se traza al consolidar los hallazgos de las seis ramas."
      />
    );
  }

  return (
    <div className="kgraph">
      <GraphCanvas
        data={visibleData ?? data}
        selectedNodeId={selectedNodeId}
        pathNodeIds={pathNodeIds}
        pathEdgeIds={pathEdgeIds}
        onSelectNode={onSelectNode}
      />
      {sourceCount > 0 && (
        <button
          type="button"
          className="kgraph__src-toggle"
          aria-pressed={showSources}
          onClick={() => setShowSources((v) => !v)}
        >
          {showSources
            ? `Ocultar fuentes (${sourceCount})`
            : `Mostrar fuentes (${sourceCount})`}
        </button>
      )}
      <GraphLegend />
      {selectedNode && (
        <SourcesPanel
          node={selectedNode}
          sources={sources}
          onClose={() => onSelectNode(null)}
        />
      )}
    </div>
  );
}
