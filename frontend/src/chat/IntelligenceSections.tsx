import { useMemo } from 'react';
import { Icon, type IconName } from '@/components';

interface IntelligenceSectionsProps {
  markdown?: string;
}

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
  { title: 'Visualizaciones generadas', icon: 'file', tone: 'signal' },
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

function renderLine(line: string, key: number): React.ReactNode {
  if (line.startsWith('###')) {
    return (
      <h4 className="report__intel-sub" key={key}>
        {line.replace(/^#+\s*/, '')}
      </h4>
    );
  }
  // Imagen markdown: ![alt](src)
  const imgMatch = line.match(/^!\[([^\]]*)\]\(([^)]+)\)/);
  if (imgMatch) {
    return (
      <figure key={key} className="report__intel-figure">
        <img
          src={imgMatch[2]}
          alt={imgMatch[1]}
          className="report__intel-img"
          loading="lazy"
        />
        {imgMatch[1] && (
          <figcaption className="report__intel-figcaption">{imgMatch[1]}</figcaption>
        )}
      </figure>
    );
  }
  return <p key={key}>{renderInline(line.replace(/^[-]+\s*/, ''))}</p>;
}

type TrlInfo = {
  min: number;
  max: number;
  phase: string;
  label: string;
  detail: string;
};

type TechMaturity = TrlInfo & { tech: string };

/** Extrae un rango TRL de un conjunto de líneas ("TRL 1-3 · …"). */
function parseTrlFromLines(lines: string[]): TrlInfo | null {
  for (const line of lines) {
    const clean = line.replace(/^[-*\s]+/, '').replace(/\*\*/g, '');
    const m = clean.match(/TRL\s+(\d+)-(\d+)\s*·\s*(.+)/i);
    if (m) {
      return {
        min: parseInt(m[1]),
        max: parseInt(m[2]),
        phase: m[3].trim(),
        label: clean,
        detail: lines
          .filter((l) => !l.includes('TRL') && !l.startsWith('#'))
          .map((l) => l.replace(/^[-*\s]+/, ''))
          .join(' '),
      };
    }
  }
  return null;
}

/**
 * Parsea la sección de madurez. El backend puede enviar:
 *  - Formato por tecnología: subtítulos `### Nombre` con su TRL debajo.
 *  - Formato global (legacy): un solo TRL sin subtítulos.
 * Devuelve una lista de tecnologías; si es global, devuelve una con tech "".
 */
