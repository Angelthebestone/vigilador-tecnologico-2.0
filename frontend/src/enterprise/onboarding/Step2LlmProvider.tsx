import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input } from '@/components';
import { testLlm } from '../api/enterpriseClient';
import { useOnboardingStore } from '../state/onboardingStore';

export function Step2LlmProvider() {
  const { saveStep2 } = useOnboardingStore();
  const navigate = useNavigate();
  const [provider, setProvider] = useState('xiaomimimo');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [testResult, setTestResult] = useState<{ model?: string; latencyMs?: number; error?: string } | null>(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testLlm(provider);
      setTestResult(res);
    } catch {
      setTestResult({ error: 'Error de conectividad' });
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!apiKey) { setError('API Key requerida'); return; }
    setError('');
    setSaving(true);
    try {
      await saveStep2(provider, apiKey, testResult?.model);
      navigate('/enterprise/tools');
    } catch {
      setError('Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 420 }}>
      <h2>Paso 2: Proveedor LLM</h2>
      <label className="field">
        <span className="field__label">Proveedor</span>
        <select className="field__control" value={provider} onChange={(e) => setProvider(e.target.value)}>
          <option value="xiaomimimo">Xiaomimimo</option>
          <option value="minimax">Minimax</option>
        </select>
      </label>
      <div style={{ position: 'relative' }}>
        <Input
          label="API Key"
          name="apiKey"
          type={showKey ? 'text' : 'password'}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          required
        />
        <button
          type="button"
          onClick={() => setShowKey(!showKey)}
          style={{ position: 'absolute', right: 8, top: 28, background: 'none', border: 'none', cursor: 'pointer' }}
        >
          {showKey ? 'Ocultar' : 'Mostrar'}
        </button>
      </div>
      <Button type="button" onClick={handleTest} disabled={testing} style={{ marginTop: 8 }}>
        {testing ? 'Probando...' : 'Probar conectividad'}
      </Button>
      {testResult && (
        <p style={{ marginTop: 8 }}>
          {testResult.error
            ? <span style={{ color: 'red' }}>{testResult.error}</span>
            : <>Modelo: <strong>{testResult.model}</strong> — Latencia: {testResult.latencyMs}ms</>}
        </p>
      )}
      {error && <p style={{ color: 'var(--color-error, red)' }}>{error}</p>}
      <Button variant="primary" type="submit" disabled={saving} style={{ marginTop: 12 }}>
        {saving ? 'Guardando...' : 'Guardar y continuar'}
      </Button>
    </form>
  );
}
