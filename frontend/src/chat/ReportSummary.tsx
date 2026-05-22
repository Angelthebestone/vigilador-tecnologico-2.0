import type { FinalReport, WsaResult, WscResult, WsdResult, WseResult } from '@/types';
import { useStore } from '@/state/useStore';
import { reportExportUrl } from '@/api';
import { Icon } from '@/components';
import { IntelligenceSections } from './IntelligenceSections';
import { WorkstreamIndicator } from '@/analysis/WorkstreamIndicator';
import { WSASection } from '@/analysis/WSASection';
import { WSCSection } from '@/analysis/WSCSection';
import { WSDSection } from '@/analysis/WSDSection';
import { WSESection } from '@/analysis/WSESection';

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

  const evaluation = report.evaluation;
  const activeWs = evaluation?.activeWorkstreams ?? [];

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

      <IntelligenceSections markdown={report.markdown} />

      {/* Spec 008 T036 — Workstream visualization sections */}
      {evaluation && activeWs.length > 0 && (
        <section className="report__workstreams">
          <header className="report__workstreams-header">
            <h3>Evaluación de Workstreams</h3>
            <WorkstreamIndicator />
          </header>
          {evaluation.wsA && (
            <WSASection data={evaluation.wsA as WsaResult} />
          )}
          {evaluation.wsC && (
            <WSCSection data={evaluation.wsC as WscResult} />
          )}
          {evaluation.wsD && (
            <WSDSection data={evaluation.wsD as WsdResult} />
          )}
          {evaluation.wsE && (
            <WSESection data={evaluation.wsE as WseResult} />
          )}
        </section>
      )}

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
