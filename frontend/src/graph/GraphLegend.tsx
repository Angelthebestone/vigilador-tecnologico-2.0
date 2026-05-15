import type { BranchType } from '@/types';
import { getBranchColor, getBranchLabel } from './graphUtils';

const BRANCHES: BranchType[] = [
  'AVANCES',
  'COMERCIAL',
  'RIESGO',
  'PI_NORMATIVA',
  'COMPETITIVO',
  'OPORTUNIDADES',
];

export function GraphLegend() {
  return (
    <figure className="glegend">
      <figcaption className="glegend__head">Cartela · ramas de origen</figcaption>
      <div className="glegend__body">
        {BRANCHES.map((branch) => (
          <div className="glegend__row" key={branch}>
            <span
              className="glegend__swatch"
              style={{ background: getBranchColor(branch) }}
              aria-hidden="true"
            />
            {getBranchLabel(branch)}
          </div>
        ))}
      </div>
      <div className="glegend__scale">
        <span
          className="glegend__dot"
          style={{ width: 7, height: 7 }}
          aria-hidden="true"
        />
        <span
          className="glegend__dot"
          style={{ width: 13, height: 13 }}
          aria-hidden="true"
        />
        <span
          className="glegend__dot"
          style={{ width: 19, height: 19 }}
          aria-hidden="true"
        />
        <span style={{ marginLeft: 4 }}>menor → mayor centralidad</span>
      </div>
    </figure>
  );
}
