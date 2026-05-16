import { useCallback, useRef, useState, type DragEvent } from 'react';
import { Icon } from './Icon';
import { Button } from './Button';
import { uploadDocument } from '@/api/endpoints';

interface FileUploadProps {
  onUploaded: (result: { markdown: string; format: string; filename: string }) => void;
  onCancel: () => void;
}

const ACCEPTED = [
  '.pdf', '.docx', '.pptx', '.xlsx', '.html',
  '.csv', '.json', '.xml', '.png', '.jpg', '.jpeg',
];

type UploadState = 'idle' | 'dragging' | 'uploading' | 'done' | 'error';

export function FileUpload({ onUploaded, onCancel }: FileUploadProps) {
  const [state, setState] = useState<UploadState>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [filename, setFilename] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setFilename(file.name);
      setState('uploading');
      setProgress(0);
      setError('');

      const tick = setInterval(() => {
        setProgress((p) => Math.min(p + 8, 90));
      }, 200);

      try {
        const result = await uploadDocument(file);
        clearInterval(tick);
        setProgress(100);
        setState('done');
        setTimeout(() => onUploaded(result), 400);
      } catch (err) {
        clearInterval(tick);
        setState('error');
        setError(err instanceof Error ? err.message : 'Error al subir el archivo');
      }
    },
    [onUploaded],
  );

  function onDragOver(e: DragEvent) {
    e.preventDefault();
    setState('dragging');
  }

  function onDragLeave(e: DragEvent) {
    e.preventDefault();
    setState('idle');
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onInputChange() {
    const file = inputRef.current?.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div
      className={`file-upload file-upload--${state}`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(',')}
        onChange={onInputChange}
        hidden
      />

      {state === 'uploading' && (
        <div className="file-upload__progress">
          <div className="file-upload__progress-icon">
            <Icon name="upload" size={24} />
          </div>
          <span className="file-upload__filename">{filename}</span>
          <div className="file-upload__bar">
            <div
              className="file-upload__bar-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="file-upload__percent">{progress}%</span>
        </div>
      )}

      {state === 'done' && (
        <div className="file-upload__done">
          <div className="file-upload__done-icon">
            <Icon name="check" size={24} />
          </div>
          <span className="file-upload__filename">{filename}</span>
          <span className="file-upload__status-text">Conversión completa</span>
        </div>
      )}

      {state === 'error' && (
        <div className="file-upload__error">
          <Icon name="close" size={20} />
          <span className="file-upload__error-msg">{error}</span>
          <Button variant="ghost" className="btn--sm" onClick={() => setState('idle')}>
            Reintentar
          </Button>
        </div>
      )}

      {(state === 'idle' || state === 'dragging') && (
        <div className="file-upload__dropzone">
          <div className="file-upload__drop-icon">
            <Icon name={state === 'dragging' ? 'upload' : 'file'} size={28} />
          </div>
          <p className="file-upload__drop-text">
            {state === 'dragging'
              ? 'Suelte el archivo aquí'
              : 'Arrastre un archivo o haga clic para seleccionar'}
          </p>
          <p className="file-upload__drop-hint">
            PDF, DOCX, PPTX, XLSX, HTML, CSV, JSON, XML, PNG, JPG
          </p>
          <div className="file-upload__drop-actions">
            <Button
              variant="primary"
              className="btn--sm"
              onClick={() => inputRef.current?.click()}
            >
              <Icon name="paperclip" size={14} />
              Seleccionar archivo
            </Button>
            <Button variant="ghost" className="btn--sm" onClick={onCancel}>
              Cancelar
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
