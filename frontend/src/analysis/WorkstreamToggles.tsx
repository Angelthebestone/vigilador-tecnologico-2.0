import { useConfigStore } from '@/state/configStore';
import type { WorkstreamConfig, WorkstreamHealth } from '@/types';

const WORKSTREAM_DEFS: Array<{
  key: keyof WorkstreamConfig;
  label: string;
  code: string;
  ordinal: string;
  description: string;
  tooltip: string;
  healthKey: keyof WorkstreamHealth;
}> = [
  {
    key: 'wsA',
    label: 'Source Quality',
    code: 'WS-A',
    ordinal: '§ I',
    description: 'Verifica reputación de autores, conflictos de interés y retractaciones.',
    tooltip: 'Activa validación de fuentes: reputación académica, conflictos de interés, fact-checking externo y monitor de retractaciones.',
    healthKey: 'wsA',
  },
  {
    key: 'wsB',
    label: 'Data Intelligence',
    code: 'WS-B',
    ordinal: '§ II',
    description: 'Deduplica fuentes, detecta contenido sintético y mapea consensos.',
    tooltip: 'Activa inteligencia de datos: búsqueda híbrida BM25+embeddings, deduplicación semántica, detección de IA y mapeo de disputas.',
    healthKey: 'wsB',
  },
  {
    key: 'wsC',
    label: 'Deep Analysis',
    code: 'WS-C',
    ordinal: '§ III',
    description: 'Proyecta curvas-S, detecta asunciones implícitas y dependencias críticas.',
    tooltip: 'Activa análisis profundo: proyecciones logísticas, meta-análisis DerSimonian-Laird, detección de asunciones y contra-factuales.',
    healthKey: 'wsC',
  },
  {
    key: 'wsD',
    label: 'Strategic Signals',
    code: 'WS-D',
    ordinal: '§ IV',
    description: 'Rastrea convergencia tecnológica, movilidad de talento y gaps de patentamiento.',
    tooltip: 'Activa señales estratégicas: clustering aglomerativo, redes de colaboración, linajes de ideas y análisis de patentamiento.',
    healthKey: 'wsD',
  },
  {
    key: 'wsE',
    label: 'Output Assurance',
    code: 'WS-E',
    ordinal: '§ V',
    description: 'Audita sesgos, simula stakeholders y calibra confianza del reporte.',
    tooltip: 'Activa aseguramiento de salida: auditoría de sesgos, simulación de stakeholders, falsificación y calibración isotónica de confianza.',
    healthKey: 'wsE',
  },
];

function healthBadgeClass(health: WorkstreamHealth | null, wsKey: keyof WorkstreamHealth): string {
  if (!health) return 'badge--info';
  const ws = health[wsKey];
  if (!ws) return 'badge--info';
  if (ws.degradedServices.length > 0) return 'badge--warning';
  return ws.available ? 'badge--success' : 'badge--error';
}

function healthLabel(health: WorkstreamHealth | null, wsKey: keyof WorkstreamHealth): string {
  if (!health) return 'S/D';
  const ws = health[wsKey];
  if (!ws) return 'S/D';
  if (ws.degradedServices.length > 0) return 'Degradado';
  return ws.available ? 'OK' : 'Error';
}

export function WorkstreamToggles() {
  const workstreams = useConfigStore((s) => s.workstreams);
  const health = useConfigStore((s) => s.health);
  const loading = useConfigStore((s) => s.loading);
  const error = useConfigStore((s) => s.error);
  const toggleWorkstream = useConfigStore((s) => s.toggleWorkstream);
  const saveWorkstreams = useConfigStore((s) => s.saveWorkstreams);

  const activeCount = WORKSTREAM_DEFS.filter((d) => workstreams[d.key]).length;

  return (
    <section className="calibration-section" aria-labelledby="cal-ws">
      <header className="calibration-section__head">
        <div>
          <span className="atlas-eyebrow">A · Tablero de instrumentos</span>
          <h2 id="cal-ws" className="calibration-section__title">
            Workstreams
          </h2>
        </div>
        <div className="calibration-tally" aria-label="Workstreams activos">
          <span className="calibration-tally__num">{activeCount}</span>
          <span className="calibration-tally__den">/ {WORKSTREAM_DEFS.length}</span>
          <span className="calibration-tally__label">en línea</span>
        </div>
      </header>

      <p className="calibration-section__desc">
        Cada workstream es un instrumento independiente del observatorio. Bájele
        la palanca para detenerlo o súbala para incorporarlo al próximo análisis.
      </p>

      {error && <div className="calibration-error" role="alert">{error}</div>}

      <ol className="ws-bench">
        {WORKSTREAM_DEFS.map((def) => {
          const on = workstreams[def.key];
          return (
            <li
              key={def.key}
              className={`ws-dial${on ? ' ws-dial--on' : ''}`}
              title={def.tooltip}
            >
              <div className="ws-dial__plate">
                <span className="ws-dial__ordinal">{def.ordinal}</span>
                <span className="ws-dial__code">{def.code}</span>
              </div>

              <div className="ws-dial__body">
                <div className="ws-dial__heading">
                  <h3 className="ws-dial__label">{def.label}</h3>
                  <span className={`badge ${healthBadgeClass(health, def.healthKey)}`}>
                    <span className="badge__dot" aria-hidden="true" />
                    {healthLabel(health, def.healthKey)}
                  </span>
                </div>
                <p className="ws-dial__desc">{def.description}</p>
              </div>

              <label className={`ws-lever${on ? ' ws-lever--on' : ''}`}>
                <input
                  type="checkbox"
                  className="ws-lever__input"
                  checked={on}
                  onChange={() => toggleWorkstream(def.key)}
                  disabled={loading}
                  aria-label={`Activar ${def.label}`}
                />
                <span className="ws-lever__track" aria-hidden="true">
                  <span className="ws-lever__notch ws-lever__notch--off">OFF</span>
                  <span className="ws-lever__notch ws-lever__notch--on">ON</span>
                  <span className="ws-lever__knob" />
                </span>
              </label>
            </li>
          );
        })}
      </ol>

      <div className="calibration-section__actions">
        <button
          type="button"
          className="btn btn--primary"
          onClick={saveWorkstreams}
          disabled={loading}
        >
          {loading ? 'Sellando…' : 'Sellar calibración'}
        </button>
        <span className="calibration-hint">
          Aplicado al siguiente análisis · sin reinicio
        </span>
      </div>
    </section>
  );
}
