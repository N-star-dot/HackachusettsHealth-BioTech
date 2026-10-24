import { fmt, simulated } from "../format";
import type { ExperimentDesign, Source, UncertaintyReport } from "../types";
import { Sourced } from "./Sourced";

interface Lever {
  id: string;
  label: string;
  min: number;
  max: number;
  step: number;
  get: (d: ExperimentDesign) => number;
  set: (d: ExperimentDesign, v: number) => ExperimentDesign;
  show: (v: number) => string;
}

const LEVERS: Lever[] = [
  {
    id: "replicates",
    label: "Replicates",
    min: 1,
    max: 6,
    step: 1,
    get: (d) => d.replicates,
    set: (d, v) => ({ ...d, replicates: v }),
    show: (v) => `${v}×`,
  },
  {
    id: "points",
    label: "Dilution points",
    min: 4,
    max: 16,
    step: 1,
    get: (d) => d.dilution.points,
    set: (d, v) => ({ ...d, dilution: { ...d.dilution, points: v } }),
    show: (v) => String(v),
  },
  {
    id: "factor",
    label: "Dilution factor",
    min: 1.5,
    max: 5,
    step: 0.5,
    get: (d) => d.dilution.factor,
    set: (d, v) => ({ ...d, dilution: { ...d.dilution, factor: v } }),
    show: (v) => `${v}×`,
  },
  {
    id: "transfer",
    label: "Transfer volume",
    min: 1,
    max: 200,
    step: 1,
    get: (d) => d.volumes_uL.transfer,
    set: (d, v) => ({ ...d, volumes_uL: { ...d.volumes_uL, transfer: v } }),
    show: (v) => fmt.uL(v),
  },
];

interface Props {
  design: ExperimentDesign;
  baseline: ExperimentDesign;
  report: UncertaintyReport;
  live: boolean;
  pending: boolean;
  error: string | null;
  onDesign: (d: ExperimentDesign) => void;
}

