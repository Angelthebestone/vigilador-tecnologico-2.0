import { useState, type FormEvent } from 'react';
import { z } from 'zod';
import { Button, Input } from '@/components';
import { useOnboardingStore } from '../state/onboardingStore';

const schema = z.object({
  name: z.string().min(2, 'Nombre requerido (mín. 2 caracteres)'),
});

const SECTORS = ['Tecnología', 'Salud', 'Educación', 'Finanzas', 'Gobierno', 'Otro'];
const TIMEZONES = ['America/Bogota', 'America/Mexico_City', 'America/Lima', 'America/Santiago', 'America/Buenos_Aires', 'UTC'];

export function Step1Company() {
  const { saveStep1, companyProfile } = useOnboardingStore();
  const [form, setForm] = useState({
    name: companyProfile?.name ?? '',
    sector: companyProfile?.sector ?? '',
    country: companyProfile?.country ?? '',
    department: companyProfile?.department ?? '',
    municipality: companyProfile?.municipality ?? '',
    timezone: companyProfile?.timezone ?? '',
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const result = schema.safeParse(form);
    if (!result.success) { setError(result.error.issues[0]?.message ?? 'Datos inválidos'); return; }
    setError('');
    setSaving(true);
    try {
      await saveStep1(form);
    } catch {
      setError('Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 420 }}>
      <h2>Paso 1: Empresa</h2>
      <Input label="Nombre *" name="name" value={form.name} onChange={set('name')} required />
      <label className="field">
        <span className="field__label">Sector</span>
        <select className="field__control" value={form.sector} onChange={set('sector')}>
          <option value="">-- Seleccionar --</option>
          {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
      <Input label="País" name="country" value={form.country} onChange={set('country')} />
      <Input label="Departamento" name="department" value={form.department} onChange={set('department')} />
      <Input label="Municipio" name="municipality" value={form.municipality} onChange={set('municipality')} />
      <label className="field">
        <span className="field__label">Zona horaria</span>
        <select className="field__control" value={form.timezone} onChange={set('timezone')}>
          <option value="">-- Seleccionar --</option>
          {TIMEZONES.map((tz) => <option key={tz} value={tz}>{tz}</option>)}
        </select>
      </label>
      {error && <p style={{ color: 'var(--color-error, red)' }}>{error}</p>}
      <Button variant="primary" type="submit" disabled={saving} style={{ marginTop: 12 }}>
        {saving ? 'Guardando...' : 'Siguiente'}
      </Button>
    </form>
  );
}
