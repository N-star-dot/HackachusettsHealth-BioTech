import { useCallback, useState } from "react";
import { useRunMutation } from "../api/queries";
import { loadRecordedRun } from "../api/recorded";
import { useUIStore } from "../state/store";
import type { RunResponse } from "../api/types";

export type RunOrigin = "live" | "recorded" | null;

/** Owns the current run: fires POST /api/run (live) or loads a recorded run, and exposes
 *  the normalized RunResponse for the workspace. */
export function useRun() {
  const mutation = useRunMutation();
  const weights = useUIStore((s) => s.weights);
  const settings = useUIStore((s) => s.settings);
  const [run, setRun] = useState<RunResponse | null>(null);
  const [origin, setOrigin] = useState<RunOrigin>(null);

  const start = useCallback(
    (query: string) => {
      setOrigin("live");
      mutation.mutate(
        {
          query,
          weights,
          runs: settings.runs,
          seed: settings.seed,
          reader_cv: settings.readerCv,
        },
        { onSuccess: (data) => setRun(data) },
      );
    },
    [mutation, weights, settings],
  );

  const openRecorded = useCallback(async (file: string) => {
    const data = await loadRecordedRun(file);
    if (data) {
      setRun(data);
      setOrigin("recorded");
    }
  }, []);

  return {
    run,
    origin,
    start,
    openRecorded,
    isRunning: mutation.isPending,
    error: mutation.error,
    setRun,
  };
}
