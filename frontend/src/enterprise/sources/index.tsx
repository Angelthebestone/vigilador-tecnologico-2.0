// Spec 021 D4 / T117 — Sources surface (placeholder).
// Lists ingestion connectors + their indexing state. Drive is the only
// MVP connector (FR-016); OneDrive / Outlook / Gmail are roadmap.

import { useState } from 'react';

type ConnectorState = 'connected' | 'pending' | 'error' | 'roadmap';

interface Connector {
  id: string;
  label: string;
  state: ConnectorState;
  lastIngestionAt?: string;
  documentCount?: number;
  note?: string;
}

const CONNECTORS: Connector[] = [
  {
    id: 'google_drive',
    label: 'Google Drive (read-only)',
    state: 'pending',
    note: 'Connect via /enterprise/onboarding/connectors/drive',
  },
  { id: 'onedrive', label: 'OneDrive', state: 'roadmap' },
  { id: 'outlook', label: 'Outlook', state: 'roadmap' },
  { id: 'gmail', label: 'Gmail', state: 'roadmap' },
];

const STATE_BADGE: Record<ConnectorState, { label: string; color: string }> = {
  connected: { label: 'Conectado', color: '#1d8a4a' },
  pending: { label: 'Pendiente', color: '#a87800' },
  error: { label: 'Error', color: '#c0392b' },
  roadmap: { label: 'Roadmap', color: '#888' },
};

export default function SourcesPlaceholder() {
  const [connectors] = useState<Connector[]>(CONNECTORS);

  return (
    <div style={{ padding: 24 }}>
      <h2>Fuentes de datos</h2>
      <p style={{ color: '#666', fontSize: 14 }}>
        Conectores de ingestión y estado de indexación.
      </p>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: '#f3f3f3' }}>
            <th style={{ textAlign: 'left', padding: 8 }}>Conector</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Estado</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Documentos</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Última ingestión</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Notas</th>
          </tr>
        </thead>
        <tbody>
          {connectors.map((c) => {
            const badge = STATE_BADGE[c.state];
            return (
              <tr key={c.id} style={{ borderTop: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{c.label}</td>
                <td style={{ padding: 8 }}>
                  <span
                    style={{
                      background: badge.color,
                      color: 'white',
                      padding: '2px 8px',
                      borderRadius: 4,
                      fontSize: 12,
                    }}
                  >
                    {badge.label}
                  </span>
                </td>
                <td style={{ padding: 8 }}>{c.documentCount ?? '—'}</td>
                <td style={{ padding: 8 }}>{c.lastIngestionAt ?? '—'}</td>
                <td style={{ padding: 8, color: '#666', fontSize: 13 }}>{c.note ?? ''}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p style={{ marginTop: 24, fontSize: 13, color: '#888' }}>
        Datos en vivo aterrizan cuando el dispatcher (T121) cablee
        /api/v2/enterprise/sources contra IngestionOrchestrator.
      </p>
    </div>
  );
}
