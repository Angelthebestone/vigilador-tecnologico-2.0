import { useState } from 'react';
import type { GraphNode, Source } from '@/types';
import { Icon, Modal, Button } from '@/components';
import { adjustSourceScore } from '@/api';
import { getBranchLabel } from './graphUtils';

interface SourcesPanelProps {
  node: GraphNode;
  sources: Source[];
  onClose: () => void;
}

interface ScoreState {
  source: Source;
  delta: number;
  reason: string;
}

export function SourcesPanel({ node, sources, onClose }: SourcesPanelProps) {
  const linked = sources.filter((s) => node.sourceIds.includes(s.id));

  const [scoreEdit, setScoreEdit] = useState<ScoreState | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<Record<string, string>>({});

  async function submitScore() {
    if (!scoreEdit || !scoreEdit.reason.trim() || scoreEdit.delta === 0) return;
    setBusy(true);
    try {
      const res = await adjustSourceScore(
        scoreEdit.source.id,
        scoreEdit.delta,
        scoreEdit.reason.trim(),
      );
      setFeedback((prev) => ({
        ...prev,
        [scoreEdit.source.id]: `Confianza ajustada → ${res.newScore}`,
      }));
      setScoreEdit(null);
    } catch (err) {
      setFeedback((prev) => ({
        ...prev,
        [scoreEdit.source.id]: `Error: ${
          err instanceof Error ? err.message : 'no se pudo ajustar'
        }`,
      }));
    } finally {
      setBusy(false);
    }
  }

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
                <button
                  type="button"
                  className="source-item__score-btn"
                  onClick={() =>
                    setScoreEdit({ source: src, delta: 0, reason: '' })
                  }
                  aria-label={`Ajustar confianza de ${src.title ?? src.url}`}
                >
                  <Icon name="gauge" size={13} />
                  Ajustar confianza
                </button>
              </div>
              {feedback[src.id] && (
                <div className="source-item__feedback">{feedback[src.id]}</div>
              )}
            </article>
          ))
        )}
      </div>

      <Modal
        open={scoreEdit !== null}
        title="Ajustar confianza de fuente"
        onClose={() => !busy && setScoreEdit(null)}
      >
        {scoreEdit && (
          <div className="score-form">
            <p className="score-form__source">{scoreEdit.source.url}</p>

            <label className="score-form__label" htmlFor="score-delta">
              Variación de confianza
              <span className="score-form__delta-val">
                {scoreEdit.delta > 0 ? `+${scoreEdit.delta}` : scoreEdit.delta}
              </span>
            </label>
            <input
              id="score-delta"
              type="range"
              min={-50}
              max={50}
              step={5}
              value={scoreEdit.delta}
              disabled={busy}
              className="score-form__range"
              onChange={(e) =>
                setScoreEdit((prev) =>
                  prev ? { ...prev, delta: Number(e.target.value) } : prev,
                )
              }
            />

            <label className="score-form__label" htmlFor="score-reason">
              Justificación
            </label>
            <textarea
              id="score-reason"
              className="field__control score-form__reason"
              rows={3}
              placeholder="Motivo del ajuste (obligatorio)…"
              value={scoreEdit.reason}
              disabled={busy}
              onChange={(e) =>
                setScoreEdit((prev) =>
                  prev ? { ...prev, reason: e.target.value } : prev,
                )
              }
            />

            <div className="score-form__foot">
              <Button
                variant="ghost"
                size="sm"
                disabled={busy}
                onClick={() => setScoreEdit(null)}
              >
                Cancelar
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={
                  busy ||
                  scoreEdit.delta === 0 ||
                  scoreEdit.reason.trim() === ''
                }
                onClick={submitScore}
              >
                {busy ? 'Aplicando…' : 'Aplicar ajuste'}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </aside>
  );
}
