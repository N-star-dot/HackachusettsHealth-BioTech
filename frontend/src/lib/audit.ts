// Plate audit (BRIEF B.10): compare the replay's final state with the planned layout and
// report differences in plain words.
import { plannedLayout } from "./plate";
import type { ReplayState } from "./replay";
import type { ExperimentDesign } from "../api/types";

export function plateAudit(design: ExperimentDesign, final: ReplayState): string[] {
  const layout = plannedLayout(design);
  const diluent = design.volumes_uL.diluent;
  const issues: string[] = [];

  for (const w of layout.wells) {
    if (w.kind === "empty") continue;
    const got = final.wells[w.id];
    const expectVol = diluent;

    if (!got || got.volume_uL <= 0.5) {
      issues.push(`${w.id} ends empty, so it can't be read.`);
      continue;
    }
    if (Math.abs(got.volume_uL - expectVol) > 1) {
      issues.push(`${w.id} ends with ${got.volume_uL.toFixed(0)} µL instead of ${expectVol} µL.`);
    }
    if (w.kind === "dilution" && w.concNM != null && got.conc_nM > 0) {
      const rel = Math.abs(got.conc_nM - w.concNM) / w.concNM;
      if (rel > 0.01) {
        issues.push(`${w.id} ends near ${got.conc_nM.toFixed(0)} nM, not the planned ${w.concNM.toFixed(0)} nM.`);
      }
    }
  }
  return issues;
}
