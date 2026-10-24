// What-if design patching (BRIEF B.8). Apply a patch, couple diluent to the factor, clamp
// to the 5.12 limits and the B.7 plate budget, and give the result a new design_id.
import { hash6 } from "./hash";
import type { ExperimentDesign } from "../api/types";

export interface WhatIfPatch {
  top_nM?: number;
  factor?: number;
  points?: number;
  replicates?: number;
  transfer?: number;
}

const LIMITS = {
  top_nM: [1, 100_000],
  factor: [2, 10],
  points: [4, 11],
  replicates: [1, 8],
  transfer: [5, 100],
} as const;

function clamp(v: number, [lo, hi]: readonly [number, number]): number {
  return Math.max(lo, Math.min(hi, v));
}

export interface WhatIfResult {
  design: ExperimentDesign;
  notes: string[];
}

/** Apply a patch to the run's design, returning a new valid design + plain notes. */
export function applyWhatIf(base: ExperimentDesign, patch: WhatIfPatch): WhatIfResult {
  const notes: string[] = [];
  const d: ExperimentDesign = structuredClone(base);

  if (patch.top_nM != null) d.dilution.top_nM = clamp(patch.top_nM, LIMITS.top_nM);
  if (patch.factor != null) d.dilution.factor = clamp(patch.factor, LIMITS.factor);
  if (patch.points != null) d.dilution.points = Math.round(clamp(patch.points, LIMITS.points));
  if (patch.replicates != null) d.replicates = Math.round(clamp(patch.replicates, LIMITS.replicates));
  if (patch.transfer != null) d.volumes_uL.transfer = clamp(patch.transfer, LIMITS.transfer);

  // couple diluent to the factor
  d.volumes_uL.diluent = d.volumes_uL.transfer * (d.dilution.factor - 1);

  // keep the top well under 300 µL: if transfer*factor > 300, lower the transfer
  if (d.volumes_uL.transfer * d.dilution.factor > 300) {
    const t = Math.floor(300 / d.dilution.factor);
    notes.push(`Transfer lowered to ${t} µL so the top well stays under 300 µL.`);
    d.volumes_uL.transfer = Math.max(LIMITS.transfer[0], t);
    d.volumes_uL.diluent = d.volumes_uL.transfer * (d.dilution.factor - 1);
  }

  // plate budget: points*replicates + controls <= 96
  const controls = d.controls.positive_wells + d.controls.negative_wells;
  while (d.dilution.points * d.replicates + controls > 96 && d.dilution.points > LIMITS.points[0]) {
    d.dilution.points -= 1;
    notes.push(`Dilution points reduced to ${d.dilution.points} to fit the plate.`);
  }

  // new design_id so the backend never overwrites the run's protocol file
  d.design_id = `${base.design_id}-w${hash6(patch)}`;
  return { design: d, notes };
}
