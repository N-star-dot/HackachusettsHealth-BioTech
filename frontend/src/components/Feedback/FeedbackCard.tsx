import { Num } from "../Num/Num";
import { simulated, assumed } from "../Num/provenance";
import { fold, nM } from "../../lib/format";
import { coverage, targetHalfWidth, concentrations } from "../../lib/dilution";
import { plannedLayout } from "../../lib/plate";
import type { ExperimentDesign, UncertaintyReport } from "../../api/types";
import styles from "./FeedbackCard.module.css";

interface Props {
  design: ExperimentDesign;
  report: UncertaintyReport;
  onApply?: (patch: { top_nM?: number; factor?: number; points?: number; replicates?: number }) => void;
}

type Verdict = "good" | "watch" | "poor";
interface Finding {
  key: string;
  verdict: Verdict;
  title: string;
  detail: string;
  action?: { label: string; patch: Parameters<NonNullable<Props["onApply"]>>[0] };
}

const GLYPH: Record<Verdict, string> = { good: "✓", watch: "!", poor: "×" };

/** Feedback and discovery (actionable, plain language): turns the uncertainty signals and
 *  the design geometry into concrete recommendations so a researcher doesn't burn compound
 *  and plates on trial and error. Complements the ranked "best next changes" list by
 *  explaining WHY and giving the specific numbers to use. */
