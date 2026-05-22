import { useState } from 'react';
import { useConfigStore } from '@/state/configStore';
import type { PromptKind } from '@/types';

const TEMPLATE_LABELS: Record<string, string> = {
  assumption_detection: 'Detección de Asunciones',
  counterfactual: 'Contra-factuales',
  falsification: 'Falsificación',
  query_expand: 'Expansión de Consulta',
  stakeholder_academic: 'Stakeholder Académico',
  stakeholder_competitor: 'Stakeholder Competidor',
  stakeholder_investor: 'Stakeholder Inversor',
  stakeholder_regulator: 'Stakeholder Regulador',
};

function templateKicker(name: string): string {
  if (name.startsWith('stakeholder')) return 'Simulación · Stakeholder';
  if (name === 'assumption_detection') return 'Auditoría · WS-C';
  if (name === 'counterfactual') return 'Crítica · WS-C';
  if (name === 'falsification') return 'Aseguramiento · WS-E';
  if (name === 'query_expand') return 'Expansión · WS-B';
  return 'Plantilla maestra';
}

const KIND_TABS: Array<{
  id: PromptKind;
  label: string;
  caption: string;
}> = [
  { id: 'system', label: 'Instrucciones', caption: 'System prompt' },
  { id: 'example_user', label: 'Ejemplo user', caption: 'sample_message_user' },
  { id: 'example_ai', label: 'Ejemplo AI', caption: 'sample_message_ai' },
];

function variantKey(kind: PromptKind): 'system' | 'exampleUser' | 'exampleAi' {
  if (kind === 'example_user') return 'exampleUser';
  if (kind === 'example_ai') return 'exampleAi';
  return 'system';
}

