// Spec 021 D4 / T118 — Admin surface (placeholder).
// Lists tools/MCPs MVP + UP/DOWN healthcheck status (lee
// MCPProcessSupervisor + HealthMonitor + ToolRegistry in T121).
// API key config UI is a placeholder; real wiring happens
// against /api/v2/enterprise/admin/* endpoints.

import { useState } from 'react';

type ToolStatus = 'UP' | 'DOWN' | 'UNCONFIGURED' | 'UNKNOWN';

interface ToolRow {
  id: string;
  domain: string;
  status: ToolStatus;
  needsKey: boolean;
  envVar?: string;
}

const PLACEHOLDER_TOOLS: ToolRow[] = [
  { id: 'tavily', domain: 'research', status: 'UNCONFIGURED', needsKey: true, envVar: 'VT_TAVILY_API_KEY' },
  { id: 'brave', domain: 'research', status: 'UNCONFIGURED', needsKey: true, envVar: 'VT_BRAVE_API_KEY' },
  { id: 'exa', domain: 'research', status: 'UNCONFIGURED', needsKey: true, envVar: 'VT_EXA_API_KEY' },
  { id: 'jina', domain: 'research', status: 'UP', needsKey: false },
  { id: 'fetch', domain: 'web', status: 'UP', needsKey: false },
  { id: 'arxiv', domain: 'research', status: 'UP', needsKey: false },
  { id: 'computer_use', domain: 'desktop', status: 'UNCONFIGURED', needsKey: false, envVar: 'VT_COMPUTER_USE_ENABLED' },
];

const STATUS_COLOR: Record<ToolStatus, string> = {
  UP: '#1d8a4a',
  DOWN: '#c0392b',
  UNCONFIGURED: '#a87800',
  UNKNOWN: '#888',
};

export default function AdminPlaceholder() {
  const [tools] = useState<ToolRow[]>(PLACEHOLDER_TOOLS);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [keyValue, setKeyValue] = useState('');

  const handleSaveKey = (toolId: string) => {
    // Wired against POST /api/v2/enterprise/admin/keys in T121.
    console.info('[admin] would persist key for', toolId, '(', keyValue.length, 'chars)');
    setEditingKey(null);
    setKeyValue('');
  };

  return (
    <div style={{ padding: 24 }}>
      <h2>Admin — Tools & API keys</h2>
      <p style={{ color: '#666', fontSize: 14 }}>
        Estado de herramientas MVP. Los datos en vivo aterrizan cuando T121
        cablee /api/v2/enterprise/admin/tools contra ToolRegistry + HealthMonitor.
      </p>

      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 16 }}>
        <thead>
          <tr style={{ background: '#f3f3f3' }}>
            <th style={{ textAlign: 'left', padding: 8 }}>Tool</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Dominio</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Estado</th>
            <th style={{ textAlign: 'left', padding: 8 }}>API key</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Acción</th>
          </tr>
        </thead>
        <tbody>
          {tools.map((tool) => (
            <tr key={tool.id} style={{ borderTop: '1px solid #eee' }}>
              <td style={{ padding: 8, fontFamily: 'monospace' }}>{tool.id}</td>
              <td style={{ padding: 8 }}>{tool.domain}</td>
              <td style={{ padding: 8 }}>
                <span
                  style={{
                    background: STATUS_COLOR[tool.status],
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: 12,
                  }}
                >
                  {tool.status}
                </span>
              </td>
              <td style={{ padding: 8, fontFamily: 'monospace', fontSize: 12 }}>
                {tool.envVar ?? '—'}
              </td>
              <td style={{ padding: 8 }}>
                {tool.needsKey && editingKey === tool.id ? (
                  <span style={{ display: 'flex', gap: 8 }}>
                    <input
                      type="password"
                      placeholder="API key"
                      value={keyValue}
                      onChange={(e) => setKeyValue(e.target.value)}
                      style={{ width: 220 }}
                    />
                    <button type="button" onClick={() => handleSaveKey(tool.id)}>
                      Guardar
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingKey(null);
                        setKeyValue('');
                      }}
                    >
                      Cancelar
                    </button>
                  </span>
                ) : tool.needsKey ? (
                  <button type="button" onClick={() => setEditingKey(tool.id)}>
                    Configurar
                  </button>
                ) : (
                  <span style={{ color: '#999' }}>—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
