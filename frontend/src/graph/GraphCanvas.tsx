import { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import type { GraphData } from '@/types';
import { GraphNode } from './GraphNode';
import { GraphEdge } from './GraphEdge';
import { buildAdjacency, filterOverlappingLabels } from './graphUtils';

interface SimNode {
  id: string;
  x: number;
  y: number;
  fx?: number | null;
  fy?: number | null;
}

interface GraphCanvasProps {
  data: GraphData;
  selectedNodeId: string | null;
  pathNodeIds?: string[];
  pathEdgeIds?: string[];
  onSelectNode: (id: string | null) => void;
}

export function GraphCanvas({
  data,
  selectedNodeId,
  pathNodeIds = [],
  pathEdgeIds = [],
  onSelectNode,
}: GraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const simRef = useRef<d3.Simulation<SimNode, undefined> | null>(null);
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [transform, setTransform] = useState('translate(0,0) scale(1)');
  const [hovered, setHovered] = useState<string | null>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });

  const adjacency = useMemo(() => buildAdjacency(data.edges), [data.edges]);
  const pathNodeSet = useMemo(() => new Set(pathNodeIds), [pathNodeIds]);
  const pathEdgeSet = useMemo(() => new Set(pathEdgeIds), [pathEdgeIds]);

  // Observa el tamaño del lienzo
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      setSize({ w: width, h: height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Simulación de fuerzas (layout circular force-directed)
  useEffect(() => {
    const nodes: SimNode[] = data.nodes.map((n) => ({
      id: n.id,
      x: size.w / 2 + (Math.random() - 0.5) * 200,
      y: size.h / 2 + (Math.random() - 0.5) * 200,
    }));
    const links = data.edges.map((e) => ({
      source: e.source,
      target: e.target,
    }));

    const sim = d3
      .forceSimulation<SimNode>(nodes)
      .force(
        'link',
        d3
          .forceLink<SimNode, { source: string; target: string }>(links)
          .id((d) => d.id)
          .distance(160)
          .strength(0.3),
      )
      .force('charge', d3.forceManyBody().strength(-650))
      .force('center', d3.forceCenter(size.w / 2, size.h / 2))
      .force('collide', d3.forceCollide(64))
      .force('x', d3.forceX(size.w / 2).strength(0.03))
      .force('y', d3.forceY(size.h / 2).strength(0.03));

    sim.on('tick', () => {
      const next: Record<string, { x: number; y: number }> = {};
      for (const n of nodes) next[n.id] = { x: n.x, y: n.y };
      setPositions(next);
    });

    simRef.current = sim;
    return () => {
      sim.stop();
    };
  }, [data]);

  // Re-center simulation on resize (no re-creation)
  useEffect(() => {
    const sim = simRef.current;
    if (!sim) return;
    sim.force('center', d3.forceCenter(size.w / 2, size.h / 2));
    sim.alpha(0.3).restart();
  }, [size.w, size.h]);

  // Zoom y pan
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => {
        const { x, y, k } = event.transform;
        setTransform(`translate(${x},${y}) scale(${k})`);
      });
    const sel = d3.select(svg);
    sel.call(zoom);
    return () => {
      sel.on('.zoom', null);
    };
  }, []);

  // Arrastre de nodos: recalienta la simulación
  function onNodePointerDown(id: string, e: React.PointerEvent) {
    e.stopPropagation();
    const svg = svgRef.current;
    const sim = simRef.current;
    if (!svg || !sim) return;
    (e.target as Element).setPointerCapture?.(e.pointerId);

    const node = sim.nodes().find((n) => n.id === id);
    if (!node) return;
    sim.alphaTarget(0.3).restart();

    const ctm = (gRef.current as SVGGElement).getScreenCTM();
    function toLocal(clientX: number, clientY: number) {
      if (!ctm) return { x: clientX, y: clientY };
      return {
        x: (clientX - ctm.e) / ctm.a,
        y: (clientY - ctm.f) / ctm.d,
      };
    }

    function move(ev: PointerEvent) {
      const p = toLocal(ev.clientX, ev.clientY);
      node!.fx = p.x;
      node!.fy = p.y;
    }
    function up() {
      sim!.alphaTarget(0);
      node!.fx = null;
      node!.fy = null;
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    }
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  }

  const visibleLabels = useMemo(() => {
    const withPos = data.nodes
      .filter((n) => positions[n.id])
      .map((n) => ({
        id: n.id,
        x: positions[n.id]!.x,
        y: positions[n.id]!.y,
        centrality: n.centrality,
      }));
    return filterOverlappingLabels(withPos, 96);
  }, [data.nodes, positions]);

  const highlightSet = useMemo(() => {
    if (!hovered) return null;
    const set = new Set<string>([hovered]);
    for (const id of adjacency.get(hovered) ?? []) set.add(id);
    return set;
  }, [hovered, adjacency]);

  return (
    <div className="kgraph__stage">
      <svg
        ref={svgRef}
        className="kgraph__svg"
        onClick={() => onSelectNode(null)}
      >
        <g ref={gRef} transform={transform}>
          {data.edges.map((edge) => {
            const s = positions[edge.source];
            const t = positions[edge.target];
            if (!s || !t) return null;
            const dim =
              highlightSet !== null &&
              !(highlightSet.has(edge.source) && highlightSet.has(edge.target));
            return (
              <GraphEdge
                key={edge.id}
                x1={s.x}
                y1={s.y}
                x2={t.x}
                y2={t.y}
                similarity={edge.similarityScore}
                dimmed={dim}
                onPath={pathEdgeSet.has(edge.id)}
              />
            );
          })}
          {data.nodes.map((node) => {
            const p = positions[node.id];
            if (!p) return null;
            const dim =
              highlightSet !== null && !highlightSet.has(node.id);
            return (
              <GraphNode
                key={node.id}
                node={node}
                x={p.x}
                y={p.y}
                selected={
                  selectedNodeId === node.id || pathNodeSet.has(node.id)
                }
                dimmed={dim}
                showLabel={visibleLabels.has(node.id)}
                onSelect={onSelectNode}
                onPointerDown={onNodePointerDown}
                onHover={setHovered}
              />
            );
          })}
        </g>
      </svg>
    </div>
  );
}
