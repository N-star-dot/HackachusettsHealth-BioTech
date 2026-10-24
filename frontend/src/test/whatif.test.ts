import { describe, expect, it } from "vitest";
import fc from "fast-check";
import { applyWhatIf } from "../lib/whatif";
import type { ExperimentDesign } from "../api/types";

const base: ExperimentDesign = {
  design_id: "d-001", topic_id: "T",
  assay: { type: "dose_response", readout: "percent_activity", target_chembl_id: "a", compound_chembl_id: "b" },
  prior_ic50: { median_nM: 24, n_measurements: 21, spread_log10: 0.93, source: { type: "chembl_activity", id: "1" } },
  dilution: { top_nM: 2399, factor: 3, points: 10 },
  replicates: 3, controls: { positive_wells: 4, negative_wells: 4 },
  plate: { labware: "corning_96_wellplate_360ul_flat", layout: "rows" },
  volumes_uL: { transfer: 50, diluent: 100 },
  pipette: "flex_1channel_1000", tiprack: "opentrons_flex_96_tiprack_200ul", rationale: [],
};

describe("applyWhatIf (BRIEF B.8)", () => {
  it("output always satisfies every limit and the factor-volume relation", () => {
    fc.assert(
      fc.property(
        fc.record({
          top_nM: fc.double({ min: 0.1, max: 1e7, noNaN: true }),
          factor: fc.double({ min: 1, max: 20, noNaN: true }),
          points: fc.integer({ min: 1, max: 20 }),
          replicates: fc.integer({ min: 1, max: 20 }),
          transfer: fc.double({ min: 0.1, max: 500, noNaN: true }),
        }),
        (patch) => {
          const { design: d } = applyWhatIf(base, patch);
          expect(d.dilution.top_nM).toBeGreaterThanOrEqual(1);
          expect(d.dilution.top_nM).toBeLessThanOrEqual(100_000);
          expect(d.dilution.factor).toBeGreaterThanOrEqual(2);
          expect(d.dilution.factor).toBeLessThanOrEqual(10);
          expect(d.dilution.points).toBeGreaterThanOrEqual(4);
          expect(d.dilution.points).toBeLessThanOrEqual(11);
          expect(d.replicates).toBeGreaterThanOrEqual(1);
          expect(d.replicates).toBeLessThanOrEqual(8);
          expect(d.volumes_uL.transfer).toBeGreaterThanOrEqual(5);
          // transfer*factor under the 300 cap
          expect(d.volumes_uL.transfer * d.dilution.factor).toBeLessThanOrEqual(300 + 1e-6);
          // diluent couples to the factor
          const ratio = (d.volumes_uL.transfer + d.volumes_uL.diluent) / d.volumes_uL.transfer;
          expect(Math.abs(ratio - d.dilution.factor)).toBeLessThan(1e-9);
          // plate budget
          const controls = d.controls.positive_wells + d.controls.negative_wells;
          expect(d.dilution.points * d.replicates + controls).toBeLessThanOrEqual(96);
          // design_id is filename-safe
          expect(d.design_id).toMatch(/^[A-Za-z0-9_-]+$/);
        },
      ),
      { numRuns: 300 },
    );
  });

  it("is idempotent for the same patch", () => {
    const patch = { factor: 4, transfer: 40 };
    const once = applyWhatIf(base, patch).design;
    const twice = applyWhatIf(base, patch).design;
    expect(once).toEqual(twice);
  });
});
