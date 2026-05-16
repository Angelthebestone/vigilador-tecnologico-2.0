import { useRef, useState, type KeyboardEvent } from 'react';
import { Button, Icon } from '@/components';
import { FileUpload } from '@/components/FileUpload';
import { CollapsibleSection } from '@/components/CollapsibleSection';

interface InputBarProps {
  disabled?: boolean;
  placeholder?: string;
  /** La sesión ya tiene reporte: el input responde preguntas de seguimiento. */
  conversationMode?: boolean;
  onSend: (text: string) => void;
}

export function InputBar({
  disabled = false,
  placeholder,
  conversationMode = false,
  onSend,
}: InputBarProps) {
  const resolvedPlaceholder =
    placeholder ??
    (conversationMode
      ? 'Pregunte sobre los hallazgos de esta investigación…'
      : 'Formule una consulta de vigilancia tecnológica…');
  const [value, setValue] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<{
    markdown: string;
    format: string;
    filename: string;
  } | null>(null);
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
    if (uploadedFile) {
      onSend(
        `[Documento adjunto: ${uploadedFile.filename}]\n\n${uploadedFile.markdown}\n\n---\n\n${text}`,
      );
      setUploadedFile(null);
    } else {
      onSend(text);
    }
    setValue('');
    if (ref.current) ref.current.style.height = 'auto';
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function handleUploaded(result: {
    markdown: string;
    format: string;
    filename: string;
  }) {
    setUploadedFile(result);
    setShowUpload(false);
  }

  return (
    <div className="inputbar">
      {showUpload && (
        <div className="inputbar__upload-area">
          <FileUpload
            onUploaded={handleUploaded}
            onCancel={() => setShowUpload(false)}
          />
        </div>
      )}

      {uploadedFile && !showUpload && (
        <div className="inputbar__attached">
          <Icon name="file" size={14} />
          <span className="inputbar__attached-name">{uploadedFile.filename}</span>
          <button
            type="button"
            className="inputbar__attached-remove"
            onClick={() => setUploadedFile(null)}
            aria-label="Quitar archivo"
          >
            <Icon name="close" size={12} />
          </button>
          <CollapsibleSection
            summary={`Vista previa — ${uploadedFile.format.toUpperCase()}`}
            marker="§ DOC"
          >
            <pre className="inputbar__preview-md">
              {uploadedFile.markdown.slice(0, 800)}
              {uploadedFile.markdown.length > 800 && '…'}
            </pre>
          </CollapsibleSection>
        </div>
      )}

      <div className="inputbar__row">
        <button
          type="button"
          className="inputbar__attach"
          disabled={disabled}
          onClick={() => setShowUpload((v) => !v)}
          aria-label="Adjuntar archivo"
        >
          <Icon name="paperclip" size={18} />
        </button>
        <div className="inputbar__field">
          <textarea
            ref={ref}
            className="inputbar__textarea"
            value={value}
            disabled={disabled}
            placeholder={resolvedPlaceholder}
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
          disabled={disabled || (value.trim() === '' && !uploadedFile)}
          onClick={submit}
          aria-label="Enviar"
        >
          <Icon name="send" size={18} />
        </Button>
      </div>
      <span className="inputbar__hint">
        {disabled
          ? conversationMode
            ? 'Consultando los hallazgos…'
            : 'Investigación en curso — entrada en pausa'
          : conversationMode
            ? 'Modo conversación · pregunte sobre los hallazgos sin reabrir la investigación'
            : 'Enter envía · Shift+Enter salto de línea · 📎 adjuntar documento'}
      </span>
    </div>
  );
}