export function FeedbackCard({ design, report, onApply }: Props) {
  const findings = buildFindings(design, report);
  const prov = () => simulated(report.seed, report.runs);
  const layout = plannedLayout(design);
  const freeWells = 96 - layout.wellsUsed;

  // the single highest-value improving change, if the planner found one
  const best = report.next_experiments
    .filter((n) => n.p90_after != null && n.p90_after < report.fold_error.p90)
    .sort((a, b) => b.score - a.score)[0];

  return (
    <section className={styles.section}>
      <div className={styles.head}>
        <span className={styles.numeral}>5</span>
        <h2 className={styles.name}>What to change</h2>
      </div>
      <p className={styles.lede}>
        Concrete adjustments from this run's numbers, so you spend compound and plate time
        where it moves the answer.
      </p>

      <ul className={styles.findings}>
        {findings.map((f) => (
          <li key={f.key} className={`${styles.finding} ${styles[f.verdict]}`}>
            <span className={styles.glyph} aria-hidden>{GLYPH[f.verdict]}</span>
            <div className={styles.body}>
              <span className={styles.title}>{f.title}</span>
              <span className={styles.detail}>{f.detail}</span>
              {f.action && onApply && (
                <button className={styles.apply} onClick={() => onApply(f.action!.patch)}>
                  {f.action.label}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      <div className={styles.summary}>
        <p>
          You use <Num value={`${layout.wellsUsed} of 96`} provenance={assumed("Wells = points x replicates + controls.")} /> wells.
          {freeWells > 0
            ? ` ${freeWells} are free, so more replicates or points add no plate.`
            : " The plate is full, so bigger designs need a second plate."}
        </p>
        {(() => {
          // A change is only "value" if it meaningfully cuts p90. Excess error is
          // (p90 - 1); require it to drop by at least 8% to be worth recommending.
          const excess = Math.max(report.fold_error.p90 - 1, 1e-6);
          const drop = best?.p90_after != null ? (report.fold_error.p90 - best.p90_after) / excess : 0;
          const worthwhile = best && best.p90_after != null && drop >= 0.08;
          if (worthwhile) {
            return (
              <p className={styles.best}>
                Best value: {best!.change.toLowerCase()}. p90{" "}
                <Num value={fold(report.fold_error.p90)} provenance={prov()} /> to{" "}
                <Num value={fold(best!.p90_after!)} provenance={prov()} /> for{" "}
                <Num value={`${best!.extra_tips} more tips`} provenance={assumed("Extra tips from the cost model.")} />{" "}
                and <Num value={`${best!.extra_compound_uL} µL`} provenance={assumed("Extra compound from the cost model.")} /> more compound.
                {best!.design && onApply && (
                  <button className={styles.apply} onClick={() => onApply({
                    top_nM: best!.design!.dilution.top_nM,
                    factor: best!.design!.dilution.factor,
                    points: best!.design!.dilution.points,
                    replicates: best!.design!.replicates,
                  })}>Apply this change</button>
                )}
              </p>
            );
          }
          return (
            <p className={styles.best}>
              This design is already efficient: no change the planner tried cuts p90 enough
              to be worth the extra tips and compound. Spend your plate on a new topic or a
              different compound instead.
            </p>
          );
        })()}
      </div>
    </section>
  );
}

/** Pure: derive plain-language findings from the design + report. Exported for tests. */
export function buildFindings(design: ExperimentDesign, report: UncertaintyReport): Finding[] {
  const out: Finding[] = [];
  const { top_nM, factor, points } = design.dilution;
  const prior = design.prior_ic50.median_nM;
  const concs = concentrations(top_nM, factor, points);
  const lo = concs[concs.length - 1];
  const hi = concs[0];
  const cov = coverage(top_nM, factor, points, prior);
  const needed = targetHalfWidth(design.prior_ic50.spread_log10 || 0.4);

  // How many points can we actually add before hitting the 11-point cap? A serial
  // dilution extends the LOW end (adds weaker concentrations below the current bottom).
  const MAX_POINTS = 11;
  const canAdd = Math.max(0, MAX_POINTS - points);
  const addN = Math.min(2, canAdd);
  const atTop = top_nM * factor; // where "raise top" lands
  const addPointsAction = canAdd > 0
    ? {
        label: addN === 1 ? "Add 1 point at the low end" : `Add ${addN} points at the low end`,
        patch: { points: points + addN },
      }
    : undefined;

  // 1. Does the tested range bracket the prior IC50?
  if (report.outside_range_share > 0.1) {
    out.push({
      key: "range", verdict: "poor",
      title: "Your concentration range misses the IC50 too often",
      detail: `In ${(report.outside_range_share * 100).toFixed(0)}% of runs the true IC50 fell outside ${nM(lo)} to ${nM(hi)}. Raise the top concentration to catch potent compounds.`,
      action: { label: `Raise top to ${nM(atTop)}`, patch: { top_nM: atTop } },
    });
  } else if (report.outside_range_share > 0.02) {
    out.push({
      key: "range", verdict: "watch",
      title: "The range covers the IC50, but with little margin",
      detail: canAdd > 0
        ? `${(report.outside_range_share * 100).toFixed(0)}% of runs land outside ${nM(lo)} to ${nM(hi)}. Adding ${addN === 1 ? "a point" : `${addN} points`} extends the low end (below ${nM(lo)}) for a little more margin.`
        : `${(report.outside_range_share * 100).toFixed(0)}% of runs land outside ${nM(lo)} to ${nM(hi)}. You are already at the 11-point limit, so raise the top concentration instead.`,
      action: addPointsAction ?? { label: `Raise top to ${nM(atTop)}`, patch: { top_nM: atTop } },
    });
  } else {
    out.push({
      key: "range", verdict: "good",
      title: "Your range brackets the expected IC50",
      detail: `The series runs ${nM(lo)} to ${nM(hi)} around a ${nM(prior)} prior, covering ${cov.below.toFixed(1)} log units below and ${cov.above.toFixed(1)} above (target about ${needed.toFixed(1)} each side).`,
    });
  }

  // 2. Precision: p90 fold error
  const p90 = report.fold_error.p90;
  if (p90 <= 1.5) {
    out.push({
      key: "precision", verdict: "good",
      title: "Precision is already good",
      detail: `9 in 10 simulated runs land within ${fold(p90)} of the truth. Extra replicates would add cost for little gain.`,
    });
  } else if (p90 <= 2) {
    out.push({
      key: "precision", verdict: "watch",
      title: "Precision is fair",
      detail: `p90 is ${fold(p90)}. Lab-to-lab spread dominates, so one more replicate helps more than more concentrations.`,
      action: { label: `Use ${design.replicates + 1} replicates`, patch: { replicates: Math.min(8, design.replicates + 1) } },
    });
  } else {
    out.push({
      key: "precision", verdict: "poor",
      title: "Precision is poor",
      detail: `p90 is ${fold(p90)}: a measured IC50 could be off by more than two fold. Add replicates and keep the range tight around the prior.`,
      action: { label: `Use ${Math.min(8, design.replicates + 2)} replicates`, patch: { replicates: Math.min(8, design.replicates + 2) } },
    });
  }

  // 3. Fit failures
  if (report.failed_fit_share > 0) {
    out.push({
      key: "fit", verdict: report.failed_fit_share > 0.05 ? "poor" : "watch",
      title: "Some curve fits failed",
      detail: canAdd > 0
        ? `${(report.failed_fit_share * 100).toFixed(0)}% of fits failed. Too few points on the curve's slope is the usual cause; adding ${addN === 1 ? "a point" : `${addN} points`} gives the fit more to work with.`
        : `${(report.failed_fit_share * 100).toFixed(0)}% of fits failed. You are at the 11-point limit; a tighter dilution factor packs more points through the IC50 instead.`,
      action: addPointsAction ?? { label: "Tighten factor to 3", patch: { factor: 3 } },
    });
  }

  // 4. Dilution factor spacing
  if (factor >= 5) {
    out.push({
      key: "spacing", verdict: "watch",
      title: "Wide dilution steps blur the curve",
      detail: `A ${factor}x factor spaces points far apart, so the fit has few readings near the IC50. A 3x factor packs more points through the transition.`,
      action: { label: "Tighten factor to 3", patch: { factor: 3 } },
    });
  }

  return out;
}
