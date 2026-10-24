import { beforeEach, describe, expect, it } from "vitest";
import { activeDesign, useUIStore } from "../state/store";
import { hash6 } from "../lib/hash";
import type { ExperimentDesign, RunResponse, UncertaintyReport } from "../api/types";

const design: ExperimentDesign = {
  design_id: "d-001", topic_id: "T",
  assay: { type: "dose_response", readout: "percent_activity", target_chembl_id: "a", compound_chembl_id: "b" },
  prior_ic50: { median_nM: 24, n_measurements: 21, spread_log10: 0.93, source: { type: "chembl_activity", id: "1" } },
  dilution: { top_nM: 2399, factor: 3, points: 10 },
  replicates: 3, controls: { positive_wells: 4, negative_wells: 4 },
  plate: { labware: "corning_96_wellplate_360ul_flat", layout: "rows" },
  volumes_uL: { transfer: 50, diluent: 100 },
  pipette: "flex_1channel_1000", tiprack: "opentrons_flex_96_tiprack_200ul", rationale: [],
};

function report(design_id: string, p90: number): UncertaintyReport {
  return {
    design_id, label: "simulated", runs: 1000, seed: 42,
    noise: { lab_spread_log10: 0.68, pipette_cv: 0.02, pipette_bias: 0.01, reader_cv: 0.05, sources: [] },
    fold_error: { median: 1.1, p90 }, outside_range_share: 0.01, failed_fit_share: 0,
    calibration: { coverage_90: 0.9, pairs: 87 }, next_experiments: [],
  };
}

const run: RunResponse = {
  run_id: "run-1", blocked: false, topic: null,
  design, sim: null, uncertainty: report("d-001", 1.22),
};

describe("active run store (W1.3)", () => {
  beforeEach(() => {
    useUIStore.setState({ active: null });
  });

  it("seeds one active report from the run", () => {
    useUIStore.getState().loadRun(run);
    const a = useUIStore.getState().active!;
    expect(a.runId).toBe("run-1");
    expect(a.report.fold_error.p90).toBe(1.22);
    // baseline design is cached, so returning to it never needs a request
    expect(a.cache[hash6(design)]).toBeDefined();
  });

  it("a committed what-if report replaces the single active report", () => {
    const s = useUIStore.getState();
    s.loadRun(run);
    s.setPatch({ points: 8 });
    const draft = activeDesign(useUIStore.getState().active!);
    s.applyReport(report(draft.design_id, 1.37));
    // the ONE active report is now the what-if result; there is no second answer
    expect(useUIStore.getState().active!.report.fold_error.p90).toBe(1.37);
  });

  it("drops a stale report whose design_id is not the current draft", () => {
    const s = useUIStore.getState();
    s.loadRun(run);
    s.setPatch({ points: 8 });
    s.applyReport(report("some-other-design", 9.9));
    expect(useUIStore.getState().active!.report.fold_error.p90).not.toBe(9.9);
  });

  it("returning to the baseline design restores the original report from cache", () => {
    const s = useUIStore.getState();
    s.loadRun(run);
    s.setPatch({ points: 8 });
    const draft = activeDesign(useUIStore.getState().active!);
    s.applyReport(report(draft.design_id, 1.37));
    // reset: patch cleared, report back to baseline instantly
    s.resetPatch();
    expect(useUIStore.getState().active!.report.fold_error.p90).toBe(1.22);
    expect(Object.keys(useUIStore.getState().active!.patch)).toHaveLength(0);
  });

  it("setPatch with a cached design resolves the report with no request", () => {
    const s = useUIStore.getState();
    s.loadRun(run);
    s.setPatch({ points: 8 });
    const draft = activeDesign(useUIStore.getState().active!);
    s.applyReport(report(draft.design_id, 1.37));
    // go away and come back to the same draft: cache hit gives the report immediately
    s.resetPatch();
    s.setPatch({ points: 8 });
    expect(useUIStore.getState().active!.report.fold_error.p90).toBe(1.37);
  });

  it("keepAsBaseline promotes the draft to the new baseline", () => {
    const s = useUIStore.getState();
    s.loadRun(run);
    s.setPatch({ points: 8 });
    const draft = activeDesign(useUIStore.getState().active!);
    s.applyReport(report(draft.design_id, 1.37));
    s.keepAsBaseline();
    const a = useUIStore.getState().active!;
    expect(a.baseDesign.design_id).toBe(draft.design_id);
    expect(a.baseReport.fold_error.p90).toBe(1.37);
    expect(Object.keys(a.patch)).toHaveLength(0);
  });

  it("a new run id resets the active state clean", () => {
    const s = useUIStore.getState();
    s.loadRun(run);
    s.setPatch({ points: 8 });
    const run2: RunResponse = { ...run, run_id: "run-2", uncertainty: report("d-001", 1.5) };
    s.loadRun(run2);
    const a = useUIStore.getState().active!;
    expect(a.runId).toBe("run-2");
    expect(Object.keys(a.patch)).toHaveLength(0);
    expect(a.report.fold_error.p90).toBe(1.5);
  });

  it("mergeNextExperiments keeps the fast fold_error and swaps only best-next-changes (W1.4)", () => {
    const s = useUIStore.getState();
    s.loadRun(run);
    s.setPatch({ points: 8 });
    const draft = activeDesign(useUIStore.getState().active!);
    // fast report (plan:false) lands first with no suggestions
    s.applyReport({ ...report(draft.design_id, 1.37), next_experiments: [] });
    // background planner report for the same design carries suggestions but a different p90
    const planned = report(draft.design_id, 9.99);
    planned.next_experiments = [
      { change: "add 1 replicate", p90_fold_error_drop_pct: 5, extra_tips: 12,
        extra_compound_uL: 150, extra_plates: 0, score: 1, p90_after: 1.3 },
    ];
    s.mergeNextExperiments(planned);
    const a = useUIStore.getState().active!;
    expect(a.report.fold_error.p90).toBe(1.37);          // kept the fast answer
    expect(a.report.next_experiments).toHaveLength(1);    // took only the suggestions
  });

  it("mergeNextExperiments drops a stale planner report for a superseded draft", () => {
    const s = useUIStore.getState();
    s.loadRun(run);
    s.setPatch({ points: 8 });
    const draft = activeDesign(useUIStore.getState().active!);
    s.applyReport({ ...report(draft.design_id, 1.37), next_experiments: [] });
    const stale = report("old-design", 1.0);
    stale.next_experiments = [
      { change: "stale", p90_fold_error_drop_pct: 1, extra_tips: 0,
        extra_compound_uL: 0, extra_plates: 0, score: 0, p90_after: 1.0 },
    ];
    s.mergeNextExperiments(stale);
    expect(useUIStore.getState().active!.report.next_experiments).toHaveLength(0);
  });
});
