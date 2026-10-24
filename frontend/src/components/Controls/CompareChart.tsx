import { scaleLinear } from "d3-scale";
import type { NextExperiment } from "../../api/types";
import { useUIStore } from "../../state/store";
import styles from "./CompareChart.module.css";

interface Props {
  currentTips: number;
  currentP90: number;
  suggestions: NextExperiment[];
}

/** Cost against certainty (BRIEF 5.13): x = tips (more = costlier), y = p90 fold error
 *  (lower = more certain). The current design, your pinned designs (lettered), and the
 *  planner's suggestions (outlined) all plot together so you can see the trade-off. */
export function CompareChart({ currentTips, currentP90, suggestions }: Props) {
  const pins = useUIStore((s) => s.pins);

  const points = [
    { kind: "current" as const, tips: currentTips, p90: currentP90, label: "Now" },
    ...pins.map((p) => ({ kind: "pin" as const, tips: p.tips, p90: p.p90, label: p.letter })),
    ...suggestions
      .filter((s) => s.p90_after != null)
      .map((s) => ({ kind: "sugg" as const, tips: currentTips + s.extra_tips, p90: s.p90_after!, label: "" })),
  ];

  const w = 360, h = 190, pad = 40;
  const xs = points.map((p) => p.tips);
  const ys = points.map((p) => p.p90);
  const xDomain: [number, number] = [Math.min(...xs) - 2, Math.max(...xs) + 2];
  const yDomain: [number, number] = [Math.min(...ys, 1) - 0.03, Math.max(...ys) + 0.03];
  const x = scaleLinear().domain(xDomain).range([pad, w - pad]);
  const y = scaleLinear().domain(yDomain).range([h - pad, pad]);

  const xTicks = [xDomain[0], (xDomain[0] + xDomain[1]) / 2, xDomain[1]].map((v) => Math.round(v));
  const yTicks = [yDomain[0], (yDomain[0] + yDomain[1]) / 2, yDomain[1]];

  return (
    <div className={styles.wrap}>
      <h3 className={styles.title}>Cost against certainty</h3>
      <p className={styles.hint}>Lower is more certain; left is cheaper. Pin designs to compare.</p>
      <svg viewBox={`0 0 ${w} ${h}`} className={styles.svg} role="img"
           aria-label="Cost against certainty: tips on x, p90 fold error on y, lower is better">
        {/* axes */}
        <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="var(--rule)" />
        <line x1={pad} y1={pad} x2={pad} y2={h - pad} stroke="var(--rule)" />
        {xTicks.map((t) => (
          <g key={`x${t}`}>
            <line x1={x(t)} y1={h - pad} x2={x(t)} y2={h - pad + 3} stroke="var(--graphite)" />
            <text x={x(t)} y={h - pad + 13} className={styles.tick} textAnchor="middle">{t}</text>
          </g>
        ))}
        {yTicks.map((t, i) => (
          <g key={`y${i}`}>
            <line x1={pad - 3} y1={y(t)} x2={pad} y2={y(t)} stroke="var(--graphite)" />
            <text x={pad - 5} y={y(t) + 3} className={styles.tick} textAnchor="end">{t.toFixed(2)}x</text>
          </g>
        ))}
        <text x={w - pad} y={h - 6} className={styles.axis} textAnchor="end">tips</text>
        <text transform={`translate(11 ${pad}) rotate(-90)`} className={styles.axis} textAnchor="end">p90 fold error</text>

        {points.map((p, i) => (
          <g key={i} transform={`translate(${x(p.tips)},${y(p.p90)})`}>
            {p.kind === "current" && (
              <>
                <circle r={5} fill="var(--ink)" />
                <text className={styles.pointLabel} x={8} y={3}>Now</text>
              </>
            )}
            {p.kind === "pin" && (
              <>
                <circle r={8} fill="var(--sheet)" stroke="var(--ink)" strokeWidth={1.2} />
                <text className={styles.pinLabel} textAnchor="middle" dy="3">{p.label}</text>
              </>
            )}
            {p.kind === "sugg" && <circle r={5} fill="none" stroke="var(--graphite)" strokeDasharray="2 2" />}
          </g>
        ))}
      </svg>
      <ul className={styles.legend}>
        <li><span className={styles.dotCurrent} /> Current design</li>
        {pins.length > 0 && <li><span className={styles.dotPin} /> Pinned ({pins.map((p) => p.letter).join(", ")})</li>}
        {suggestions.some((s) => s.p90_after != null) && <li><span className={styles.dotSugg} /> Suggestions</li>}
      </ul>
    </div>
  );
}
