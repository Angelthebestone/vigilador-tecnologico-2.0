import { useState } from 'react';
import { Button } from '@/components';

export interface ClarificationQuestion {
  id: string;
  text: string;
}

interface ClarificationInputProps {
  questions: ClarificationQuestion[];
  answered?: boolean;
  onSubmit: (answers: Record<string, string>) => void;
}

export function ClarificationInput({
  questions,
  answered = false,
  onSubmit,
}: ClarificationInputProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const allFilled = questions.every((q) => (answers[q.id] ?? '').trim() !== '');

  function handleSubmit() {
    if (!allFilled || answered) return;
    onSubmit(answers);
  }

  return (
    <div className={`clarify ${answered ? 'clarify--done' : ''}`}>
      <div className="clarify__head">
        Precisión del alcance
        <span className="badge badge--info">
          <span className="badge__dot" aria-hidden="true" />
          {questions.length} ítems
        </span>
      </div>
      <div className="clarify__list">
        {questions.map((q, i) => (
          <div className="clarify__q" key={q.id}>
            <span className="clarify__q-text">
              <span className="clarify__q-num">
                {String(i + 1).padStart(2, '0')}
              </span>
              {q.text}
            </span>
            <input
              className="field__control"
              value={answers[q.id] ?? ''}
              disabled={answered}
              placeholder="Su respuesta…"
              onChange={(e) =>
                setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
              }
              onKeyDown={(e) => {
                if (e.key === 'Enter' && allFilled) handleSubmit();
              }}
            />
          </div>
        ))}
      </div>
      {!answered && (
        <div className="clarify__foot">
          <Button
            variant="primary"
            size="sm"
            disabled={!allFilled}
            onClick={handleSubmit}
          >
            Confirmar alcance
          </Button>
        </div>
      )}
    </div>
  );
}
