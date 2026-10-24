import { scaleLinear, scaleLog } from "d3-scale";
import { line, area } from "d3-shape";
import type { UncertaintyReport } from "../../api/types";
import styles from "./Charts.module.css";

interface Props {
  report: UncertaintyReport;
}

/** Dose-response band (BRIEF 5.11), shown only when the curve is present (B1.3): log
 *  concentration x, % activity y, a p10-p90 band and a p50 line. */
export function CurveBand({ report }: Props) {
  const c = report.curve;
  if (!c || c.concentrations_nM.length === 0) return null;

  const w = 320, h = 140, pad = 28;
  const x = scaleLog().domain([Math.min(...c.concentrations_nM), Math.max(...c.concentrations_nM)]).range([pad, w - pad]);
  const y = scaleLinear().domain([0, 100]).range([h - pad, pad]);

  const idx = c.concentrations_nM.map((_, i) => i);
  const band = area<number>()
    .x((i) => x(c.concentrations_nM[i]))
    .y0((i) => y(c.activity_p10[i]))
    .y1((i) => y(c.activity_p90[i]));
  const mid = line<number>().x((i) => x(c.concentrations_nM[i])).y((i) => y(c.activity_p50[i]));

  return (
    <div className={styles.wrap}>
      <svg viewBox={`0 0 ${w} ${h}`} className={styles.svg} role="img"
           aria-label="Dose-response band, p10 to p90 of activity by concentration">
        <path d={band(idx) ?? ""} fill="var(--inhibited)" opacity="0.18" />
        <path d={mid(idx) ?? ""} fill="none" stroke="var(--inhibited)" strokeWidth="1.5" />
        {c.concentrations_nM.map((conc, i) => (
          <line key={i} x1={x(conc)} y1={h - pad} x2={x(conc)} y2={h - pad + 3} stroke="var(--graphite)" />
        ))}
        <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="var(--rule)" />
        <text x={pad} y={pad - 6} className={styles.axisText}>% activity</text>
      </svg>
      <p className={styles.caption}>Simulated dose-response: p10-p90 band, p50 line.</p>
    </div>
  );
}
