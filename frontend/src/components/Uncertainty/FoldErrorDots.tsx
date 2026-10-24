import { scaleLog } from "d3-scale";
import type { UncertaintyReport } from "../../api/types";
import styles from "./Charts.module.css";

interface Props {
  report: UncertaintyReport;
}

/** Fold-error dot histogram (BRIEF 5.11), shown only when samples are present (B1.3).
 *  Log x from 1x; median and p90 lines. */
export function FoldErrorDots({ report }: Props) {
  const fe = report.samples?.fold_error;
  if (!fe || fe.length === 0) return null;

  const w = 320, h = 90, pad = 20;
  const max = Math.max(...fe, report.fold_error.p90, 2);
  const x = scaleLog().domain([1, max]).range([pad, w - pad]).clamp(true);

  // simple vertical jitter by index bucket
  const dots = fe.map((v, i) => ({ cx: x(Math.max(1, v)), cy: pad + ((i * 7) % (h - pad * 2)) }));

  return (
    <div className={styles.wrap}>
      <svg viewBox={`0 0 ${w} ${h}`} className={styles.svg} role="img"
           aria-label={`Fold error of ${fe.length} simulated experiments`}>
        {dots.map((d, i) => (
          <circle key={i} cx={d.cx} cy={d.cy} r={1.6} fill="var(--graphite)" opacity="0.6" />
        ))}
        <line x1={x(report.fold_error.median)} y1={pad - 4} x2={x(report.fold_error.median)} y2={h - pad}
              stroke="var(--ink)" strokeWidth="1" />
        <line x1={x(report.fold_error.p90)} y1={pad - 4} x2={x(report.fold_error.p90)} y2={h - pad}
              stroke="var(--active)" strokeWidth="1" />
        <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="var(--rule)" />
      </svg>
      <p className={styles.caption}>Each dot is one simulated experiment. Ink line median, pink line p90.</p>
    </div>
  );
}
