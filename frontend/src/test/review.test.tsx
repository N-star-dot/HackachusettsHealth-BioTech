import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { ReviewThread } from "../components/Review/ReviewThread";
import { ruleChecks } from "../lib/ruleChecks";
import type { ExperimentDesign } from "../api/types";

function design(rationale: ExperimentDesign["rationale"]): ExperimentDesign {
  return {
    design_id: "d-001", topic_id: "T",
    assay: { type: "dose_response", readout: "percent_activity",
      target_chembl_id: "CHEMBL1824", compound_chembl_id: "CHEMBL554" },
    prior_ic50: { median_nM: 24, n_measurements: 21, spread_log10: 0.93,
      source: { type: "chembl_activity", id: "1" } },
    dilution: { top_nM: 2399, factor: 3, points: 10 },
    replicates: 3,
    controls: { positive_wells: 4, negative_wells: 4 },
    plate: { labware: "corning_96_wellplate_360ul_flat", layout: "rows" },
    volumes_uL: { transfer: 50, diluent: 100 },
    pipette: "flex_1channel_1000", tiprack: "opentrons_flex_96_tiprack_200ul",
    rationale,
  };
}

describe("ReviewThread (BRIEF 5.8)", () => {
  it("shows the flag and reason for an unverified item", () => {
    const d = design([
      { claim: "x", pmid: "", evidence_type: "chembl_activity", evidence_id: "1",
        status: "unverified", verified: false, reason: "activity 1 not in this pair's records" },
    ]);
    const { getByText } = render(<ReviewThread design={d} />);
    expect(getByText(/1 items could not be verified/)).toBeTruthy();
    expect(getByText(/Not verified/)).toBeTruthy();
    expect(getByText(/not in this pair's records/)).toBeTruthy();
  });

  it("renders a model_note with its 'not verified' label (never beside a green badge)", () => {
    const d = design([
      { claim: "model paraphrase", pmid: "123", evidence_type: "abstract_quote", evidence_id: "123",
        quote: "Lapatinib inhibited HER2 with an IC50 of 9.2 nM in a biochemical assay.",
        model_note: "model paraphrase", status: "verified", verified: true },
    ]);
    const { getByText } = render(<ReviewThread design={d} />);
    // the quote (not the note) earns the verified badge
    expect(getByText("Verified quote")).toBeTruthy();
    // the model note always carries the not-verified label
    expect(getByText("Model's note, not verified")).toBeTruthy();
  });
});

describe("ruleChecks", () => {
  it("passes for a well-formed lapatinib design", () => {
    const d = design([]);
    const checks = ruleChecks(d);
    expect(checks.every((c) => c.pass)).toBe(true);
  });
});
