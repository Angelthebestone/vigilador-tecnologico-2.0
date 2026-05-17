import type { NodeType } from '@/types';
import { NODE_TYPE_COLORS, NODE_TYPE_LABELS } from './graphUtils';

const NODE_TYPES: NodeType[] = [
  'TECHNOLOGY',
  'FINDING',
  'CONCEPT',
  'SOURCE',
  'PATENT',
  'PERSON',
  'COMPANY',
];

// Forma SVG miniatura para la leyenda
function LegendShape({ nodeType, color }: { nodeType: NodeType; color: string }) {
  const r = 6;
  switch (nodeType) {
    case 'CONCEPT':
      return <polygon points={`0,${-r} ${r},0 0,${r} ${-r},0`} fill={color} />;
    case 'SOURCE':
      return <rect x={-r} y={-r} width={r * 2} height={r * 2} rx={2} fill={color} />;
    case 'PATENT': {
      const pts = Array.from({ length: 6 }, (_, i) => {
        const a = (Math.PI / 3) * i - Math.PI / 6;
        return `${(r * Math.cos(a)).toFixed(1)},${(r * Math.sin(a)).toFixed(1)}`;
      }).join(' ');
      return <polygon points={pts} fill={color} />;
    }
    case 'PERSON':
      return (
        <>
          <circle r={r} fill={color} />
          <circle r={r + 2} fill="none" stroke={color} strokeWidth={1} strokeDasharray="2 1.5" />
        </>
      );
    case 'COMPANY':
      return <rect x={-r * 1.2} y={-r * 0.75} width={r * 2.4} height={r * 1.5} rx={2} fill={color} />;
    case 'TECHNOLOGY': {
      const outer = r; const inner = r * 0.45;
      const pts = Array.from({ length: 12 }, (_, i) => {
        const a = (Math.PI / 6) * i - Math.PI / 2;
        const rad = i % 2 === 0 ? outer : inner;
        return `${(rad * Math.cos(a)).toFixed(1)},${(rad * Math.sin(a)).toFixed(1)}`;
      }).join(' ');
      return <polygon points={pts} fill={color} />;
    }
    default:
      return <circle r={r} fill={color} />;
  }
}

export function GraphLegend() {
  return (
    <figure className="glegend">
      <figcaption className="glegend__head">Cartela · tipos de nodo</figcaption>
      <div className="glegend__body">
        {NODE_TYPES.map((nt) => (
          <div className="glegend__row" key={nt}>
            <svg width={18} height={18} viewBox="-9 -9 18 18" aria-hidden="true" style={{ flexShrink: 0 }}>
              <LegendShape nodeType={nt} color={NODE_TYPE_COLORS[nt]} />
            </svg>
            {NODE_TYPE_LABELS[nt]}
          </div>
        ))}
      </div>
      <div className="glegend__scale">
        <span className="glegend__dot" style={{ width: 7, height: 7 }} aria-hidden="true" />
        <span className="glegend__dot" style={{ width: 13, height: 13 }} aria-hidden="true" />
        <span className="glegend__dot" style={{ width: 19, height: 19 }} aria-hidden="true" />
        <span style={{ marginLeft: 4 }}>menor → mayor centralidad</span>
      </div>
    </figure>
  );
}
