import { fmt } from "../format";
import type { ExperimentDesign, SimResult, Source } from "../types";
import { Sourced } from "./Sourced";

export function RunCost({ sim }: { sim: SimResult }) {
  const src: Source = { type: "simulator", id: `${sim.design_id} · opentrons ${sim.simulator.opentrons_version}` };
  const items: [string, string][] = [
    ["Tips", fmt.int(sim.cost.tips)],
    ["Compound", fmt.uL(sim.cost.compound_uL)],
    ["Plates", fmt.int(sim.cost.plates)],
    ["Robot steps", fmt.int(sim.cost.robot_steps)],
  ];
  return (
    <div className="card">
      <h3>Run cost</h3>
      <div className="cost">
        {items.map(([label, value]) => (
          <div key={label}>
            <span className="label">{label}</span>
            <Sourced source={src} className="mono cost__value">
              {value}
            </Sourced>
          </div>
        ))}
      </div>
      <p className="muted small">
        Protocol <span className="mono ink">{sim.protocol_file}</span> · simulated in{" "}
        <Sourced source={src} className="mono ink">
          {sim.simulator.seconds.toFixed(2)} s
        </Sourced>
      </p>
    </div>
  );
}

export function Evidence({ design }: { design: ExperimentDesign }) {
  const unverified = design.rationale.filter((r) => !r.verified).length;
  return (
    <div className="card">
      <div>
        <p className="eyebrow">04 · Evidence</p>
        <h3>Design rationale</h3>
      </div>
      {unverified > 0 && (
        <p className="small flag-text">
          {unverified} of {design.rationale.length} citation{design.rationale.length === 1 ? "" : "s"} not verified
        </p>
      )}
      {design.rationale.length === 0 && <p className="muted small">No literature claims in this design.</p>}
      <ul className="claims">
        {design.rationale.map((r, i) => (
          <li key={i} className={r.verified ? "claim" : "claim claim--unverified"}>
            <span className={`claim__status ${r.verified ? "ok" : "bad"}`}>
              {r.verified ? (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M3 7.5l2.5 2.5L11 4.5" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                  <path d="M3 12.5V1.5" />
                  <path d="M3 2h7.5l-1.5 3 1.5 3H3" />
                </svg>
              )}
              {r.verified ? "Verified" : "Unverified citation"}
            </span>
            <span>{r.claim}</span>
            <a className="mono small" href={`https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(r.pmid)}/`} target="_blank" rel="noreferrer">
              PMID {r.pmid}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
