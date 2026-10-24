import { scaleLog } from "d3-scale";
import { concentrations, targetHalfWidth } from "../../lib/dilution";
import { nM } from "../../lib/format";
import type { ExperimentDesign } from "../../api/types";
import styles from "./DilutionLadder.module.css";

interface Props {
  design: ExperimentDesign;
}

/** Dilution ladder on a log10 nM axis (BRIEF 5.7): one dot per concentration, the prior
 *  as a vertical line, a light +/- target band and a darker +/- 1 lab-spread band. */
export function DilutionLadder({ design }: Props) {
  const { top_nM, factor, points } = design.dilution;
  const concs = concentrations(top_nM, factor, points);
  const prior = design.prior_ic50.median_nM;
  const spread = design.prior_ic50.spread_log10;
  const h = targetHalfWidth(spread);

  const w = 340, height = 70, pad = 16;
  const lo = Math.min(...concs, prior / 10 ** (h + 0.3));
  const hi = Math.max(...concs, prior * 10 ** (h + 0.3));
  const x = scaleLog().domain([lo, hi]).range([pad, w - pad]);

  const bandTarget = [prior / 10 ** h, prior * 10 ** h];
  const bandSpread = [prior / 10 ** spread, prior * 10 ** spread];

  return (
    <div className={styles.wrap}>
      <svg viewBox={`0 0 ${w} ${height}`} className={styles.svg} role="img"
           aria-label={`Dilution ladder, ${points} concentrations from ${nM(top_nM)} down to ${nM(concs[concs.length - 1])}`}>
        {/* target coverage band (light) */}
        <rect x={x(bandTarget[0])} y={20} width={x(bandTarget[1]) - x(bandTarget[0])} height={20}
              fill="var(--rule)" opacity="0.5" />
        {/* lab-spread band (darker) */}
        <rect x={x(bandSpread[0])} y={24} width={x(bandSpread[1]) - x(bandSpread[0])} height={12}
              fill="var(--graphite)" opacity="0.3" />
        {/* prior line */}
        <line x1={x(prior)} y1={14} x2={x(prior)} y2={46} stroke="var(--ink)" strokeWidth="1.5" />
        {/* concentration dots */}
        {concs.map((c, i) => (
          <circle key={i} cx={x(c)} cy={30} r={3} fill="var(--ink)">
            <title>{nM(c)}</title>
          </circle>
        ))}
        <line x1={pad} y1={52} x2={w - pad} y2={52} stroke="var(--rule)" />
      </svg>
      <p className={styles.caption}>
        {points} concentrations from {nM(top_nM)} down to {nM(concs[concs.length - 1])}, each
        one {factor === Math.round(factor) ? ordinal(factor) : `1/${factor}`} of the one before.
      </p>
    </div>
  );
}

function ordinal(f: number): string {
  if (f === 2) return "half";
  if (f === 3) return "third";
  if (f === 4) return "quarter";
  return `1/${f}`;
}
