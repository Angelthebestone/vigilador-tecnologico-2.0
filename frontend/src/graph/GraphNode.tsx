import type { GraphNode as GraphNodeData, NodeType } from '@/types';
import { getNodeColor, mapCentralityToRadius, getFontSize } from './graphUtils';

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

function NodeShape({ nodeType, r, color }: { nodeType: NodeType | undefined; r: number; color: string }) {
  const s = r * 1.15;
  switch (nodeType) {
    case 'CONCEPT': {
      // Rombo
      const d = `M 0 ${-s} L ${s} 0 L 0 ${s} L ${-s} 0 Z`;
      return <path className="gnode__shape" d={d} fill={color} />;
    }
    case 'SOURCE': {
      // Cuadrado redondeado
      const hw = s * 0.85;
      return <rect className="gnode__shape" x={-hw} y={-hw} width={hw * 2} height={hw * 2} rx={4} ry={4} fill={color} />;
    }
    case 'PATENT': {
      // Hexágono
      const pts = Array.from({ length: 6 }, (_, i) => {
        const angle = (Math.PI / 3) * i - Math.PI / 6;
        return `${(r * Math.cos(angle)).toFixed(2)},${(r * Math.sin(angle)).toFixed(2)}`;
      }).join(' ');
      return <polygon className="gnode__shape" points={pts} fill={color} />;
    }
    case 'PERSON': {
      // Círculo con borde punteado
      return (
        <>
          <circle className="gnode__shape" r={r} fill={color} />
          <circle r={r + 3} fill="none" stroke={color} strokeWidth={1.5} strokeDasharray="3 2" />
        </>
      );
    }
    case 'COMPANY': {
      // Rectángulo ancho
      return <rect className="gnode__shape" x={-s} y={-s * 0.65} width={s * 2} height={s * 1.3} rx={3} ry={3} fill={color} />;
    }
    case 'TECHNOLOGY': {
      // Estrella de 6 puntas
      const outer = r;
      const inner = r * 0.45;
      const pts = Array.from({ length: 12 }, (_, i) => {
        const angle = (Math.PI / 6) * i - Math.PI / 2;
        const rad = i % 2 === 0 ? outer : inner;
        return `${(rad * Math.cos(angle)).toFixed(2)},${(rad * Math.sin(angle)).toFixed(2)}`;
      }).join(' ');
      return <polygon className="gnode__shape" points={pts} fill={color} />;
    }
    default:
      // FINDING y fallback → círculo
      return <circle className="gnode__circle" r={r} fill={color} />;
  }
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
  const color = getNodeColor(node.nodeType, node.branchType);

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
      aria-label={`${node.nodeType ?? 'Nodo'}: ${node.label}`}
    >
      <NodeShape nodeType={node.nodeType} r={r} color={color} />
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
