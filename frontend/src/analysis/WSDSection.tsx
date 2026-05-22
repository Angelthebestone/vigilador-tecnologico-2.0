import type { WsdResult } from '@/types';
import { WorkstreamSection } from './WorkstreamSection';

interface WSDSectionProps {
  data: WsdResult;
}

export function WSDSection({ data }: WSDSectionProps) {
  return (
    <WorkstreamSection title="Señales estratégicas (WS-D)" icon="trending-up" status="active">
      {data.convergenceClusters.length > 0 && (
        <div className="ws-block">
          <h4>Convergence Clusters</h4>
          <ul className="ws-list">
            {data.convergenceClusters.map((c, i) => (
              <li key={i}>
                {c.domains.join(', ')}
                <span className={`badge badge--sm ${c.growthTrend === 'accelerating' ? 'badge--success' : 'badge--warning'}`}>
                  {c.growthTrend}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.ideaLineages.length > 0 && (
        <div className="ws-block">
          <h4>Idea Lineages</h4>
          {data.ideaLineages.map((l, i) => (
            <div key={i} className="ws-lineage">
              <span className="ws-lineage__seminal">{l.seminalTitle}</span>
              <span className="ws-lineage__arrow">→</span>
              <span className="ws-lineage__leaves">{l.leafWorks.length} leaf works</span>
            </div>
          ))}
        </div>
      )}

      {data.narrativeShifts.length > 0 && (
        <div className="ws-block">
          <h4>Narrative Shifts</h4>
          {data.narrativeShifts.map((n, i) => (
            <div key={i} className="ws-shift">
              <span>{n.topic}</span>
              <span>{n.sentimentPre.toFixed(2)} → {n.sentimentPost.toFixed(2)}</span>
              <span className={`badge badge--sm ${n.direction === 'positive' ? 'badge--success' : n.direction === 'negative' ? 'badge--danger' : 'badge--muted'}`}>
                {n.direction}
              </span>
            </div>
          ))}
        </div>
      )}

      {data.talentMobilities.length > 0 && (
        <div className="ws-block">
          <h4>Talent Mobility</h4>
          <div className="ws-badges">
            {data.talentMobilities.map((t, i) => (
              <span key={i} className="badge">
                {t.personName}: {t.fromAffiliation} → {t.toAffiliation} ({t.year})
              </span>
            ))}
          </div>
        </div>
      )}

      {data.patentingGaps.length > 0 && (
        <div className="ws-block">
          <h4>Patenting Gaps</h4>
          {data.patentingGaps.map((g, i) => (
            <span key={i} className={`badge ${g.classification === 'blue_ocean' ? 'badge--success' : 'badge--danger'}`}>
              {g.domain}: {g.classification}
            </span>
          ))}
        </div>
      )}
    </WorkstreamSection>
  );
}
