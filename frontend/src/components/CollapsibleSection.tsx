import { useId, useState, type ReactNode } from 'react';
import { Icon } from './Icon';

interface CollapsibleSectionProps {
  /** Resumen mostrado en la cabecera (estado colapsado y expandido). */
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  /** Texto monoespaciado del índice de archivo a la izquierda, ej. "§ PLAN". */
  marker?: string;
}

export function CollapsibleSection({
  summary,
  children,
  defaultOpen = false,
  marker,
}: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <section className="collapse" data-open={open}>
      <button
        type="button"
        className="collapse__head"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        {marker && (
          <span style={{ color: 'var(--ink-faint)', letterSpacing: '0.14em' }}>
            {marker}
          </span>
        )}
        <span style={{ flex: 1, minWidth: 0 }}>{summary}</span>
        <Icon name="chevron" size={14} className="collapse__chevron" />
      </button>
      <div
        className="collapse__panel"
        id={panelId}
        role="region"
        aria-hidden={!open}
      >
        <div>
          <div className="collapse__inner">{children}</div>
        </div>
      </div>
    </section>
  );
}
