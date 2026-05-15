import type { BranchType, GraphEdge } from '@/types';

/**
 * Construye un mapa de adyacencia no dirigido a partir de las aristas.
 * Útil para resaltar vecinos directos al hacer hover sobre un nodo.
 */
export function buildAdjacency(
  edges: GraphEdge[],
): Map<string, Set<string>> {
  const adj = new Map<string, Set<string>>();
  for (const e of edges) {
    if (!adj.has(e.source)) adj.set(e.source, new Set());
    if (!adj.has(e.target)) adj.set(e.target, new Set());
    adj.get(e.source)!.add(e.target);
    adj.get(e.target)!.add(e.source);
  }
  return adj;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * Convierte un score de centralidad (0-1) a radio de nodo (4-30px).
 * Mapeo lineal: score 0 → 4px, score 1 → 30px
 */
export function mapCentralityToRadius(
  score: number,
  minRadius = 4,
  maxRadius = 30,
): number {
  const clamped = clamp(score, 0, 1);
  return minRadius + clamped * (maxRadius - minRadius);
}

const BRANCH_COLORS: Record<BranchType, string> = {
  AVANCES: '#3B82F6',
  COMERCIAL: '#10B981',
  RIESGO: '#EF4444',
  PI_NORMATIVA: '#F59E0B',
  COMPETITIVO: '#8B5CF6',
  OPORTUNIDADES: '#EC4899',
};

/**
 * Devuelve color HEX para cada rama.
 * Mapeo fijo:
 * AVANCES → #3B82F6 (azul)
 * COMERCIAL → #10B981 (verde)
 * RIESGO → #EF4444 (rojo)
 * PI_NORMATIVA → #F59E0B (amarillo)
 * COMPETITIVO → #8B5CF6 (púrpura)
 * OPORTUNIDADES → #EC4899 (rosa)
 * default → #6B7280 (gris)
 */
export function getBranchColor(branchType: BranchType): string {
  return BRANCH_COLORS[branchType] ?? '#6B7280';
}

const BRANCH_LABELS: Record<BranchType, string> = {
  AVANCES: 'Avances',
  COMERCIAL: 'Comercial',
  RIESGO: 'Riesgo',
  PI_NORMATIVA: 'PI/Normativa',
  COMPETITIVO: 'Competitivo',
  OPORTUNIDADES: 'Oportunidades',
};

/**
 * Devuelve el nombre legible de cada rama.
 * AVANCES → "Avances", COMERCIAL → "Comercial", etc.
 */
export function getBranchLabel(branchType: BranchType): string {
  return BRANCH_LABELS[branchType];
}

/**
 * Escala el tamaño de fuente según el radio del nodo.
 * fuente = max(10, min(16, radio * 0.6))
 */
export function getFontSize(radius: number): number {
  return clamp(radius * 0.6, 10, 16);
}

/**
 * Función para filtrar etiquetas solapadas.
 * Si dos nodos están a menos de minDistance píxeles de distancia,
 * oculta la etiqueta del nodo con menor centrality.
 * Devuelve un Set con los nodeId que deben mostrar label.
 */
export function filterOverlappingLabels(
  nodes: Array<{ id: string; x: number; y: number; centrality: number }>,
  minDistance = 60,
): Set<string> {
  if (nodes.length === 0) return new Set();

  const visible = new Set<string>(nodes.map((n) => n.id));
  const sorted = [...nodes].sort((a, b) => b.centrality - a.centrality);

  for (let i = 0; i < sorted.length; i++) {
    const a = sorted[i];
    if (!a) continue;
    for (let j = i + 1; j < sorted.length; j++) {
      const b = sorted[j];
      if (!b) continue;
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < minDistance) {
        visible.delete(b.id);
      }
    }
  }

  return visible;
}
