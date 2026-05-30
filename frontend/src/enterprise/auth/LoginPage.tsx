import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input } from '@/components';
import { login } from '../api/enterpriseClient';
import { useOnboardingStore } from '../state/onboardingStore';

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { companyProfile, currentStep } = useOnboardingStore();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      const incomplete = currentStep < 2 || !companyProfile;
      navigate(incomplete ? '/enterprise/onboarding' : '/enterprise/tools');
    } catch {
      setError('Credenciales inválidas');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 360, margin: '80px auto', padding: 24 }}>
      <h1>Vigilador Enterprise</h1>
      <form onSubmit={handleSubmit}>
        <Input label="Usuario" name="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        <Input label="Contraseña" name="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <p style={{ color: 'var(--color-error, red)' }}>{error}</p>}
        <Button variant="primary" type="submit" disabled={loading} style={{ marginTop: 12, width: '100%' }}>
          {loading ? 'Ingresando...' : 'Ingresar'}
        </Button>
      </form>
    </div>
  );
}
