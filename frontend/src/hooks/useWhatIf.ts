import { useCallback, useRef, useState } from "react";
import { runSimulate, runUncertainty } from "../api/queries";
import { applyWhatIf, type WhatIfPatch } from "../lib/whatif";
import { hash6 } from "../lib/hash";
import { activeDesign, useUIStore } from "../state/store";

/** Controller for the what-if draft (W1.3, W1.4). The draft, report and sim all live in
 *  the store under the active run, so the notebook and the bench read the same numbers and
 *  a new run starts clean. On release this fires /api/uncertainty (plan=false) and
 *  /api/simulate in parallel for a fast answer, then /api/uncertainty (plan=true) in the
 *  background and merges only the planner's "best next changes". Cached designs resolve
 *  instantly with no request; stale responses are dropped by design id. */
export function useWhatIf() {
  const active = useUIStore((s) => s.active);
  const setStorePatch = useUIStore((s) => s.setPatch);
  const applyReport = useUIStore((s) => s.applyReport);
  const applySim = useUIStore((s) => s.applySim);
  const mergeNextExperiments = useUIStore((s) => s.mergeNextExperiments);
  const resetPatch = useUIStore((s) => s.resetPatch);
  const keepAsBaseline = useUIStore((s) => s.keepAsBaseline);
  const [pending, setPending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const patch = active?.patch ?? {};
  const base = active?.baseDesign ?? null;
  const report = active?.report ?? null;
  const sim = active?.sim ?? null;
  const { design: draft, notes } = base
    ? applyWhatIf(base, patch)
    : { design: null, notes: [] as string[] };

  const setPatch = useCallback((p: WhatIfPatch) => setStorePatch(p), [setStorePatch]);

  const commit = useCallback(async () => {
    const st = useUIStore.getState().active;
    if (!st) return;
    const design = activeDesign(st);
    // cache hit (includes returning to the baseline design): nothing to fetch
    if (st.cache[hash6(design)]) return;

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const runs = st.baseReport.runs;
    const seed = st.baseReport.seed;
    setPending(true);
    try {
      // fast path: uncertainty without the planner + the protocol sim, in parallel
      const [fast] = await Promise.all([
        runUncertainty({ design, runs, seed, plan: false }, ctrl.signal),
        runSimulate(design, ctrl.signal)
          .then((s) => applySim(s))
          .catch(() => {/* sim is best-effort; keep the last deck */}),
      ]);
      applyReport(fast);
    } catch {
      /* aborted or failed — keep the last good report */
    } finally {
      if (abortRef.current === ctrl) setPending(false);
    }

    // background: the planner's extra Monte Carlo runs. Update only "best next changes".
    if (ctrl.signal.aborted) return;
    runUncertainty({ design, runs, seed, plan: true }, ctrl.signal)
      .then((planned) => mergeNextExperiments(planned))
      .catch(() => {/* superseded or failed — the fast report already shows */});
  }, [applyReport, applySim, mergeNextExperiments]);

  const dirty = Object.keys(patch).length > 0 && !!base && draft?.design_id !== base.design_id;

  return {
    patch, setPatch, draft, notes, report, sim, base,
    pending, commit, resetPatch, keepAsBaseline, dirty,
    runId: active?.runId ?? null,
  };
}
