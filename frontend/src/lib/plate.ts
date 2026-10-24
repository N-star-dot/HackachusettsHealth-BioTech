// Planned 96-well layout (BRIEF B.7). Replicate r uses row "ABCDEFGH"[r]; point i uses
// column i+1. Column 12 holds controls: negatives (diluent) first, then positives (stock).
import { concentrations } from "./dilution";

export const ROWS = "ABCDEFGH".split("");
export const COLS = Array.from({ length: 12 }, (_, i) => i + 1);

export type WellKind = "dilution" | "negative" | "positive" | "empty";

export interface PlannedWell {
  id: string;          // e.g. "B4"
  row: number;         // 0-7
  col: number;         // 0-11
  kind: WellKind;
  concNM?: number;     // for dilution wells + positive controls (top stock)
  replicate?: number;  // 1-based for dilution wells
  point?: number;      // 1-based column within the dilution series
}

export interface PlannedLayout {
  wells: PlannedWell[];
  wellsUsed: number;
}

export function plannedLayout(design: {
  dilution: { top_nM: number; factor: number; points: number };
  replicates: number;
  controls: { positive_wells: number; negative_wells: number };
}): PlannedLayout {
  const { top_nM, factor, points } = design.dilution;
  const concs = concentrations(top_nM, factor, points);
  const wells: PlannedWell[] = [];

  for (let r = 0; r < ROWS.length; r++) {
    for (let c = 0; c < COLS.length; c++) {
      const id = `${ROWS[r]}${c + 1}`;
      // dilution block: first `replicates` rows x first `points` columns
      if (r < design.replicates && c < points) {
        wells.push({ id, row: r, col: c, kind: "dilution",
          concNM: concs[c], replicate: r + 1, point: c + 1 });
      } else if (c === 11) {
        // column 12: negatives then positives, from the top
        const k = r;
        if (k < design.controls.negative_wells) {
          wells.push({ id, row: r, col: c, kind: "negative" });
        } else if (k < design.controls.negative_wells + design.controls.positive_wells) {
          wells.push({ id, row: r, col: c, kind: "positive", concNM: top_nM });
        } else {
          wells.push({ id, row: r, col: c, kind: "empty" });
        }
      } else {
        wells.push({ id, row: r, col: c, kind: "empty" });
      }
    }
  }

  const wellsUsed =
    design.dilution.points * design.replicates +
    design.controls.positive_wells + design.controls.negative_wells;

  return { wells, wellsUsed };
}
