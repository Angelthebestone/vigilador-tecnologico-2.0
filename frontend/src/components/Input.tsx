import type { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className = '', id, ...rest }: InputProps) {
  const fieldId = id ?? rest.name;
  return (
    <label className="field" htmlFor={fieldId}>
      {label && <span className="field__label">{label}</span>}
      <input
        id={fieldId}
        className={`field__control ${className}`}
        aria-invalid={error ? true : undefined}
        {...rest}
      />
      {error && <span className="field__error">{error}</span>}
    </label>
  );
}
