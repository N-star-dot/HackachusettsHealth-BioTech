// Owns the current run: the topic/design/sim/uncertainty payload, the working
// copy of the weights and design the user edits, and the call that fetches a new
// run (or loads the mocks). App reads this as plain state and setters.

import { useState } from "react";
import { mockRun, runPipeline, type DataMode } from "../api";
import type { ExperimentDesign, RunResponse, UncertaintyReport, Weights } from "../types";

export const SEED = 42;

export interface RunState {
  run: RunResponse;
  weights: Weights;
  setWeights: (w: Weights) => void;
  design: ExperimentDesign | null;
  setDesign: (d: ExperimentDesign | null) => void;
  uncertainty: UncertaintyReport | null;
  setUncertainty: (u: UncertaintyReport | null) => void;
  loading: boolean;
  error: string | null;
  /** Load the mocks (mock mode) or call the pipeline (api mode). */
  submit: (mode: DataMode, query: string, runs: number) => Promise<void>;
}

export function useRun(): RunState {
  const [run, setRun] = useState<RunResponse>(() => mockRun());
  const [weights, setWeights] = useState<Weights>(run.topic.matrix.weights);
  const [design, setDesign] = useState<ExperimentDesign | null>(run.design);
  const [uncertainty, setUncertainty] = useState<UncertaintyReport | null>(run.uncertainty);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** Replace the whole run and reset the working copies the user edits. */
  function adopt(next: RunResponse) {
    setRun(next);
    setWeights(next.topic.matrix.weights);
    setDesign(next.design);
    setUncertainty(next.uncertainty);
  }

  async function submit(mode: DataMode, query: string, runs: number) {
    setError(null);
    if (mode === "mock") {
      adopt(mockRun(query));
      return;
    }
    setLoading(true);
    try {
      adopt(await runPipeline({ query, runs, seed: SEED, weights }));
    } catch (err) {
      setError(
        `${(err as Error).message}. Is the backend running? (uvicorn backend.api:app --reload)`,
      );
    } finally {
      setLoading(false);
    }
  }

  return {
    run,
    weights,
    setWeights,
    design,
    setDesign,
    uncertainty,
    setUncertainty,
    loading,
    error,
    submit,
  };
}
