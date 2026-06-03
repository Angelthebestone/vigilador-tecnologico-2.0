// Spec 021 D4 / T116 — Chat surface (placeholder).
// MVP exit criteria: chat with mode selector + 2.0 workstream viewer + history.
// Real wiring lands when the dispatcher (T121) is wired in api/app.py.

import { useState } from 'react';

type ModeId = 'default' | 'CEO' | 'vigilancia-tech';

const MODES: { id: ModeId; label: string }[] = [
  { id: 'default', label: 'Asistente generalista' },
  { id: 'CEO', label: 'Director Ejecutivo' },
  { id: 'vigilancia-tech', label: 'Vigilancia tecnológica' },
];

export default function ChatPlaceholder() {
  const [mode, setMode] = useState<ModeId>('default');
  const [message, setMessage] = useState('');
  const [history, setHistory] = useState<Array<{ role: string; text: string }>>([]);

  const handleSend = () => {
    if (!message.trim()) return;
    // Wired against /api/v2/enterprise/chat in T121.
    setHistory((prev) => [
      ...prev,
      { role: 'user', text: message },
      {
        role: 'assistant',
        text: `[placeholder] mode=${mode}: real dispatcher wiring lands in T121.`,
      },
    ]);
    setMessage('');
  };

  return (
    <div style={{ padding: 24 }}>
      <h2>Chat — Vigilador 3.0 MVP</h2>
      <p style={{ color: '#666', fontSize: 14 }}>
        Selector de modo + visor de workstreams del 2.0. Sin login (D4).
      </p>

      <div style={{ marginBottom: 16 }}>
        <label htmlFor="mode-select" style={{ marginRight: 8 }}>
          Modo activo:
        </label>
        <select
          id="mode-select"
          value={mode}
          onChange={(e) => setMode(e.target.value as ModeId)}
        >
          {MODES.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      <div
        style={{
          border: '1px solid #ddd',
          padding: 12,
          minHeight: 200,
          background: '#fafafa',
          marginBottom: 12,
        }}
      >
        {history.length === 0 && (
          <div style={{ color: '#888' }}>Sin mensajes. Pruebe `/mode {mode}` arriba.</div>
        )}
        {history.map((entry, idx) => (
          <div key={idx} style={{ marginBottom: 8 }}>
            <strong>{entry.role}:</strong> {entry.text}
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          type="text"
          placeholder="Escriba un mensaje..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          style={{ flex: 1, padding: 8 }}
        />
        <button onClick={handleSend} type="button">
          Enviar
        </button>
      </div>
    </div>
  );
}
