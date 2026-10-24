import { useCallback, useRef, useState } from "react";
import { runUncertainty } from "../api/queries";
import { applyWhatIf, type WhatIfPatch } from "../lib/whatif";
import { hash6 } from "../lib/hash";
import { activeDesign, useUIStore } from "../state/store";

/** Controller for the what-if draft (W1.3). The draft, report and sim all live in the
 *  store under the active run, so the notebook and the bench read the same numbers and a
 *  new run starts clean. This hook only drives the debounced server call on release
 *  (plan=true), cancelling any in-flight request and dropping stale responses; cached
 *  designs resolve instantly with no request. */
export function useWhatIf() {
  const active = useUIStore((s) => s.active);
  const setStorePatch = useUIStore((s) => s.setPatch);
  const applyReport = useUIStore((s) => s.applyReport);
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
    setPending(true);
    try {
      const res = await runUncertainty(
        { design, runs: st.baseReport.runs, seed: st.baseReport.seed, plan: true },
        ctrl.signal,
      );
      applyReport(res);
    } catch {
      /* aborted or failed — keep the last good report */
    } finally {
      if (abortRef.current === ctrl) setPending(false);
    }
  }, [applyReport]);

  const dirty = Object.keys(patch).length > 0 && !!base && draft?.design_id !== base.design_id;

  return {
    patch, setPatch, draft, notes, report, sim, base,
    pending, commit, resetPatch, keepAsBaseline, dirty,
    runId: active?.runId ?? null,
  };
}
