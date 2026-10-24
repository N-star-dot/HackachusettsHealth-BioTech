import { Num } from "../Num/Num";
import { assumed, src } from "../Num/provenance";
import { prob } from "../../lib/format";
import type { TopicReport } from "../../api/types";
import styles from "./MomentumScale.module.css";

interface Props {
  topic: TopicReport;
}

/** Momentum 0-100% scale with a marker and a 50% tick, plus a model-card note (BRIEF 5.4).
 *  Hidden entirely for the offline-placeholder model. */
export function MomentumScale({ topic }: Props) {
  const m = topic.momentum;
  if (m.model === "offline-placeholder") return null;

  const p = m.p_growth;
  const momentumSource = topic.matrix.axis_sources?.momentum;
  const prov = momentumSource
    ? src(momentumSource, modelNote(m.model))
    : assumed(modelNote(m.model));

  return (
    <div className={styles.wrap}>
      <div className={styles.track} aria-hidden>
        <div className={styles.tick} style={{ left: "50%" }} />
        <div className={styles.marker} style={{ left: `${p * 100}%` }} />
      </div>
      <p className={styles.sentence}>
        <Num value={prob(p)} provenance={prov} /> chance this topic grows faster than the
        typical topic over the next five years.
      </p>
    </div>
  );
}

function modelNote(model: string): string {
  if (model === "slope-heuristic")
    return "Rough estimate from the publication trend. The trained model wasn't available.";
  return `Trained model ${model}, using 2015-2019 publication counts to predict 2020-2024 growth.`;
}
