interface GraphEdgeProps {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  similarity: number;
  dimmed: boolean;
  onPath: boolean;
}

export function GraphEdge({
  x1,
  y1,
  x2,
  y2,
  similarity,
  dimmed,
  onPath,
}: GraphEdgeProps) {
  return (
    <line
      className={`gedge ${dimmed ? 'gedge--dim' : ''} ${onPath ? 'gedge--path' : ''}`}
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      strokeWidth={onPath ? 2.5 : 0.6 + similarity * 1.6}
      strokeOpacity={onPath ? 1 : 0.25 + similarity * 0.5}
    />
  );
}
