import type { ReactNode } from 'react';

type Tone = 'success' | 'warning' | 'error' | 'info';

interface BadgeProps {
  tone: Tone;
  children: ReactNode;
  dot?: boolean;
}

export function Badge({ tone, children, dot = true }: BadgeProps) {
  return (
    <span className={`badge badge--${tone}`}>
      {dot && <span className="badge__dot" aria-hidden="true" />}
      {children}
    </span>
  );
}
