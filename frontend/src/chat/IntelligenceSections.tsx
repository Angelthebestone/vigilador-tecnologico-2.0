import { useMemo } from 'react';
import { Icon, type IconName } from '@/components';

interface IntelligenceSectionsProps {
  markdown: string;
}

/**
 * Las secciones de inteligencia derivada las genera el backend de forma
 * determinística y las anexa al final de `report.markdown`. Aquí se extraen
 * por encabezado `## ` y se renderizan como bloques colapsables.
 *
 * `tone` marca secciones de señal (madurez = ¿es real?, verificación =
 * ¿hay debilidades?) para resaltarlas visualmente sin salir de la paleta.
 */
type SectionTone = 'neutral' | 'signal' | 'warn';

const KNOWN_SECTIONS: {
  title: string;
  icon: IconName;
  tone: SectionTone;
}[] = [
  { title: 'Madurez tecnológica', icon: 'layers', tone: 'signal' },
  { title: 'Hallazgos priorizados por impacto', icon: 'gauge', tone: 'neutral' },
  { title: 'Puntos en disputa', icon: 'scale', tone: 'neutral' },
  { title: 'Señales débiles emergentes', icon: 'compass', tone: 'neutral' },
  { title: 'Trayectoria causal', icon: 'route', tone: 'neutral' },
  { title: 'Verificación adversarial', icon: 'shield', tone: 'warn' },
];

type ParsedSection = {
  title: string;
  icon: IconName;
  tone: SectionTone;
  lines: string[];
};

function parseSections(markdown: string): ParsedSection[] {
  const result: ParsedSection[] = [];
  for (const { title, icon, tone } of KNOWN_SECTIONS) {
    const start = markdown.indexOf(`## ${title}`);
    if (start === -1) continue;
    const bodyStart = start + `## ${title}`.length;
    const next = markdown.indexOf('\n## ', bodyStart);
    const body = markdown.slice(bodyStart, next === -1 ? undefined : next);
    const lines = body
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);
    if (lines.length > 0) result.push({ title, icon, tone, lines });
  }
  return result;
}

/**
 * Parser inline mínimo: convierte `**negrita**` y `` `código` `` del markdown
 * en nodos React. Sin librería de markdown para mantener coherencia con el
 * sistema de diseño propio.
 */
function renderInline(text: string): React.ReactNode[] {
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return tokens.filter(Boolean).map((token, i) => {
    if (token.startsWith('**') && token.endsWith('**')) {
      return <strong key={i}>{token.slice(2, -2)}</strong>;
    }
    if (token.startsWith('`') && token.endsWith('`')) {
      return <code key={i}>{token.slice(1, -1)}</code>;
    }
    return <span key={i}>{token}</span>;
  });
}

/** Una línea del cuerpo: subtítulo `### x` o párrafo (con markdown inline). */
function renderLine(line: string, key: number): React.ReactNode {
  if (line.startsWith('###')) {
    return (
      <h4 className="report__intel-sub" key={key}>
        {line.replace(/^#+\s*/, '')}
      </h4>
    );
  }
  return <p key={key}>{renderInline(line.replace(/^[-]+\s*/, ''))}</p>;
}

export function IntelligenceSections({ markdown }: IntelligenceSectionsProps) {
  const sections = useMemo(() => parseSections(markdown), [markdown]);

  if (sections.length === 0) return null;

  return (
    <div className="report__intel">
      <div className="report__intel-head">Inteligencia derivada</div>
      {sections.map((section) => (
        <details
          className={`report__intel-block report__intel-block--${section.tone}`}
          key={section.title}
          open
        >
          <summary className="report__intel-title">
            <Icon name={section.icon} size={14} />
            {section.title}
          </summary>
          <div className="report__intel-body">
            {section.lines.map((line, i) => renderLine(line, i))}
          </div>
        </details>
      ))}
    </div>
  );
}