export function PromptEditor() {
  const prompts = useConfigStore((s) => s.prompts);
  const selectedPrompt = useConfigStore((s) => s.selectedPrompt);
  const selectedKind = useConfigStore((s) => s.selectedKind);
  const promptContents = useConfigStore((s) => s.promptContents);
  const loading = useConfigStore((s) => s.loading);
  const error = useConfigStore((s) => s.error);
  const selectPrompt = useConfigStore((s) => s.selectPrompt);
  const selectKind = useConfigStore((s) => s.selectKind);
  const updatePromptContent = useConfigStore((s) => s.updatePromptContent);
  const savePrompt = useConfigStore((s) => s.savePrompt);
  const restorePrompt = useConfigStore((s) => s.restorePrompt);

  const [confirmRestore, setConfirmRestore] = useState<{
    name: string;
    kind: PromptKind;
  } | null>(null);

  const selectedMeta = prompts.find((p) => p.name === selectedPrompt);
  const promptContent = selectedPrompt
    ? promptContents[`${selectedPrompt}::${selectedKind}`] ?? ''
    : '';
  const wordCount = promptContent
    ? promptContent.trim().split(/\s+/).filter(Boolean).length
    : 0;
  const lineCount = promptContent ? promptContent.split('\n').length : 0;

  const variantMeta = selectedMeta?.variants?.[variantKey(selectedKind)];
  const variantModified = variantMeta?.modified ?? false;

  return (
    <section className="calibration-section" aria-labelledby="cal-prompts">
      <header className="calibration-section__head">
        <div>
          <span className="atlas-eyebrow">B · Imprenta de prompts</span>
          <h2 id="cal-prompts" className="calibration-section__title">
            Prompts maestros
          </h2>
        </div>
        <div className="calibration-tally" aria-label="Plantillas con override">
          <span className="calibration-tally__num">
            {prompts.filter((p) => p.modified).length}
          </span>
          <span className="calibration-tally__den">/ {prompts.length}</span>
          <span className="calibration-tally__label">modificadas</span>
        </div>
      </header>

      <p className="calibration-section__desc">
        Reescriba las plantillas maestras de evaluación. Cada ficha tiene
        tres variantes editables: <em>Instrucciones</em> (system prompt),
        <em> Ejemplo user</em> y <em>Ejemplo AI</em> (par few-shot que se
        inyecta al modelo como <code>sample_message_user</code> /
        <code> sample_message_ai</code>). Los cambios se guardan como
        overrides reversibles.
      </p>

      {error && <div className="calibration-error" role="alert">{error}</div>}

      <div className="press">
        <nav className="press__index" aria-label="Índice de plantillas">
          <div className="press__index-head">
            <span className="atlas-eyebrow">Índice</span>
            <span className="press__count">{prompts.length} fichas</span>
          </div>
          <ol className="press__list">
            {prompts.map((p, idx) => {
              const active = selectedPrompt === p.name;
              return (
                <li key={p.name}>
                  <button
                    type="button"
                    className={`press__card${active ? ' press__card--active' : ''}`}
                    onClick={() => selectPrompt(p.name)}
                    disabled={loading}
                  >
                    <span className="press__card-num">
                      {String(idx + 1).padStart(2, '0')}
                    </span>
                    <span className="press__card-text">
                      <span className="press__card-kicker">
                        {templateKicker(p.name)}
                      </span>
                      <span className="press__card-name">
                        {TEMPLATE_LABELS[p.name] ?? p.name}
                      </span>
                    </span>
                    {p.modified && (
                      <span className="press__card-flag" aria-label="Modificado">
                        ✎
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>

        <div className="press__deck">
          {selectedPrompt ? (
            <article className="press__sheet">
              <header className="press__sheet-head">
                <div>
                  <span className="atlas-eyebrow">
                    Ficha · {templateKicker(selectedPrompt)}
                  </span>
                  <h3 className="press__sheet-title">
                    {TEMPLATE_LABELS[selectedPrompt] ?? selectedPrompt}
                  </h3>
                </div>
                {selectedMeta?.modified ? (
                  <span className="badge badge--warning">
                    <span className="badge__dot" aria-hidden="true" />
                    Override activo
                  </span>
                ) : (
                  <span className="badge badge--info">
                    <span className="badge__dot" aria-hidden="true" />
                    Plantilla de fábrica
                  </span>
                )}
              </header>

              <nav
                className="press__kinds"
                role="tablist"
                aria-label="Variante del prompt"
              >
                {KIND_TABS.map((t) => {
                  const meta = selectedMeta?.variants?.[variantKey(t.id)];
                  const tabModified = meta?.modified ?? false;
                  const isActive = selectedKind === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      role="tab"
                      aria-selected={isActive}
                      className={`press__kind${isActive ? ' press__kind--active' : ''}`}
                      onClick={() => selectKind(t.id)}
                      disabled={loading}
                    >
                      <span className="press__kind-label">{t.label}</span>
                      <span className="press__kind-caption">
                        {t.caption}
                        {tabModified && <em className="press__kind-flag"> ✎</em>}
                      </span>
                    </button>
                  );
                })}
              </nav>

              <div className="press__paper">
                <span className="press__paper-margin" aria-hidden="true" />
                <textarea
                  className="press__textarea"
                  value={promptContent}
                  onChange={(e) => updatePromptContent(e.target.value)}
                  disabled={loading}
                  rows={18}
                  spellCheck={false}
                  placeholder={
                    selectedKind === 'system'
                      ? 'Redacte el system prompt aquí…'
                      : selectedKind === 'example_user'
                        ? 'Pegue un mensaje de usuario representativo (entrada típica)…'
                        : 'Pegue la respuesta esperada del modelo para ese mensaje…'
                  }
                />
              </div>

              <footer className="press__sheet-foot">
                <dl className="press__meter">
                  <div>
                    <dt>Líneas</dt>
                    <dd>{lineCount}</dd>
                  </div>
                  <div>
                    <dt>Palabras</dt>
                    <dd>{wordCount}</dd>
                  </div>
                  <div>
                    <dt>Caracteres</dt>
                    <dd>{promptContent.length}</dd>
                  </div>
                </dl>
                <div className="press__actions">
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() =>
                      setConfirmRestore({
                        name: selectedPrompt,
                        kind: selectedKind,
                      })
                    }
                    disabled={loading || !variantModified}
                    title={
                      variantModified
                        ? 'Restaurar valor de fábrica de esta variante'
                        : 'Esta variante ya está en su valor de fábrica'
                    }
                  >
                    Restaurar fábrica
                  </button>
                  <button
                    type="button"
                    className="btn btn--primary"
                    onClick={savePrompt}
                    disabled={loading}
                  >
                    {loading ? 'Imprimiendo…' : 'Guardar override'}
                  </button>
                </div>
              </footer>
            </article>
          ) : (
            <div className="press__empty">
              <span className="press__empty-mark" aria-hidden="true">
                ¶
              </span>
              <p>Tome una ficha del índice para abrir su plantilla.</p>
              <span className="atlas-eyebrow">— Mesa de imprenta vacía —</span>
            </div>
          )}
        </div>
      </div>

      {confirmRestore && (
        <div
          className="press-confirm__overlay"
          onClick={() => setConfirmRestore(null)}
        >
          <div
            className="press-confirm__panel"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <span className="atlas-eyebrow">Reversión de variante</span>
            <h4 className="press-confirm__title">¿Restaurar valor de fábrica?</h4>
            <p className="press-confirm__body">
              Esto eliminará el override de la variante{' '}
              <strong>
                {KIND_TABS.find((t) => t.id === confirmRestore.kind)?.label}
              </strong>{' '}
              de la plantilla{' '}
              <strong>
                {TEMPLATE_LABELS[confirmRestore.name] ?? confirmRestore.name}
              </strong>
              . La acción no es reversible.
            </p>
            <div className="press-confirm__actions">
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setConfirmRestore(null)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn--danger"
                onClick={async () => {
                  await restorePrompt(confirmRestore.name, confirmRestore.kind);
                  setConfirmRestore(null);
                }}
                disabled={loading}
              >
                Restaurar
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
