// Rule checks computed in the browser from the design (BRIEF 5.8).
import { coverage, targetHalfWidth } from "./dilution";
import { plannedLayout } from "./plate";
import type { ExperimentDesign } from "../api/types";

export interface RuleCheck {
  label: string;
  pass: boolean;
}

export function ruleChecks(design: ExperimentDesign): RuleCheck[] {
  const { top_nM, factor, points } = design.dilution;
  const prior = design.prior_ic50.median_nM;
  const { above, below } = coverage(top_nM, factor, points, prior);
  const h = targetHalfWidth(design.prior_ic50.spread_log10);
  const used = plannedLayout(design).wellsUsed;
  const t = design.volumes_uL.transfer;
  const d = design.volumes_uL.diluent;

  return [
    {
      label: `Covers the starting guess: ${above.toFixed(1)} log units above and ${below.toFixed(1)} below (target ${h.toFixed(1)}).`,
      pass: Math.min(above, below) >= h - 0.01,
    },
    {
      label: "Transfers stay at or above 5 µL, the 1000 µL pipette's minimum.",
      pass: t >= 5,
    },
    {
      label: `Fits on one plate: ${used} of 96 wells.`,
      pass: used <= 96,
    },
    {
      label: `Dilution factor matches the volumes: (${t} + ${d}) / ${t} = ${((t + d) / t).toFixed(2)}.`,
      pass: Math.abs((t + d) / t - factor) < 1e-6,
    },
  ];
}
