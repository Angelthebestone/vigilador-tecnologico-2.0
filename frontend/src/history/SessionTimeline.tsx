import { useEffect, useState } from 'react';
import type { SessionTimelineEntry } from '@/types';
import { getSessionTimeline } from '@/api';
import { StateBlock, Icon } from '@/components';

function formatStamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('es', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function SessionTimeline() {
  const [entries, setEntries] = useState<SessionTimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getSessionTimeline()
      .then((res) => {
        if (active) setEntries(res.sessions ?? []);
      })
      .catch((err: unknown) => {
        if (active)
          setError(err instanceof Error ? err.message : 'Error desconocido');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="timeline">
        <StateBlock kind="loading" title="Recuperando memoria entre sesiones…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="timeline">
        <StateBlock
          kind="error"
          title="No se pudo cargar la línea de tiempo"
          hint={error}
        />
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="timeline">
        <StateBlock
          kind="empty"
          glyph="MEMORIA SIN REGISTROS"
          title="Aún no hay sesiones acumuladas"
          hint="Cada investigación completada se archiva aquí, mostrando cómo evoluciona el conocimiento del tema a lo largo del tiempo."
        />
      </div>
    );
  }

  return (
    <div className="timeline">
      <header className="timeline__head">
        <h2 className="timeline__title">
          <Icon name="clock" size={16} />
          Evolución del conocimiento
        </h2>
        <span className="timeline__count">
          {entries.length} {entries.length === 1 ? 'sesión' : 'sesiones'}
        </span>
      </header>

      <ol className="timeline__list">
        {entries.map((entry, i) => (
          <li className="timeline__item" key={entry.sessionId}>
            <div className="timeline__rail" aria-hidden="true">
              <span className="timeline__dot" />
              {i < entries.length - 1 && (
                <span className="timeline__line" />
              )}
            </div>
            <div className="timeline__card">
              <div className="timeline__stamp">
                {formatStamp(entry.timestamp)}
              </div>
              <div className="timeline__query">{entry.querySummary}</div>
              <div className="timeline__meta">
                {typeof entry.findingCount === 'number' && (
                  <span className="timeline__chip">
                    {entry.findingCount} hallazgos
                  </span>
                )}
                {entry.entities && entry.entities.length > 0 && (
                  <span className="timeline__entities">
                    {entry.entities.slice(0, 6).join(' · ')}
                  </span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
