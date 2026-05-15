import type { ReactNode } from 'react';
import { Spinner } from './Spinner';

type Kind = 'loading' | 'empty' | 'error';

interface StateBlockProps {
  kind: Kind;
  /** Glifo monoespaciado, ej. "LÁMINA SIN TRAZAR". */
  glyph?: string;
  title: string;
  hint?: ReactNode;
  action?: ReactNode;
}

const DEFAULT_GLYPH: Record<Kind, string> = {
  loading: 'TRAZANDO LÁMINA',
  empty: 'LÁMINA EN BLANCO',
  error: 'ERROR DE REGISTRO',
};

export function StateBlock({
  kind,
  glyph,
  title,
  hint,
  action,
}: StateBlockProps) {
  return (
    <div
      className={`state-block ${kind === 'error' ? 'state-block--error' : ''}`}
      role={kind === 'error' ? 'alert' : 'status'}
    >
      {kind === 'loading' ? (
        <Spinner size="lg" />
      ) : (
        <span className="state-block__glyph">{glyph ?? DEFAULT_GLYPH[kind]}</span>
      )}
      <span className="state-block__title">{title}</span>
      {hint && <p className="state-block__hint">{hint}</p>}
      {action}
    </div>
  );
}
