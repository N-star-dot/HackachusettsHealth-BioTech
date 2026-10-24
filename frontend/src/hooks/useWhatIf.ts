import { useCallback, useRef, useState } from "react";
import { runUncertainty } from "../api/queries";
import { applyWhatIf, type WhatIfPatch } from "../lib/whatif";
import type { ExperimentDesign, UncertaintyReport } from "../api/types";

/** Owns the what-if draft: live geometry from applyWhatIf, and a debounced server call on
 *  release (plan=true) that cancels any in-flight request and drops stale responses. */
export function useWhatIf(baseDesign: ExperimentDesign, baseReport: UncertaintyReport) {
  const [patch, setPatch] = useState<WhatIfPatch>({});
  const [report, setReport] = useState<UncertaintyReport>(baseReport);
  const [pending, setPending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const { design: draft, notes } = applyWhatIf(baseDesign, patch);

  const commit = useCallback(async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const { design } = applyWhatIf(baseDesign, patch);
    setPending(true);
    try {
      const res = await runUncertainty({ design, runs: baseReport.runs, seed: baseReport.seed, plan: true }, ctrl.signal);
      // drop stale responses whose design_id isn't the current draft
      if (res.design_id === design.design_id) setReport(res);
    } catch {
      /* aborted or failed — keep the last good report */
    } finally {
      if (abortRef.current === ctrl) setPending(false);
    }
  }, [baseDesign, patch, baseReport.runs, baseReport.seed]);

  return { patch, setPatch, draft, notes, report, pending, commit };
}
