import { useEffect } from 'react';
import { Badge, Spinner } from '@/components';
import { useToolsStore } from '../state/toolsStore';

const STATUS_TONE = { UP: 'success', DOWN: 'error', UNCONFIGURED: 'info' } as const;

export function ToolsListPage() {
  const { tools, loading, lastFetch, refresh } = useToolsStore();

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    const id = setInterval(refresh, 60_000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div style={{ maxWidth: 900, margin: '40px auto', padding: 24 }}>
      <h1>Herramientas</h1>
      {loading && <Spinner />}
      {lastFetch && <p style={{ fontSize: 12, color: '#888' }}>Último refresh: {new Date(lastFetch).toLocaleTimeString()}</p>}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 16 }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Nombre</th>
            <th style={{ textAlign: 'left' }}>Dominios</th>
            <th>Estado</th>
            <th>Último check</th>
          </tr>
        </thead>
        <tbody>
          {tools.map((t) => (
            <tr key={t.id} style={{ borderTop: '1px solid #eee' }}>
              <td>{t.id}</td>
              <td>{t.domains.join(', ')}</td>
              <td style={{ textAlign: 'center' }}>
                <Badge tone={STATUS_TONE[t.status as keyof typeof STATUS_TONE] ?? 'info'}>{t.status}</Badge>
              </td>
              <td style={{ textAlign: 'center', fontSize: 12 }}>{lastFetch ? new Date(lastFetch).toLocaleTimeString() : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!loading && tools.length === 0 && <p>No hay herramientas configuradas.</p>}
    </div>
  );
}
