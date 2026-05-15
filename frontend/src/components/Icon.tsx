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
  | 'search';

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
