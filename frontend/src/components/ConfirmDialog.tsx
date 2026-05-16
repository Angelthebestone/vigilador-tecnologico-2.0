import { Modal } from './Modal';
import { Button } from './Button';
import { Icon } from './Icon';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  variant = 'default',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Modal open={open} title={title} onClose={onCancel}>
      <div className="confirm-dialog">
        <p className="confirm-dialog__message">{message}</p>
        <div className="confirm-dialog__actions">
          <Button variant="ghost" className="btn--sm" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant="primary"
            className={`btn--sm ${variant === 'danger' ? 'btn--danger' : ''}`}
            onClick={onConfirm}
          >
            <Icon name={variant === 'danger' ? 'trash' : 'check'} size={14} />
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
