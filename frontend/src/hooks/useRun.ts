import { useCallback, useEffect, useRef, useState } from "react";
import { api, TIMEOUTS } from "../api/client";
import { loadRecordedRun } from "../api/recorded";
import { useUIStore } from "../state/store";
import type { RunRecord, RunResponse } from "../api/types";

export type RunOrigin = "live" | "recorded" | null;

const POLL_MS = 500;
const TERMINAL = new Set(["done", "error"]);

/** Owns the current run (W1.4): fires POST /api/run in async mode and polls
 *  GET /api/run/{id} every 500 ms so each stage reveals as its report lands. Falls back
 *  to a recorded run or a shared run id. Exposes the live pipeline status for the stage
 *  strip. */
export function useRun() {
  const weights = useUIStore((s) => s.weights);
  const settings = useUIStore((s) => s.settings);
  const [run, setRun] = useState<RunResponse | null>(null);
  const [origin, setOrigin] = useState<RunOrigin>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeRunId = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const poll = useCallback((runId: string) => {
    stopPolling();
    const tick = async () => {
      if (activeRunId.current !== runId) return;
      try {
        const rec = await api.get<RunRecord>(`/api/run/${runId}`);
        if (activeRunId.current !== runId) return;   // a newer run started; drop this
        setRun(rec);
        if (TERMINAL.has(rec.meta?.status ?? "")) {
          stopPolling();
          setIsRunning(false);
          if (rec.meta?.status === "error") setError(new Error(rec.meta.error ?? "Run failed"));
        }
      } catch (e) {
        stopPolling();
        setIsRunning(false);
        setError(e);
      }
    };
    pollRef.current = setInterval(tick, POLL_MS);
    tick();   // fire immediately so the first stage can show up fast
  }, [stopPolling]);

  const start = useCallback(
    (query: string) => {
      stopPolling();
      setRun(null);
      setError(null);
      setIsRunning(true);
      setOrigin("live");
      api
        .post<RunResponse>(
          "/api/run",
          {
            query,
            weights,
            runs: settings.runs,
            seed: settings.seed,
            reader_cv: settings.readerCv,
            mode: "async",
          },
          TIMEOUTS.run,
        )
        .then((res) => {
          activeRunId.current = res.run_id;
          poll(res.run_id);
        })
        .catch((e) => {
          setIsRunning(false);
          setError(e);
        });
    },
    [weights, settings, poll, stopPolling],
  );

  const openRecorded = useCallback(async (file: string) => {
    stopPolling();
    activeRunId.current = null;
    const data = await loadRecordedRun(file);
    if (data) { setRun(data); setOrigin("recorded"); setIsRunning(false); }
  }, [stopPolling]);

  const openRunId = useCallback(async (runId: string) => {
    stopPolling();
    try {
      const rec = await api.get<RunRecord>(`/api/run/${runId}`);
      activeRunId.current = runId;
      setRun(rec);
      setOrigin("live");
      // a shared run that is still computing resumes polling
      if (!TERMINAL.has(rec.meta?.status ?? "done")) { setIsRunning(true); poll(runId); }
    } catch {
      /* unknown run id — leave the start screen up */
    }
  }, [stopPolling, poll]);

  const reset = useCallback((value: RunResponse | null) => {
    stopPolling();
    activeRunId.current = null;
    setRun(value);
    setIsRunning(false);
    setError(null);
  }, [stopPolling]);

  return {
    run,
    origin,
    start,
    openRecorded,
    openRunId,
    isRunning,
    error,
    setRun: reset,
  };
}