export function WhatIf({ design, baseline, report, live, pending, error, onDesign }: Props) {
  const sim = simulated(report.seed, report.runs);
  const noiseBy = (type: Source["type"]) => report.noise.sources.filter((s) => s.type === type);
  const fe = report.fold_error;
  const scaleMax = Math.max(2, Math.ceil(fe.p90 * 1.25 * 2) / 2);
  const pos = (v: number) => `${((v - 1) / (scaleMax - 1)) * 100}%`;
  const bottom = design.dilution.top_nM / design.dilution.factor ** (design.dilution.points - 1);
  const changed = LEVERS.some((l) => l.get(design) !== l.get(baseline));
  const transferWarn = design.volumes_uL.transfer < 1;

  return (
    <section className="card">
      <div className="card__head">
        <div>
          <p className="eyebrow">02 · Design and uncertainty</p>
          <h2>What-if: dose-response design</h2>
        </div>
        <span className="chip chip--sim">
          Simulated · {report.runs.toLocaleString("en-US")} runs · seed {report.seed}
        </span>
      </div>

      {!live && changed && (
        <p className="notice">
          Fold error below is from the mock file. Switch to <strong>Live API</strong> to recompute it as you move the
          sliders.
        </p>
      )}
      {error && <p className="notice notice--error">{error}</p>}

      <div className="split">
        <div className="split__main levers">
          {LEVERS.map((l) => {
            const v = l.get(design);
            return (
              <div className="lever" key={l.id}>
                <div className="lever__top">
                  <label htmlFor={`lever-${l.id}`} className="strong">
                    {l.label}
                  </label>
                  <span className="mono">
                    {l.show(v)}
                    {v !== l.get(baseline) && <span className="muted small"> (was {l.show(l.get(baseline))})</span>}
                  </span>
                </div>
                <input
                  id={`lever-${l.id}`}
                  type="range"
                  min={l.min}
                  max={l.max}
                  step={l.step}
                  value={v}
                  onChange={(e) => onDesign(l.set(design, Number(e.target.value)))}
                />
              </div>
            );
          })}
          <div className="lever__actions">
            <button type="button" className="btn btn--ghost" disabled={!changed} onClick={() => onDesign(baseline)}>
              Reset design
            </button>
            {transferWarn && <span className="flag">Transfers under 1 µL: robot error rivals biology here.</span>}
          </div>
          <p className="muted small">
            Prior IC50{" "}
            <Sourced
              source={design.prior_ic50.source}
              note={`${design.prior_ic50.n_measurements} measurements`}
              className="mono ink"
            >
              {fmt.nM(design.prior_ic50.median_nM)}
            </Sourced>{" "}
            · spread{" "}
            <Sourced source={design.prior_ic50.source} className="mono ink">
              {fmt.num(design.prior_ic50.spread_log10)} log10
            </Sourced>{" "}
            · range <span className="mono ink">{fmt.nM(bottom)}</span> to{" "}
            <span className="mono ink">{fmt.nM(design.dilution.top_nM)}</span>
          </p>
        </div>

        <div className={`split__side${pending ? " is-pending" : ""}`} aria-busy={pending}>
          <div className="tiles">
            <div className="tile">
              <span className="label">Fold error · median</span>
              <Sourced source={sim} className="mono tile__value">
                {fmt.fold(fe.median)}
              </Sourced>
            </div>
            <div className="tile">
              <span className="label">Fold error · p90</span>
              <Sourced source={sim} className="mono tile__value accent">
                {fmt.fold(fe.p90)}
              </Sourced>
            </div>
            <div className="tile">
              <span className="label">90% coverage</span>
              <Sourced
                source={sim}
                note={`Calibrated against ${report.calibration.pairs} held-out ChEMBL pairs; near 0.90 is well calibrated.`}
                className="mono tile__value"
              >
                {fmt.num(report.calibration.coverage_90)}
              </Sourced>
            </div>
          </div>

          <div className="range">
            <span className="label">Fold error across simulated runs</span>
            <div className="range__track" role="img" aria-label={`Median ${fmt.fold(fe.median)}, p90 ${fmt.fold(fe.p90)}`}>
              <span className="range__band" style={{ width: pos(fe.p90) }} />
              <span className="range__tick range__tick--median" style={{ left: pos(fe.median) }} />
              <span className="range__tick range__tick--p90" style={{ left: pos(fe.p90) }} />
            </div>
            <div className="range__axis mono muted small">
              <span>1.0×</span>
              <span>{fmt.fold((1 + scaleMax) / 2)}</span>
              <span>{fmt.fold(scaleMax)}</span>
            </div>
            <div className="legend small muted">
              <span>
                <i className="swatch swatch--ink" /> median
              </span>
              <span>
                <i className="swatch swatch--accent" /> p90
              </span>
            </div>
          </div>

          <div className="facts small muted">
            <span>
              Outside range{" "}
              <Sourced source={sim} className="mono ink">
                {fmt.pct(report.outside_range_share)}
              </Sourced>
            </span>
            <span>
              Failed fits{" "}
              <Sourced source={sim} className="mono ink">
                {fmt.pct(report.failed_fit_share)}
              </Sourced>
            </span>
            <span>
              Lab spread{" "}
              <Sourced source={noiseBy("paper")} className="mono ink">
                {fmt.num(report.noise.lab_spread_log10)} log10
              </Sourced>
            </span>
            <span>
              Pipette CV{" "}
              <Sourced source={noiseBy("spec")} className="mono ink">
                {fmt.pct(report.noise.pipette_cv)}
              </Sourced>
            </span>
            <span>
              Pipette bias{" "}
              <Sourced source={noiseBy("spec")} className="mono ink">
                {fmt.pct(report.noise.pipette_bias)}
              </Sourced>
            </span>
            <span>
              Reader CV{" "}
              <Sourced derived="Set by the user; default 5%." className="mono ink">
                {fmt.pct(report.noise.reader_cv, 0)}
              </Sourced>
            </span>
          </div>
        </div>
      </div>

      {report.next_experiments.length > 0 && (
        <div className="next">
          <h3>Suggested next experiments</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Change</th>
                  <th className="right">p90 drop</th>
                  <th className="right">Extra tips</th>
                  <th className="right">Extra compound</th>
                  <th className="right">Extra plates</th>
                  <th className="right">Score</th>
                </tr>
              </thead>
              <tbody>
                {[...report.next_experiments]
                  .sort((a, b) => b.score - a.score)
                  .map((n) => (
                    <tr key={n.change}>
                      <td>{n.change}</td>
                      <td className="right mono">
                        <Sourced source={sim}>−{n.p90_fold_error_drop_pct}%</Sourced>
                      </td>
                      <td className="right mono">+{n.extra_tips}</td>
                      <td className="right mono">{fmt.uL(n.extra_compound_uL)}</td>
                      <td className="right mono">+{n.extra_plates}</td>
                      <td className="right mono strong">
                        <Sourced derived="Fold-error reduction per unit cost; higher ranks first.">{fmt.num(n.score, 1)}</Sourced>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
