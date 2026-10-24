import { useState } from "react";
import { Num } from "../Num/Num";
import { src, assumed } from "../Num/provenance";
import { simOk, costIsCounted } from "../../api/normalize";
import { uL } from "../../lib/format";
import type { SimResult } from "../../api/types";
import styles from "./RobotSection.module.css";

interface Props {
  sim: SimResult;
}

export function RobotSection({ sim }: Props) {
  const [showLog, setShowLog] = useState(false);
  const ok = simOk(sim);
  const staticOnly = sim.simulator.opentrons_version.includes("not installed");
  const simSource = sim.cost.source ?? { type: "assumed", id: "cost-formula" };
  const counted = costIsCounted(sim);
  const costProv = counted
    ? src(simSource, "Counted from the simulator run log.")
    : assumed("Estimated by formula, not counted from the simulator.");

  return (
    <section className={styles.section}>
      <div className={styles.head}>
        <span className={styles.numeral}>3</span>
        <h2 className={styles.name}>
          {ok ? "Passed the Opentrons simulator" : "Did not pass the Opentrons simulator"}
        </h2>
      </div>

      {ok ? (
        <p className={styles.verdict}>
          <Num value={`${sim.simulator.seconds}s`} provenance={src({ type: "simulator", id: sim.protocol_file })} />
          , {sim.simulator.log_lines} log lines, Opentrons {sim.simulator.opentrons_version}.
          {staticOnly && (
            <span className={styles.warn}> Static check only. The Opentrons package isn't
              installed on the server, so the protocol wasn't simulated.</span>
          )}
        </p>
      ) : (
        <div className={styles.fail}>
          <pre className={styles.error}>{sim.simulator.error}</pre>
          <p>The protocol comes from a fixed template, so this is a backend bug to report,
            not something to edit by hand.</p>
        </div>
      )}

      <ul className={styles.cost}>
        <li>Tips: <Num value={String(sim.cost.tips)} provenance={costProv} /></li>
        <li>Compound: <Num value={uL(sim.cost.compound_uL)} provenance={costProv} /></li>
        <li>Plates: <Num value={String(sim.cost.plates)} provenance={costProv} /></li>
        <li>Robot steps: <Num value={String(sim.cost.robot_steps)} provenance={costProv} /></li>
      </ul>

      {sim.steps.length > 0 && (
        <div>
          <button className={styles.toggle} onClick={() => setShowLog((v) => !v)}>
            {showLog ? "Hide run log" : `Show run log (${sim.steps.length} steps)`}
          </button>
          {showLog && (
            <ol className={styles.log}>
              {sim.steps.map((s) => (
                <li key={s.i}>{s.text || s.action}</li>
              ))}
            </ol>
          )}
        </div>
      )}
      <p className={styles.caption}>Generated from a fixed template. No model-written code runs.</p>
    </section>
  );
}
