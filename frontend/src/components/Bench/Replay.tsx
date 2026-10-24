import { useMemo } from "react";
import { useReplay } from "../../hooks/useReplay";
import { runReplay } from "../../lib/replay";
import { plateAudit } from "../../lib/audit";
import { isReplayable } from "../../api/normalize";
import type { ExperimentDesign, SimResult } from "../../api/types";
import styles from "./Replay.module.css";

interface Props {
  sim: SimResult;
  design: ExperimentDesign;
}

/** Replay of the Opentrons simulator run (BRIEF 5.10). No physical robot. When steps lack
 *  structure, Play is disabled with the reason. The plate audit appears at the end. */
export function Replay({ sim, design }: Props) {
  const replayable = isReplayable(sim);
  const r = useReplay(sim.steps);
  const states = useMemo(
    () => (replayable ? runReplay(sim.steps, design.dilution.top_nM) : []),
    [sim.steps, design.dilution.top_nM, replayable],
  );

  if (!replayable) {
    return (
      <div className={styles.wrap}>
        <button className={styles.play} disabled>Replay robot run</button>
        <p className={styles.caption}>
          Replay needs step details from the server (backend item B0.4).
        </p>
      </div>
    );
  }

  const current = r.leaves[Math.min(r.index, r.leaves.length - 1)];
  const atEnd = r.status === "done" || r.index >= r.total;
  const audit = atEnd ? plateAudit(design, states[states.length - 1]) : [];

  return (
    <div className={styles.wrap}>
      <div className={styles.controls}>
        {r.status === "playing" ? (
          <button className={styles.play} onClick={r.pause}>Pause</button>
        ) : (
          <button className={styles.play} onClick={r.play}>Play</button>
        )}
        {[1, 4, 16].map((s) => (
          <button key={s}
            className={`${styles.speed} ${r.speed === s ? styles.active : ""}`}
            onClick={() => r.setSpeed(s)}>{s}x</button>
        ))}
        <button className={styles.speed} onClick={r.skipToEnd}>Skip to end</button>
      </div>
      <input type="range" min={0} max={r.total} value={Math.min(r.index, r.total)}
             className={styles.scrubber} aria-label="Replay position"
             onChange={(e) => r.stepBy(Number(e.target.value) - r.index)} />
      <p className={styles.step}>Step {Math.min(r.index + 1, r.total)} of {r.total}</p>
      <p className={styles.line}>{current?.text || current?.action || ""}</p>
      <p className={styles.caption}>Replay of the Opentrons simulator run. No physical robot was used.</p>

      {atEnd && (
        <div className={styles.audit}>
          {audit.length === 0 ? (
            <p className={styles.clean}>Every well ends as planned.</p>
          ) : (
            <ul>{audit.map((a, i) => <li key={i}>{a}</li>)}</ul>
          )}
        </div>
      )}
    </div>
  );
}
