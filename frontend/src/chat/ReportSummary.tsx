import type { FinalReport } from '@/types';
import { useStore } from '@/state/useStore';
import { reportExportUrl } from '@/api';
import { Icon } from '@/components';

interface ReportSummaryProps {
  report: FinalReport;
}

const VARIANT_LABELS: Record<string, string> = {
  technical: 'Técnico (I+D)',
  executive: 'Ejecutivo',
  risk: 'Riesgo / Cumplimiento',
  investor: 'Inversión',
};

export function ReportSummary({ report }: ReportSummaryProps) {
  const sessionId = useStore((s) => s.sessionId);
  const reportVariants = useStore((s) => s.reportVariants);

  const paragraphs = report.executiveSummary
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);

  const variants =
    reportVariants.length > 0 ? reportVariants : ['executive'];

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

      {sessionId && (
        <div className="report__export">
          <div className="report__export-label">
            <Icon name="upload" size={13} />
            Exportar informe
          </div>
          <div className="report__export-grid">
            {variants.map((variant) => {
              const reportId = `${sessionId}_${variant}`;
              return (
                <div className="report__export-row" key={variant}>
                  <span className="report__export-variant">
                    {VARIANT_LABELS[variant] ?? variant}
                  </span>
                  <div className="report__export-actions">
                    <a
                      className="btn btn--ghost btn--sm report__export-btn"
                      href={reportExportUrl(reportId, 'md')}
                      download
                    >
                      <Icon name="file" size={13} />
                      MD
                    </a>
                    <a
                      className="btn btn--ghost btn--sm report__export-btn"
                      href={reportExportUrl(reportId, 'html')}
                      download
                    >
                      <Icon name="file" size={13} />
                      HTML
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </article>
  );
}
