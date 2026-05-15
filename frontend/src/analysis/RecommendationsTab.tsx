import type { Recommendation } from '@/types';
import { StateBlock } from '@/components';

interface RecommendationsTabProps {
  recommendations: Recommendation[];
  loading: boolean;
  error: string | null;
}

type Priority = Recommendation['priority'];

const ORDER: Priority[] = ['alta', 'media', 'baja'];

const GROUP_LABEL: Record<Priority, string> = {
  alta: 'Prioridad alta',
  media: 'Prioridad media',
  baja: 'Prioridad baja',
};

const GROUP_TONE: Record<Priority, 'error' | 'warning' | 'info'> = {
  alta: 'error',
  media: 'warning',
  baja: 'info',
};

export function RecommendationsTab({
  recommendations,
  loading,
  error,
}: RecommendationsTabProps) {
  if (loading) {
    return <StateBlock kind="loading" title="Compilando recomendaciones" />;
  }
  if (error) {
    return (
      <StateBlock
        kind="error"
        title="No se pudieron cargar las recomendaciones"
        hint={error}
      />
    );
  }
  if (recommendations.length === 0) {
    return (
      <StateBlock
        kind="empty"
        glyph="SIN DICTAMEN"
        title="Aún no hay recomendaciones"
        hint="Las acciones sugeridas aparecen cuando el informe final está disponible."
      />
    );
  }

  return (
    <div className="recs">
      {ORDER.map((priority) => {
        const group = recommendations.filter((r) => r.priority === priority);
        if (group.length === 0) return null;
        return (
          <section key={priority}>
            <div className="recs__group-head">
              <h3 className="recs__group-title">{GROUP_LABEL[priority]}</h3>
              <span className={`badge badge--${GROUP_TONE[priority]}`}>
                <span className="badge__dot" aria-hidden="true" />
                {group.length}
              </span>
            </div>
            <div className="recs__list">
              {group.map((rec, i) => (
                <article
                  className="rec-card"
                  data-priority={priority}
                  key={`${priority}-${i}`}
                >
                  <span className="rec-card__idx">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <div>
                    <p className="rec-card__text">{rec.text}</p>
                    {rec.basedOn.length > 0 && (
                      <div className="rec-card__evidence">
                        {rec.basedOn.map((src, j) => (
                          <span className="rec-card__source" key={j}>
                            {src}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
