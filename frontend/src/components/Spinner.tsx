interface SpinnerProps {
  size?: 'md' | 'lg';
  label?: string;
}

export function Spinner({ size = 'md', label = 'Cargando' }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-live="polite"
      aria-label={label}
      className={size === 'lg' ? 'spinner spinner--lg' : 'spinner'}
    />
  );
}
