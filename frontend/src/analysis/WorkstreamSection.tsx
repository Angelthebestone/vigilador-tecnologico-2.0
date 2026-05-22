import { Icon } from '@/components';

type SectionStatus = 'active' | 'degraded' | 'inactive';


type IconName = React.ComponentProps<typeof Icon>['name'];

interface WorkstreamSectionProps {
  title: string;
  icon: IconName;
  status: SectionStatus;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

const STATUS_LABELS: Record<SectionStatus, string> = {
  active: 'Activo',
  degraded: 'Degradado',
  inactive: 'Inactivo',
};

const STATUS_CLASS: Record<SectionStatus, string> = {
  active: 'badge--success',
  degraded: 'badge--warning',
  inactive: 'badge--muted',
};

export function WorkstreamSection({
  title,
  icon,
  status,
  children,
  defaultOpen = true,
}: WorkstreamSectionProps) {
  return (
    <details className="ws-section" open={defaultOpen}>
      <summary className="ws-section__header">
        <span className="ws-section__icon">
          <Icon name={icon} size={16} />
        </span>
        <span className="ws-section__title">{title}</span>
        <span className={`badge ${STATUS_CLASS[status]}`}>
          {STATUS_LABELS[status]}
        </span>
      </summary>
      <div className="ws-section__body">{children}</div>
    </details>
  );
}
