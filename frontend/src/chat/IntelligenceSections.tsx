import { useMemo } from 'react';
import { Icon, type IconName } from '@/components';

interface IntelligenceSectionsProps {
  markdown: string;
}

/**
 * Las secciones de inteligencia derivada (impacto, contradicciones, señales
 * débiles, trayectoria causal) las genera el backend de forma determinística
 * y las anexa al final de `report.markdown`. Aquí se extraen por encabezado
 * `## ` y se renderizan como bloques colapsables.
 */
const KNOWN_SECTIONS: { title: string; icon: IconName }[] = [
  { title: 'Madurez tecnológica', icon: 'layers' },
  { title: 'Hallazgos priorizados por impacto', icon: 'gauge' },
  { title: 'Puntos en disputa', icon: 'scale' },
  { title: 'Señales débiles emergentes', icon: 'compass' },
  { title: 'Trayectoria causal', icon: 'route' },
];

type ParsedSection = { title: string; icon: IconName; lines: string[] };

function parseSections(markdown: string): ParsedSection[] {
  const result: ParsedSection[] = [];
  for (const { title, icon } of KNOWN_SECTIONS) {
    const start = markdown.indexOf(`## ${title}`);
    if (start === -1) continue;
    const bodyStart = start + `## ${title}`.length;
    const next = markdown.indexOf('\n## ', bodyStart);
    const body = markdown.slice(bodyStart, next === -1 ? undefined : next);
    const lines = body
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);
    if (lines.length > 0) result.push({ title, icon, lines });
  }
  return result;
}

export function IntelligenceSections({ markdown }: IntelligenceSectionsProps) {
  const sections = useMemo(() => parseSections(markdown), [markdown]);

  if (sections.length === 0) return null;

  return (
    <div className="report__intel">
      <div className="report__intel-head">Inteligencia derivada</div>
      {sections.map((section) => (
        <details className="report__intel-block" key={section.title} open>
          <summary className="report__intel-title">
            <Icon name={section.icon} size={14} />
            {section.title}
          </summary>
          <div className="report__intel-body">
            {section.lines.map((line, i) => (
              <p key={i}>{line.replace(/^[-#]+\s*/, '')}</p>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
