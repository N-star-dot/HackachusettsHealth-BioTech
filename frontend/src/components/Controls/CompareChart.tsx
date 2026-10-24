import { scaleLinear } from "d3-scale";
import type { NextExperiment } from "../../api/types";
import { useUIStore } from "../../state/store";
import styles from "./CompareChart.module.css";

interface Props {
  currentTips: number;
  currentP90: number;
  suggestions: NextExperiment[];
}

/** Cost against certainty (BRIEF 5.13): x = tips, y = p90 fold error (lower is better).
 *  Current design filled, pins lettered, planner suggestions outlined. */
export function CompareChart({ currentTips, currentP90, suggestions }: Props) {
  const pins = useUIStore((s) => s.pins);

  const points = [
    { kind: "current" as const, tips: currentTips, p90: currentP90, label: "" },
    ...pins.map((p) => ({ kind: "pin" as const, tips: p.tips, p90: p.p90, label: p.letter })),
    ...suggestions
      .filter((s) => s.p90_after != null)
      .map((s) => ({ kind: "sugg" as const, tips: currentTips + s.extra_tips, p90: s.p90_after!, label: "" })),
  ];

  const w = 300, h = 160, pad = 32;
  const xs = points.map((p) => p.tips);
  const ys = points.map((p) => p.p90);
  const x = scaleLinear().domain([Math.min(...xs) - 2, Math.max(...xs) + 2]).range([pad, w - pad]);
  const y = scaleLinear().domain([Math.min(...ys, 1) - 0.02, Math.max(...ys) + 0.02]).range([h - pad, pad]);

  return (
    <div className={styles.wrap}>
      <h3 className={styles.title}>Cost against certainty</h3>
      <svg viewBox={`0 0 ${w} ${h}`} className={styles.svg} role="img"
           aria-label="Cost against certainty: tips versus p90 fold error">
        <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="var(--rule)" />
        <line x1={pad} y1={pad} x2={pad} y2={h - pad} stroke="var(--rule)" />
        <text x={w - pad} y={h - pad + 14} className={styles.axis} textAnchor="end">tips</text>
        <text x={pad - 6} y={pad} className={styles.axis} textAnchor="end">p90</text>
        {points.map((p, i) => (
          <g key={i} transform={`translate(${x(p.tips)},${y(p.p90)})`}>
            {p.kind === "current" && <circle r={5} fill="var(--ink)" />}
            {p.kind === "pin" && <><circle r={7} fill="var(--sheet)" stroke="var(--ink)" /><text className={styles.pinLabel} textAnchor="middle" dy="3">{p.label}</text></>}
            {p.kind === "sugg" && <circle r={5} fill="none" stroke="var(--graphite)" strokeDasharray="2 2" />}
          </g>
        ))}
      </svg>
    </div>
  );
}
