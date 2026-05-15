import type { GraphNode as GraphNodeData } from '@/types';
import { getBranchColor, mapCentralityToRadius, getFontSize } from './graphUtils';

interface GraphNodeProps {
  node: GraphNodeData;
  x: number;
  y: number;
  selected: boolean;
  dimmed: boolean;
  showLabel: boolean;
  onSelect: (id: string) => void;
  onPointerDown: (id: string, e: React.PointerEvent) => void;
  onHover: (id: string | null) => void;
}

export function GraphNode({
  node,
  x,
  y,
  selected,
  dimmed,
  showLabel,
  onSelect,
  onPointerDown,
  onHover,
}: GraphNodeProps) {
  const r = mapCentralityToRadius(node.centrality);
  const fontSize = getFontSize(r);

  return (
    <g
      className={`gnode ${selected ? 'gnode--selected' : ''} ${dimmed ? 'gnode--dim' : ''}`}
      transform={`translate(${x},${y})`}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(node.id);
      }}
      onPointerDown={(e) => onPointerDown(node.id, e)}
      onPointerEnter={() => onHover(node.id)}
      onPointerLeave={() => onHover(null)}
      role="button"
      aria-label={`Concepto ${node.label}`}
    >
      <circle
        className="gnode__circle"
        r={r}
        fill={getBranchColor(node.branchType)}
      />
      {showLabel && (
        <text
          className="gnode__label"
          textAnchor="middle"
          dy={r + fontSize + 3}
          fontSize={fontSize}
        >
          {node.label}
        </text>
      )}
    </g>
  );
}
