/**
 * Iconografía propia estilo grabado de atlas: trazo fino, sin relleno.
 * No se usa librería externa para mantener coherencia con la estética
 * de cuaderno de laboratorio (líneas de 1.5px, terminaciones rectas).
 */

export type IconName =
  | 'arrow-left'
  | 'arrow-right'
  | 'chevron'
  | 'plus'
  | 'close'
  | 'compass'
  | 'send'
  | 'graph'
  | 'chat'
  | 'layers'
  | 'flask'
  | 'panel'
  | 'route'
  | 'search'
  | 'trash'
  | 'paperclip'
  | 'file'
  | 'upload'
  | 'image'
  | 'check'
  | 'clock'
  | 'gauge'
  | 'scale'
  | 'shield'
  | 'cpu'
  | 'database'
  | 'trending-up';

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
}

const PATHS: Record<IconName, React.ReactNode> = {
  'arrow-left': <path d="M13 4 6 10l7 6M6 10h9" />,
  'arrow-right': <path d="M7 4l7 6-7 6M14 10H5" />,
  chevron: <path d="M7 5l6 5-6 5" />,
  plus: <path d="M10 4v12M4 10h12" />,
  close: <path d="M5 5l10 10M15 5L5 15" />,
  compass: (
    <>
      <circle cx="10" cy="10" r="7" />
      <path d="M13 7l-2 4-4 2 2-4z" />
    </>
  ),
  send: <path d="M3 10l14-6-5 14-3-6-6-2z" />,
  graph: (
    <>
      <circle cx="5" cy="6" r="2" />
      <circle cx="15" cy="5" r="2" />
      <circle cx="11" cy="15" r="2" />
      <path d="M6.6 7.2 9.4 13.4M7 6.4 13 5.2M13.6 6.6 11.6 13" />
    </>
  ),
  chat: <path d="M3 5h14v9H8l-4 3v-3H3z" />,
  layers: <path d="M10 3 3 7l7 4 7-4-7-4zM3 11l7 4 7-4M3 14.5 10 18l7-3.5" />,
  flask: (
    <>
      <path d="M8 3h4M8.5 3v5l-4 7a1.5 1.5 0 0 0 1.3 2.3h8.4A1.5 1.5 0 0 0 19.5 16l-4-7V3" />
      <path d="M6 14h8" />
    </>
  ),
  panel: (
    <>
      <rect x="3" y="4" width="14" height="12" />
      <path d="M12 4v12" />
    </>
  ),
  route: (
    <>
      <circle cx="5" cy="5" r="2" />
      <circle cx="15" cy="15" r="2" />
      <path d="M5 7v4a3 3 0 0 0 3 3h5" />
    </>
  ),
  search: (
    <>
      <circle cx="8.5" cy="8.5" r="5" />
      <path d="M12.5 12.5 17 17" />
    </>
  ),
  trash: (
    <>
      <path d="M6 6v10a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6" />
      <path d="M4 6h12M8 6V4h4v2" />
      <path d="M8.5 9v5M11.5 9v5" />
    </>
  ),
  paperclip: <path d="M15 7l-6.5 6.5a2.1 2.1 0 1 1-3-3L12 4a3 3 0 0 1 4.2 4.2L9.7 14.7a1.5 1.5 0 0 1-2.1-2.1L13 7" />,
  file: (
    <>
      <path d="M6 3h6l4 4v10a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
      <path d="M12 3v4h4" />
    </>
  ),
  upload: (
    <>
      <path d="M10 14V5M6 9l4-4 4 4" />
      <path d="M4 14v2a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-2" />
    </>
  ),
  image: (
    <>
      <rect x="3" y="4" width="14" height="12" rx="1" />
      <circle cx="7" cy="8" r="1.5" />
      <path d="M17 13l-3.5-4-2.5 3-2-2L3 16" />
    </>
  ),
  check: <path d="M4 10l4 4 8-9" />,
  clock: (
    <>
      <circle cx="10" cy="10" r="7" />
      <path d="M10 5.5V10l3 2" />
    </>
  ),
  gauge: (
    <>
      <path d="M3 14a7 7 0 0 1 14 0" />
      <path d="M10 14l4-4" />
      <circle cx="10" cy="14" r="1" />
    </>
  ),
  scale: (
    <>
      <path d="M10 3v14M6 17h8" />
      <path d="M10 5 4 8m6-3 6 3" />
      <path d="M2 8a2.5 4 0 0 0 4 0M14 8a2.5 4 0 0 0 4 0" />
    </>
  ),
  shield: (
    <>
      <path d="M10 3 4 5v5c0 4 2.6 6.4 6 7.5 3.4-1.1 6-3.5 6-7.5V5l-6-2z" />
      <path d="M7.5 10l2 2 3.5-4" />
    </>
  ),
  cpu: (
    <>
      <rect x="6" y="6" width="8" height="8" />
      <path d="M8 3v3M12 3v3M8 14v3M12 14v3M3 8h3M3 12h3M14 8h3M14 12h3" />
    </>
  ),
  database: (
    <>
      <ellipse cx="10" cy="5" rx="6" ry="2.5" />
      <path d="M4 5v10c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5V5" />
      <path d="M4 10c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5" />
    </>
  ),
  'trending-up': (
    <>
      <path d="M3 14l5-5 3 3 6-6" />
      <path d="M13 6h4v4" />
    </>
  ),
};

export function Icon({ name, size = 16, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="square"
      strokeLinejoin="miter"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}
