import type { WscResult } from '@/types';
import { WorkstreamSection } from './WorkstreamSection';
import { ChartImage } from './ChartImage';

interface WSCSectionProps {
  data: WscResult;
}

export function WSCSection({ data }: WSCSectionProps) {
  return (
    <WorkstreamSection title="Análisis profundo (WS-C)" icon="cpu" status="active">

      {data.sCurves.length > 0 && (
        <div className="ws-block">
          <h4>Proyecciones de curva S</h4>
          <p className="ws-explain">
            La curva S modela el ciclo de adopción de una tecnología: crecimiento lento inicial,
            aceleración exponencial alrededor del <strong>punto de inflexión</strong> y meseta al
            alcanzar el techo de adopción del mercado. El <strong>R²</strong> indica qué tan bien
            se ajusta el modelo a los datos observados (1.0 = ajuste perfecto).
          </p>
          <div className="ws-scurve-list">
            {data.sCurves.map((s, i) => (
              <div key={i} className="ws-scurve-card">
                <div className="ws-scurve-card__title">{s.technology}</div>

                {s.chartImage ? (
                  <ChartImage
                    src={s.chartImage}
                    alt={`Curva S de adopción de ${s.technology}`}
                  />
                ) : (
                  <div className="ws-stat-grid">
                    <div className="ws-stat-cell">
                      <span className="ws-stat-cell__label">Tasa de crecimiento</span>
                      <span className="ws-stat-cell__value">{s.growthRate.toFixed(2)}</span>
                    </div>
                    <div className="ws-stat-cell">
                      <span className="ws-stat-cell__label">Punto de inflexión</span>
                      <span className="ws-stat-cell__value">{s.inflectionYear}</span>
                    </div>
                    <div className="ws-stat-cell">
                      <span className="ws-stat-cell__label">Techo de adopción</span>
                      <span className="ws-stat-cell__value">{Math.round(s.ceiling * 100)}%</span>
                    </div>
                    <div className="ws-stat-cell">
                      <span className="ws-stat-cell__label">Ajuste (R²)</span>
                      <span className="ws-stat-cell__value">{s.rSquared.toFixed(2)}</span>
                    </div>
                  </div>
                )}

                <div className="ws-scurve-card__interpretation">
                  {s.growthRate >= 0.2
                    ? `Adopción rápida — se espera que ${s.technology} alcance el punto de inflexión en ${s.inflectionYear}, con adopción acelerada.`
                    : s.growthRate >= 0.1
                    ? `Adopción moderada — ${s.technology} muestra crecimiento sostenido hacia ${s.inflectionYear}.`
                    : `Adopción lenta — ${s.technology} se encuentra en fase temprana de maduración.`}
                  {s.rSquared >= 0.8
                    ? ` El modelo es confiable (R²=${s.rSquared.toFixed(2)}).`
                    : ` Datos insuficientes para un ajuste sólido (R²=${s.rSquared.toFixed(2)}).`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Gráficos adicionales generados por el backend (matplotlib) */}
      {data.charts && data.charts.length > 0 && (
        <div className="ws-block">
          <h4>Visualizaciones analíticas</h4>
          {data.charts.map((c, i) => (
            <ChartImage key={i} src={c.image} alt={c.title} caption={c.caption} />
          ))}
        </div>
      )}

      {data.metaAnalyses.length > 0 && (
        <div className="ws-block">
          <h4>Meta-análisis estadísticos</h4>
          <p className="ws-explain">
            Un meta-análisis combina resultados de múltiples estudios. El <strong>tamaño del efecto (ES)</strong>{' '}
            mide la magnitud del fenómeno estudiado. El <strong>I²</strong> mide la heterogeneidad entre estudios:
            I² {'>'} 75% indica alta variabilidad y resultados potencialmente inconsistentes entre sí.
          </p>
          {data.metaAnalyses.map((m, i) => (
            <div key={i} className="ws-meta-card">
              <div className="ws-meta-card__topic">{m.topic}</div>
              <div className="ws-meta-card__stats">
                <div className="ws-meta-stat">
                  <span className="ws-meta-stat__label">Tamaño del efecto</span>
                  <span className="ws-meta-stat__value">
                    {m.effectSizeRange[0].toFixed(2)} – {m.effectSizeRange[1].toFixed(2)}
                  </span>
                  <span className="ws-meta-stat__hint">
                    {m.effectSizeRange[1] < 0.2 ? 'efecto pequeño' : m.effectSizeRange[1] < 0.5 ? 'efecto moderado' : 'efecto grande'}
                  </span>
                </div>
                <div className="ws-meta-stat">
                  <span className="ws-meta-stat__label">Heterogeneidad (I²)</span>
                  <span className={`ws-meta-stat__value ${m.iSquared > 0.75 ? 'ws-meta-stat__value--warn' : ''}`}>
                    {Math.round(m.iSquared * 100)}%
                  </span>
                  <span className="ws-meta-stat__hint">
                    {m.iSquared > 0.75 ? 'alta variabilidad' : m.iSquared > 0.4 ? 'heterogeneidad moderada' : 'estudios consistentes'}
                  </span>
                </div>
                <div className="ws-meta-stat">
                  <span className="ws-meta-stat__label">Estudios analizados</span>
                  <span className="ws-meta-stat__value">{m.sampleCount}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {data.implicitAssumptions.length > 0 && (
        <div className="ws-block">
          <h4>Supuestos implícitos detectados</h4>
          <p className="ws-explain">
            Premisas no declaradas explícitamente en los hallazgos pero que son necesarias
            para que las conclusiones sean válidas. Su invalidación puede afectar la confianza del análisis.
          </p>
          <div className="ws-assumption-list">
            {data.implicitAssumptions.map((a, i) => (
              <div key={i} className={`ws-assumption ws-assumption--${a.severity}`}>
                <span className={`badge badge--sm ${a.severity === 'critical' || a.severity === 'high' ? 'badge--alert' : a.severity === 'medium' ? 'badge--warning' : 'badge--info'}`}>
                  {a.severity === 'high' || a.severity === 'critical' ? 'Crítico' : a.severity === 'medium' ? 'Medio' : 'Bajo'}
                </span>
                <span className="ws-assumption__text">{a.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.counterfactuals.length > 0 && (
        <div className="ws-block">
          <h4>Escenarios contrafactuales</h4>
          <p className="ws-explain">
            Escenarios alternativos que, de materializarse, invalidarían total o parcialmente
            las conclusiones del análisis. Sirven para evaluar la robustez de los hallazgos.
          </p>
          <div className="ws-counterfactual-list">
            {data.counterfactuals.map((c, i) => (
              <div key={i} className="ws-counterfactual">
                <div className="ws-counterfactual__scenario">{c.scenario}</div>
                <div className="ws-counterfactual__meta">
                  <span className={`badge badge--sm ${c.plausibility === 'high' ? 'badge--alert' : c.plausibility === 'medium' ? 'badge--warning' : 'badge--info'}`}>
                    Plausibilidad {c.plausibility === 'high' ? 'alta' : c.plausibility === 'medium' ? 'media' : 'baja'}
                  </span>
                  {c.wouldInvalidate && (
                    <span className="ws-counterfactual__invalidates">
                      Invalidaría: {c.wouldInvalidate}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.criticalDependencies.length > 0 && (
        <div className="ws-block">
          <h4>Dependencias críticas</h4>
          <p className="ws-explain">
            Factores externos cuya ausencia o fallo comprometería directamente los resultados
            proyectados. Identificarlas permite diseñar estrategias de mitigación.
          </p>
          <div className="ws-dependency-list">
            {data.criticalDependencies.map((d, i) => (
              <div key={i} className="ws-dependency">
                <div className="ws-dependency__header">
                  <strong>{d.dependencyName}</strong>
                  <span className={`badge badge--sm ${d.impactIfRemoved === 'critical' ? 'badge--alert' : 'badge--warning'}`}>
                    Impacto {d.impactIfRemoved === 'critical' ? 'crítico' : d.impactIfRemoved}
                  </span>
                </div>
                {d.alternatives && d.alternatives.length > 0 && (
                  <div className="ws-dependency__alternatives">
                    <span className="ws-dependency__alt-label">Alternativas:</span>
                    {d.alternatives.map((alt, j) => (
                      <span key={j} className="badge badge--sm badge--info">{alt}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </WorkstreamSection>
  );
}
