import { fmt } from "../format";
import { AXES, type Axis, type Source, type TopicReport, type Weights } from "../types";
import { Sourced } from "./Sourced";

const LABELS: Record<Axis, string> = {
  momentum: "Momentum",
  novelty: "Novelty",
  evidence: "Evidence",
  automatable: "Automatable",
  cost_time: "Cost & time",
};

/** Same formula as ViabilityMatrix.weighted_total in backend/contracts/topic_report.py. */
export function weightedTotal(axes: Record<Axis, number>, weights: Weights): number {
  const den = AXES.reduce((a, k) => a + (weights[k] ?? 0), 0);
  if (den <= 0) return 0;
  return AXES.reduce((a, k) => a + axes[k] * (weights[k] ?? 0), 0) / den;
}

export type AxisProvenance = Partial<Record<Axis, { source: Source[]; note?: string }>>;

interface Props {
  topic: TopicReport;
  axisSources: AxisProvenance;
  weights: Weights;
  onWeights: (w: Weights) => void;
}

export function ViabilityMatrix({ topic, axisSources, weights, onWeights }: Props) {
  const m = topic.matrix;
  const total = weightedTotal(m, weights);
  const wsum = AXES.reduce((a, k) => a + weights[k], 0) || 1;
  const isDefault = AXES.every((k) => weights[k] === m.weights[k]);

  return (
    <div className="card card--wide">
      <div className="card__head">
        <div>
          <p className="eyebrow">01 · Topic viability</p>
          <h2>Viability matrix</h2>
        </div>
        <div className="total">
          <span className="muted small">Weighted score</span>
          <Sourced className="total__value" derived="Weighted average of the five scores below, using your weights.">
            {fmt.num(total, 3)}
          </Sourced>
        </div>
      </div>

      <div className="matrix" role="table" aria-label="Viability criteria">
        <div className="matrix__row matrix__row--head" role="row">
          <span role="columnheader">Criterion</span>
          <span role="columnheader">Score</span>
          <span role="columnheader">Weight</span>
          <span role="columnheader" className="right">
            Adds
          </span>
        </div>
        {AXES.map((k) => {
          const score = m[k];
          const share = weights[k] / wsum;
          const id = `weight-${k}`;
          return (
            <div className="matrix__row" role="row" key={k}>
              <label htmlFor={id} role="rowheader" className="strong">
                {LABELS[k]}
              </label>
              <span className="bar-cell" role="cell">
                <span className="bar" aria-hidden="true">
                  <span className="bar__fill" style={{ width: `${score * 100}%` }} />
                </span>
                <Sourced source={axisSources[k]?.source} note={axisSources[k]?.note} className="mono">
                  {fmt.num(score)}
                </Sourced>
              </span>
              <span className="slider-cell" role="cell">
                <input
                  id={id}
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={weights[k]}
                  onChange={(e) => onWeights({ ...weights, [k]: Number(e.target.value) })}
                />
                <span className="mono muted small slider-cell__val">{Math.round(share * 100)}%</span>
              </span>
              <span className="mono right" role="cell">
                {fmt.num(score * share, 3)}
              </span>
            </div>
          );
        })}
      </div>

      <div className="card__foot">
        <button type="button" className="btn btn--ghost" disabled={isDefault} onClick={() => onWeights({ ...m.weights })}>
          Reset weights
        </button>
        {!topic.safety.pass && (
          <span className="flag">Blocked by safety gate: {topic.safety.reasons.join("; ") || "no reason given"}</span>
        )}
      </div>
    </div>
  );
}
