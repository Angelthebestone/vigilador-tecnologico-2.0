import type { FinalReport } from '@/types';

interface ReportSummaryProps {
  report: FinalReport;
}

export function ReportSummary({ report }: ReportSummaryProps) {
  const paragraphs = report.executiveSummary
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <article className="report">
      <header className="report__head">
        <h2 className="report__title">
          <small>Síntesis ejecutiva · Lámina I</small>
          Hallazgos consolidados
        </h2>
        <span className="badge badge--success">
          <span className="badge__dot" aria-hidden="true" />
          confianza {Math.round(report.confidenceScore * 100)}%
        </span>
      </header>

      <div className="report__body">
        {paragraphs.length > 0 ? (
          paragraphs.map((p, i) => <p key={i}>{p}</p>)
        ) : (
          <p>{report.executiveSummary || 'Sin resumen disponible.'}</p>
        )}
      </div>

      <div className="report__stats">
        <div className="report__stat">
          <div className="report__stat-num">{report.totalLearnings}</div>
          <div className="report__stat-label">Hallazgos</div>
        </div>
        <div className="report__stat">
          <div className="report__stat-num">
            {report.totalSourcesConsulted}
          </div>
          <div className="report__stat-label">Fuentes consultadas</div>
        </div>
        <div className="report__stat">
          <div className="report__stat-num">
            {report.recommendations.length}
          </div>
          <div className="report__stat-label">Recomendaciones</div>
        </div>
      </div>
    </article>
  );
}
