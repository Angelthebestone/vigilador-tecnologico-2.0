import type { WsbResult } from '@/types';
import { WorkstreamSection } from './WorkstreamSection';

interface WSBSectionProps {
  data: WsbResult;
}

export function WSBSection({ data }: WSBSectionProps) {
  return (
    <WorkstreamSection title="Data Intelligence (WS-B)" icon="database" status="active">
      {data.hybridSearchStats && Object.keys(data.hybridSearchStats).length > 0 && (
        <div className="ws-block">
          <h4>Hybrid Search Stats</h4>
          <div className="ws-cards">
            {Object.entries(data.hybridSearchStats).map(([k, v]) => (
              <div key={k} className="ws-card">
                <div className="ws-card__num">{v}</div>
                <div className="ws-card__label">{k}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="ws-block">
        <h4>Dedup Rate</h4>
        <div className="ws-meter">
          <span className="ws-meter__label">{Math.round(data.dedupRate * 100)}% duplicates removed</span>
          <div className="ws-meter__bar">
            <div className="ws-meter__fill" style={{ width: `${Math.round(data.dedupRate * 100)}%` }} />
          </div>
        </div>
      </div>

      {data.dedupedSources.length > 0 && (
        <div className="ws-block">
          <h4>Deduped Sources</h4>
          <ul className="ws-list">
            {data.dedupedSources.map((s, i) => (
              <li key={i}>{s.title} <span className="text-muted">({s.provider})</span></li>
            ))}
          </ul>
        </div>
      )}

      {data.authenticitySignals.length > 0 && (
        <div className="ws-block">
          <h4>Authenticity Signals</h4>
          <div className="ws-badges">
            {data.authenticitySignals.map((s, i) => (
              <span key={i} className={`badge ${s.verdict === 'likely_ai' ? 'badge--warning' : 'badge--success'}`}>
                {s.verdict} (AI: {Math.round(s.aiProbability * 100)}%)
              </span>
            ))}
          </div>
        </div>
      )}

      {data.consensusDisputes.length > 0 && (
        <div className="ws-block">
          <h4>Consensus / Disputes</h4>
          <ul className="ws-list">
            {data.consensusDisputes.map((c, i) => (
              <li key={i}>
                <span className={`badge badge--sm ${c.agreement ? 'badge--success' : 'badge--danger'}`}>
                  {c.agreement ? 'Consensus' : 'Dispute'}
                </span>
                {' '}{c.topic} ({c.sourceCount} sources, conf: {Math.round(c.confidence * 100)}%)
              </li>
            ))}
          </ul>
        </div>
      )}
    </WorkstreamSection>
  );
}
