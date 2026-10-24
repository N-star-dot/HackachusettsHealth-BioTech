import { plannedLayout, ROWS, COLS, type PlannedWell } from "../../lib/plate";
import { activity, activityColor } from "../../lib/hill";
import { nM, pct } from "../../lib/format";
import type { ExperimentDesign } from "../../api/types";
import styles from "./PlateMap.module.css";

interface Props {
  design: ExperimentDesign;
}

/** Planned 96-well layout (BRIEF 5.7). Each dilution well is filled with the expected
 *  activity at the starting guess on the resazurin ramp. */
export function PlateMap({ design }: Props) {
  const layout = plannedLayout(design);
  const ic50 = design.prior_ic50.median_nM;

  const fill = (w: PlannedWell): string => {
    if (w.kind === "dilution" && w.concNM != null) return activityColor(activity(w.concNM, ic50));
    if (w.kind === "positive" && w.concNM != null) return activityColor(activity(w.concNM, ic50));
    if (w.kind === "negative") return "var(--sheet)";
    return "transparent";
  };

  const title = (w: PlannedWell): string => {
    if (w.kind === "dilution" && w.concNM != null) {
      const a = activity(w.concNM, ic50);
      return `${w.id}: ${nM(w.concNM)}, replicate ${w.replicate}. Expected ${pct(a / 100)} activity at the starting guess (Hill slope 1 assumed).`;
    }
    if (w.kind === "negative") return `${w.id}: negative control (diluent only)`;
    if (w.kind === "positive") return `${w.id}: positive control (compound stock)`;
    return w.id;
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.label}>Planned layout</div>
      <div className={styles.grid} role="img" aria-label="Planned 96-well plate layout">
        <div className={styles.corner} />
        {COLS.map((c) => <div key={`c${c}`} className={styles.colHead}>{c}</div>)}
        {ROWS.map((rowLabel, r) => [
          <div key={`h${rowLabel}`} className={styles.rowHead}>{rowLabel}</div>,
          ...COLS.map((_, c) => {
            const w = layout.wells[r * 12 + c];
            return (
              <div
                key={w.id}
                className={`${styles.well} ${w.kind === "empty" ? styles.empty : ""}`}
                style={{ background: fill(w) }}
                title={title(w)}
                tabIndex={w.kind !== "empty" ? 0 : -1}
              />
            );
          }),
        ])}
      </div>
      <div className={styles.legend}>
        <span className={styles.ramp} /> 0% to 100% activity
        <span className={styles.ctrl}>N negative · P positive controls</span>
      </div>
    </div>
  );
}
