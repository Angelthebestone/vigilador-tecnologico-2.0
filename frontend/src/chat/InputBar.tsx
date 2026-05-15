import { useRef, useState, type KeyboardEvent } from 'react';
import { Button, Icon } from '@/components';

interface InputBarProps {
  disabled?: boolean;
  placeholder?: string;
  onSend: (text: string) => void;
}

export function InputBar({
  disabled = false,
  placeholder = 'Formule una consulta de vigilancia tecnológica…',
  onSend,
}: InputBarProps) {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  function autoGrow() {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  function submit() {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
    if (ref.current) ref.current.style.height = 'auto';
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="inputbar">
      <div className="inputbar__row">
        <div className="inputbar__field">
          <textarea
            ref={ref}
            className="inputbar__textarea"
            value={value}
            disabled={disabled}
            placeholder={placeholder}
            rows={1}
            aria-label="Mensaje"
            onChange={(e) => {
              setValue(e.target.value);
              autoGrow();
            }}
            onKeyDown={onKeyDown}
          />
        </div>
        <Button
          variant="primary"
          className="inputbar__send"
          disabled={disabled || value.trim() === ''}
          onClick={submit}
          aria-label="Enviar"
        >
          <Icon name="send" size={18} />
        </Button>
      </div>
      <span className="inputbar__hint">
        {disabled
          ? 'Investigación en curso — entrada en pausa'
          : 'Enter envía · Shift+Enter salto de línea'}
      </span>
    </div>
  );
}
