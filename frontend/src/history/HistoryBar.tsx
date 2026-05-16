import { useState, type MouseEvent } from 'react';
import type { SessionSummary, SessionStatus } from '@/types';
import { Button, Icon } from '@/components';
import { ConfirmDialog } from '@/components/ConfirmDialog';

interface HistoryBarProps {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  collapsed: boolean;
  loading?: boolean;
  error?: string | null;
  onToggle: () => void;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete?: (id: string) => void;
}

function statusDot(status: SessionStatus): string {
  if (status === 'COMPLETED') return 'completed';
  if (status === 'FAILED') return 'failed';
  if (status === 'EXECUTING' || status === 'PLANNING' || status === 'CLARIFYING')
    return 'running';
  return 'idle';
}

function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('es', { day: '2-digit', month: 'short' });
}

export function HistoryBar({
  sessions,
  activeSessionId,
  collapsed,
  loading = false,
  error = null,
  onToggle,
  onSelect,
  onNew,
  onDelete,
}: HistoryBarProps) {
  const [deleteTarget, setDeleteTarget] = useState<SessionSummary | null>(null);

  function handleDeleteClick(e: MouseEvent, session: SessionSummary) {
    e.stopPropagation();
    setDeleteTarget(session);
  }

  function confirmDelete() {
    if (deleteTarget && onDelete) {
      onDelete(deleteTarget.id);
    }
    setDeleteTarget(null);
  }

  return (
    <nav
      className={`history ${collapsed ? 'history--collapsed' : ''}`}
      aria-label="Índice de investigaciones"
    >
      <div className="history__head">
        <span className="history__title">Índice de láminas</span>
        <button
          type="button"
          className="btn btn--icon"
          onClick={onToggle}
          aria-label={collapsed ? 'Expandir índice' : 'Colapsar índice'}
        >
          <Icon name={collapsed ? 'arrow-right' : 'arrow-left'} size={14} />
        </button>
      </div>

      <Button
        variant="primary"
        className="history__new"
        onClick={onNew}
        aria-label="Nueva investigación"
      >
        <Icon name="plus" size={14} />
        <span className="history__new-label">Nueva investigación</span>
      </Button>

      <div className="history__list">
        {loading && (
          <p
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 10,
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              color: 'var(--ink-faint)',
              padding: '16px 14px',
            }}
          >
            Cargando índice…
          </p>
        )}
        {error && !loading && (
          <p
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 11,
              color: 'var(--st-fail)',
              padding: '16px 14px',
            }}
          >
            {error}
          </p>
        )}
        {!loading && !error && sessions.length === 0 && (
          <p
            style={{
              fontFamily: 'var(--serif-body)',
              fontSize: 13,
              fontStyle: 'italic',
              color: 'var(--ink-faint)',
              padding: '20px 14px',
            }}
          >
            Sin investigaciones registradas todavía.
          </p>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className="history__item-row"
          >
            <button
              type="button"
              className="history__item"
              aria-current={s.id === activeSessionId}
              onClick={() => onSelect(s.id)}
            >
              <div className="history__item-q">{s.query || 'Sin título'}</div>
              <div className="history__item-meta">
                <span
                  className="history__status-dot"
                  data-status={statusDot(s.status)}
                  aria-hidden="true"
                />
                <span>{s.status}</span>
                <span>·</span>
                <span>{shortDate(s.date)}</span>
              </div>
            </button>
            {onDelete && (
              <button
                type="button"
                className="history__delete-btn"
                onClick={(e) => handleDeleteClick(e, s)}
                aria-label={`Eliminar investigación: ${s.query || 'Sin título'}`}
              >
                <Icon name="trash" size={13} />
              </button>
            )}
          </div>
        ))}
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Eliminar investigación"
        message={
          deleteTarget
            ? `¿Eliminar «${deleteTarget.query || 'Sin título'}» y todos sus datos asociados? Esta acción es irreversible.`
            : ''
        }
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        variant="danger"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </nav>
  );
}