function parseMaturity(lines: string[]): TechMaturity[] {
  const techHeaderIdxs = lines
    .map((l, i) => (l.startsWith('###') ? i : -1))
    .filter((i) => i >= 0);

  if (techHeaderIdxs.length === 0) {
    const trl = parseTrlFromLines(lines);
    return trl ? [{ ...trl, tech: '' }] : [];
  }

  const result: TechMaturity[] = [];
  for (let i = 0; i < techHeaderIdxs.length; i++) {
    const start = techHeaderIdxs[i];
    const end = i + 1 < techHeaderIdxs.length ? techHeaderIdxs[i + 1] : lines.length;
    const tech = lines[start].replace(/^#+\s*/, '').trim();
    const block = lines.slice(start + 1, end);
    const trl = parseTrlFromLines(block);
    if (trl) result.push({ ...trl, tech });
  }
  return result;
}

const TRL_DESCRIPTIONS: Record<string, string[]> = {
  'investigación básica': [
    'Principios básicos observados y reportados (TRL 1)',
    'Concepto tecnológico formulado (TRL 2)',
    'Prueba de concepto analítica y experimental (TRL 3)',
  ],
  'validación y prototipos': [
    'Validación en entorno de laboratorio (TRL 4)',
    'Validación en entorno relevante (TRL 5)',
    'Demostración en entorno relevante (TRL 6)',
  ],
  'comercialización': [
    'Demostración en entorno operacional (TRL 7)',
    'Sistema completo y calificado (TRL 8)',
    'Tecnología probada en entorno real (TRL 9)',
  ],
};

/** Gauge visual del nivel TRL con escala de 1 a 9 */
function TrlGauge({ min, max, phase }: { min: number; max: number; phase: string }) {
  const levels = [1, 2, 3, 4, 5, 6, 7, 8, 9];
  const phaseColors: Record<string, string> = {
    'investigación básica': 'var(--gray-dark)',
    'validación y prototipos': 'var(--lime-deep)',
    'comercialización': 'var(--uts-green)',
  };
  const color = phaseColors[phase] ?? 'var(--lime-deep)';

  return (
    <div className="trl-gauge">
      <div className="trl-gauge__track">
        {levels.map((lvl) => (
          <div
            key={lvl}
            className={`trl-gauge__cell ${lvl >= min && lvl <= max ? 'trl-gauge__cell--active' : ''}`}
            style={lvl >= min && lvl <= max ? { background: color, borderColor: color } : {}}
            title={`TRL ${lvl}`}
          >
            <span className="trl-gauge__num">{lvl}</span>
          </div>
        ))}
      </div>
      <div className="trl-gauge__labels">
        <span>Investigación</span>
        <span>Validación</span>
        <span>Comercialización</span>
      </div>
    </div>
  );
}

/** Tarjeta de madurez de una tecnología individual. */
function TechMaturityCard({ data }: { data: TechMaturity }) {
  const phaseKey = data.phase.toLowerCase();
  const descriptions = Object.entries(TRL_DESCRIPTIONS).find(([k]) =>
    phaseKey.includes(k.split(' ')[0]),
  );

  return (
    <div className="trl-card">
      {data.tech && <div className="trl-card__tech">{data.tech}</div>}

      <TrlGauge min={data.min} max={data.max} phase={data.phase} />

      <div className="trl-card__phase-badge">
        <strong>{data.label}</strong>
      </div>

      {data.detail && <p className="trl-card__detail">{data.detail}</p>}

      {descriptions && (
        <div className="trl-card__levels">
          <div className="trl-card__levels-title">¿Qué implica este nivel?</div>
          <ul className="trl-card__levels-list">
            {descriptions[1].map((desc, i) => {
              const lvl = (descriptions[0] === 'investigación básica' ? 1 : descriptions[0] === 'validación y prototipos' ? 4 : 7) + i;
              return (
                <li
                  key={i}
                  className={lvl >= data.min && lvl <= data.max ? 'trl-level--active' : 'trl-level--inactive'}
                >
                  {desc}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="trl-card__context">
        {data.min <= 3 && (
          <p>
            Etapa de <strong>investigación básica</strong>. Los hallazgos provienen
            de publicaciones académicas y pruebas de concepto. No se recomienda
            inversión productiva inmediata sin validación adicional.
          </p>
        )}
        {data.min >= 4 && data.max <= 6 && (
          <p>
            En <strong>validación activa</strong>: existen prototipos funcionales y
            pilotos en entornos controlados. Momento óptimo para proyectos piloto y
            alianzas de I+D.
          </p>
        )}
        {data.min >= 7 && (
          <p>
            Ha alcanzado <strong>madurez comercial</strong>: hay productos desplegados
            en entornos reales. La barrera principal es la adopción empresarial, no la
            viabilidad técnica.
          </p>
        )}
      </div>
    </div>
  );
}

function MaturitySection({ lines }: { lines: string[] }) {
  const technologies = parseMaturity(lines);

  if (technologies.length === 0) {
    return <>{lines.map((line, i) => renderLine(line, i))}</>;
  }

  // Líneas introductorias antes del primer subtítulo de tecnología.
  const firstHeaderIdx = lines.findIndex((l) => l.startsWith('###'));
  const intro = firstHeaderIdx > 0 ? lines.slice(0, firstHeaderIdx) : [];

  return (
    <div className="trl-section">
      {intro
        .filter((l) => !l.includes('TRL'))
        .map((line, i) => renderLine(line, i))}
      <div className="trl-section__grid">
        {technologies.map((t, i) => (
          <TechMaturityCard key={t.tech || i} data={t} />
        ))}
      </div>
    </div>
  );
}

export function IntelligenceSections({ markdown }: IntelligenceSectionsProps) {
  const sections = useMemo(() => {
    if (!markdown) return [];
    return parseSections(markdown);
  }, [markdown]);

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
            {section.title === 'Madurez tecnológica'
              ? <MaturitySection lines={section.lines} />
              : section.lines.map((line, i) => renderLine(line, i))
            }
          </div>
        </details>
      ))}
    </div>
  );
}
