import type { SSEConnectionStatus } from '@/types';

interface ConnectionStatusProps {
  status: SSEConnectionStatus;
}

const LABEL: Record<SSEConnectionStatus, string> = {
  connected: 'Enlace activo',
  connecting: 'Reconectando',
  disconnected: 'Sin enlace',
};

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  return (
    <span
      className={`conn conn--${status}`}
      role="status"
      aria-live="polite"
      title={`Estado del flujo en tiempo real: ${LABEL[status]}`}
    >
      <span className="conn__beacon" aria-hidden="true" />
      {LABEL[status]}
    </span>
  );
}
