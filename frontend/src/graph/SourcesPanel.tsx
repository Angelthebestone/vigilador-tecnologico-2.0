import type { GraphNode, Source } from '@/types';
import { Icon } from '@/components';
import { getBranchLabel } from './graphUtils';

interface SourcesPanelProps {
  node: GraphNode;
  sources: Source[];
  onClose: () => void;
}

export function SourcesPanel({ node, sources, onClose }: SourcesPanelProps) {
  const linked = sources.filter((s) => node.sourceIds.includes(s.id));

  return (
    <aside className="sources" aria-label="Fuentes del concepto">
      <div className="sources__head">
        <div>
          <div className="sources__node-name">{node.label}</div>
          <div className="sources__node-meta">
            {getBranchLabel(node.branchType)} · confianza{' '}
            {Math.round(node.confidence * 100)}%
          </div>
        </div>
        <button
          type="button"
          className="btn btn--icon"
          onClick={onClose}
          aria-label="Cerrar panel de fuentes"
        >
          <Icon name="close" size={15} />
        </button>
      </div>
      <div className="sources__list">
        {linked.length === 0 ? (
          <p
            style={{
              fontFamily: 'var(--serif-body)',
              fontSize: 13,
              fontStyle: 'italic',
              color: 'var(--ink-faint)',
              padding: '20px 4px',
              textAlign: 'center',
            }}
          >
            Sin fuentes asociadas a este concepto.
          </p>
        ) : (
          linked.map((src) => (
            <article className="source-item" key={src.id}>
              <div className="source-item__title">
                {src.title ?? 'Fuente sin título'}
              </div>
              <a
                className="source-item__link"
                href={src.url}
                target="_blank"
                rel="noreferrer noopener"
              >
                {src.url}
              </a>
              <div className="source-item__foot">
                <span>{src.provider}</span>
                <span>·</span>
                <span>{getBranchLabel(src.branchType)}</span>
              </div>
            </article>
          ))
        )}
      </div>
    </aside>
  );
}
