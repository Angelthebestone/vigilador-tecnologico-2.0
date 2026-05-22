import { useEffect } from 'react';
import { useConfigStore } from '@/state/configStore';
import { WorkstreamToggles } from './WorkstreamToggles';
import { PromptEditor } from './PromptEditor';

export function ConfigView() {
  const fetchWorkstreams = useConfigStore((s) => s.fetchWorkstreams);
  const fetchPrompts = useConfigStore((s) => s.fetchPrompts);
  const fetchHealth = useConfigStore((s) => s.fetchHealth);

  useEffect(() => {
    fetchWorkstreams();
    fetchPrompts();
    fetchHealth();
  }, [fetchWorkstreams, fetchPrompts, fetchHealth]);

  return (
    <div className="atlas-body">
      <aside className="atlas-spine" aria-hidden="true">
        <span>Lám. IV</span>
        <span>·</span>
        <span>Tablero de Calibración</span>
        <span>·</span>
        <span>Workstreams &amp; Prompts</span>
      </aside>

      <div className="atlas-plate calibration-plate">
        <header className="calibration-plate__head">
          <div className="calibration-plate__kicker">
            <span className="atlas-eyebrow">Lám. IV · Configuración</span>
            <span className="calibration-plate__rule" aria-hidden="true" />
            <span className="atlas-folio">Tablero de calibración</span>
          </div>
          <h1 className="calibration-plate__title">
            Calibración del <em>instrumental</em>
          </h1>
          <p className="calibration-plate__lede">
            Active o repose los cinco workstreams del laboratorio y reescriba los
            prompts maestros que rigen la evaluación. Los cambios entran en vigor
            a partir de la <strong>siguiente sesión</strong>.
          </p>
        </header>

        <div className="calibration-plate__body">
          <WorkstreamToggles />
          <PromptEditor />
        </div>

        <footer className="calibration-plate__foot">
          <span>Atlas · Tablero IV</span>
          <span aria-hidden="true">— ✦ —</span>
          <span>Calibración manual del observatorio</span>
        </footer>
      </div>
    </div>
  );
}
