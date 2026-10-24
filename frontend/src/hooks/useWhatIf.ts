// Keeps the uncertainty report in sync with the design the user is editing.
// In live mode, shortly after the sliders stop moving it reruns stage 4; the
// previous request is aborted so only the latest result lands. When the design
// is reset to the run's baseline, it snaps back to that run's own report.

import { useEffect, useRef, useState } from "react";
import { rerunUncertainty } from "../api";
import { SEED } from "./useRun";
import type { ExperimentDesign, RunResponse, UncertaintyReport } from "../types";

const DEBOUNCE_MS = 350;

interface Params {
  live: boolean;
  runs: number;
  run: RunResponse;
  design: ExperimentDesign | null;
  setUncertainty: (u: UncertaintyReport | null) => void;
}

export interface WhatIfState {
  pending: boolean;
  error: string | null;
}

export function useWhatIf({ live, runs, run, design, setUncertainty }: Params): WhatIfState {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  const isBaseline = design === run.design;

  // Recompute stage 4 for an edited design (live mode only), debounced.
  useEffect(() => {
    if (!live || !design || isBaseline) return;

    const timer = window.setTimeout(async () => {
      abort.current?.abort();
      const ctrl = new AbortController();
      abort.current = ctrl;
      setPending(true);
      setError(null);
      try {
        setUncertainty(await rerunUncertainty(design, runs, SEED, ctrl.signal));
      } catch (err) {
        if ((err as Error).name !== "AbortError") setError((err as Error).message);
      } finally {
        if (abort.current === ctrl) setPending(false);
      }
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [live, runs, design, isBaseline, setUncertainty]);

  // Design reset to baseline: show the run's own report again.
  useEffect(() => {
    if (isBaseline) {
      setError(null);
      setUncertainty(run.uncertainty);
    }
  }, [isBaseline, run, setUncertainty]);

  return { pending, error };
}
