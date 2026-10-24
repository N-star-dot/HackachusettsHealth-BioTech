import { describe, expect, it } from "vitest";
import { buildFindings } from "../components/Feedback/FeedbackCard";
import type { ExperimentDesign, UncertaintyReport } from "../api/types";

const design: ExperimentDesign = {
  design_id: "d-001", topic_id: "T",
  assay: { type: "dose_response", readout: "percent_activity", target_chembl_id: "a", compound_chembl_id: "b" },
  prior_ic50: { median_nM: 24, n_measurements: 21, spread_log10: 0.4, source: { type: "chembl_activity", id: "1" } },
  dilution: { top_nM: 2400, factor: 3, points: 10 },
  replicates: 3, controls: { positive_wells: 4, negative_wells: 4 },
  plate: { labware: "corning_96_wellplate_360ul_flat", layout: "rows" },
  volumes_uL: { transfer: 50, diluent: 100 },
  pipette: "flex_1channel_1000", tiprack: "opentrons_flex_96_tiprack_200ul", rationale: [],
};

function report(over: Partial<UncertaintyReport>): UncertaintyReport {
  return {
    design_id: "d-001", label: "simulated", runs: 1000, seed: 42,
    noise: { lab_spread_log10: 0.68, pipette_cv: 0.02, pipette_bias: 0.01, reader_cv: 0.05, sources: [] },
    fold_error: { median: 1.1, p90: 1.3 }, outside_range_share: 0.0, failed_fit_share: 0,
    calibration: { coverage_90: 0.9, pairs: 87 }, next_experiments: [], ...over,
  };
}

describe("feedback findings (discovery)", () => {
  it("flags a range that misses the IC50 as poor and suggests widening", () => {
    const f = buildFindings(design, report({ outside_range_share: 0.2 }));
    const range = f.find((x) => x.key === "range")!;
    expect(range.verdict).toBe("poor");
    expect(range.action).toBeTruthy();
    expect(range.action!.patch.top_nM).toBeGreaterThan(design.dilution.top_nM);
  });

  it("calls a tight p90 good and offers no replicate change", () => {
    const f = buildFindings(design, report({ fold_error: { median: 1.05, p90: 1.3 } }));
    const prec = f.find((x) => x.key === "precision")!;
    expect(prec.verdict).toBe("good");
    expect(prec.action).toBeUndefined();
  });

  it("calls a poor p90 poor and suggests more replicates", () => {
    const f = buildFindings(design, report({ fold_error: { median: 1.8, p90: 2.6 } }));
    const prec = f.find((x) => x.key === "precision")!;
    expect(prec.verdict).toBe("poor");
    expect(prec.action!.patch.replicates).toBe(5); // 3 + 2
  });

  it("flags failed fits and a wide dilution factor", () => {
    const wide = { ...design, dilution: { ...design.dilution, factor: 6 } };
    const f = buildFindings(wide, report({ failed_fit_share: 0.08 }));
    expect(f.find((x) => x.key === "fit")!.verdict).toBe("poor");
    const spacing = f.find((x) => x.key === "spacing")!;
    expect(spacing.verdict).toBe("watch");
    expect(spacing.action!.patch.factor).toBe(3);
  });
});
