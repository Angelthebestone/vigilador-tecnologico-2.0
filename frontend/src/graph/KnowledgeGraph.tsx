import { useMemo } from 'react';
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
  const selectedNode = useMemo(
    () => data?.nodes.find((n) => n.id === selectedNodeId) ?? null,
    [data, selectedNodeId],
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
        data={data}
        selectedNodeId={selectedNodeId}
        pathNodeIds={pathNodeIds}
        pathEdgeIds={pathEdgeIds}
        onSelectNode={onSelectNode}
      />
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
