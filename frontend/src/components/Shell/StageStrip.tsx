import type { RunResponse } from "../../api/types";
import styles from "./StageStrip.module.css";

interface Props {
  run: RunResponse | null;
  isRunning: boolean;
}

type StageState = "waiting" | "running" | "done";

const STAGES = [
  { key: "topic", label: "Topic" },
  { key: "design", label: "Design" },
  { key: "sim", label: "Robot" },
  { key: "uncertainty", label: "Uncertainty" },
] as const;

/** Per-stage progress (W1.4). Shows from the moment Run is pressed; each stage flips to
 *  done as its report lands from polling, and the next one shows as running. */
export function StageStrip({ run, isRunning }: Props) {
  // which reports have arrived
  const present: Record<string, boolean> = {
    topic: !!run?.topic,
    design: !!run?.design,
    sim: !!run?.sim,
    uncertainty: !!run?.uncertainty,
  };
  const doneAll = (run?.status ?? "") === "done" || present.uncertainty;

  const stateFor = (i: number): StageState => {
    const key = STAGES[i].key;
    if (present[key]) return "done";
    if (!isRunning && !doneAll) return "waiting";
    // first not-yet-present stage is the one running
    const firstPending = STAGES.findIndex((s) => !present[s.key]);
    if (isRunning && i === firstPending) return "running";
    return "waiting";
  };

  const word = (s: StageState) => (s === "done" ? "done" : s === "running" ? "running" : "waiting");

  return (
    <ol className={styles.strip} aria-label="Pipeline progress">
      {STAGES.map((stage, i) => {
        const st = stateFor(i);
        return (
          <li key={stage.key} className={`${styles.stage} ${styles[st]}`}>
            <span className={styles.numeral}>{i + 1}</span>
            <span className={styles.label}>{stage.label}</span>
            <span className={styles.state}>{word(st)}</span>
          </li>
        );
      })}
    </ol>
  );
}
