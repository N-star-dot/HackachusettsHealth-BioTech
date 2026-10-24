import { useEffect, useMemo, useRef } from "react";
import { useReducedMotion } from "motion/react";
import { useReplay } from "../../hooks/useReplay";
import { leafSteps, runReplay } from "../../lib/replay";
import { plateAudit } from "../../lib/audit";
import { isReplayable } from "../../api/normalize";
import { DeckSvg } from "./DeckSvg";
import { uL } from "../../lib/format";
import type { ExperimentDesign, SimResult } from "../../api/types";
import styles from "./Replay.module.css";

interface Props {
  sim: SimResult;
  design: ExperimentDesign;
}

/** Replay of the Opentrons simulator run (BRIEF 5.10, V1). The animated deck is driven by
 *  the pure replay state machine; counters are read from that same state, so they match
 *  the simulator's cost at the end. Autoplays once at 16x when it first mounts. */
export function Replay({ sim, design }: Props) {
  const replayable = isReplayable(sim);
  const reduced = useReducedMotion() ?? false;
  const r = useReplay(sim.steps);

  const leaves = useMemo(() => leafSteps(sim.steps), [sim.steps]);
  const states = useMemo(
    () => (replayable ? runReplay(sim.steps, design.dilution.top_nM) : []),
    [sim.steps, design.dilution.top_nM, replayable],
  );

  // compound µL moved up to the current step: sum of aspirates from the compound well (D3/A2)
  const compoundMovedByStep = useMemo(() => {
    const acc: number[] = [0];
    let sum = 0;
    for (const s of leaves) {
      if (s.action === "aspirate" && (s.source?.slot ?? s.slot) === "D3" &&
          (s.source?.well ?? s.well) === "A2") {
        sum += s.uL ?? 0;
      }
      acc.push(sum);
    }
    return acc;
  }, [leaves]);

  // autoplay once at 16x on first mount of a replayable run
  const autoplayed = useRef(false);
  useEffect(() => {
    if (replayable && !reduced && !autoplayed.current) {
      autoplayed.current = true;
      r.setSpeed(16);
      r.play();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [replayable]);

  if (!replayable) {
    return (
      <div className={styles.wrap}>
        <p className={styles.caption}>
          Replay needs step details from the server, which this run did not produce
          (static check only). The deck layout is shown without a run.
        </p>
      </div>
    );
  }

  const idx = Math.min(r.index, states.length - 1);
  const state = states[idx] ?? states[0];
  const current = r.leaves[Math.min(r.index, r.leaves.length - 1)];
  const atEnd = r.status === "done" || r.index >= r.total;
  const audit = atEnd ? plateAudit(design, states[states.length - 1]) : [];

  const wellsFilled = Object.values(state.wells).filter((w) => w.volume_uL > 0.5).length;
  const compoundMoved = compoundMovedByStep[Math.min(r.index, compoundMovedByStep.length - 1)] ?? 0;

  return (
    <div className={styles.wrap}>
      <DeckSvg deck={sim.deck} state={state} step={current ?? null}
               ic50NM={design.prior_ic50.median_nM} reduced={reduced} />

      <dl className={styles.counters} aria-label="Replay counters">
        <div><dt>Tips</dt><dd>{state.tipsUsed}</dd></div>
        <div><dt>Compound</dt><dd>{uL(compoundMoved)}</dd></div>
        <div><dt>Wells filled</dt><dd>{wellsFilled}</dd></div>
        <div><dt>Pipetting step</dt><dd>{Math.min(r.index + 1, r.total)} of {r.total}</dd></div>
      </dl>

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
