import { useCallback, useEffect, useRef, useState } from "react";
import { api, TIMEOUTS } from "../api/client";
import { loadRecordedRun } from "../api/recorded";
import { useUIStore } from "../state/store";
import type { RunRecord, RunResponse } from "../api/types";

export type RunOrigin = "live" | "recorded" | null;

const POLL_MS = 500;
const TERMINAL = new Set(["done", "error"]);

/** Owns the current run (W1.4). Polling is driven by a single effect keyed on `runId`, so
 *  starting a second run can never leave a stale interval or a dropped poll (the
 *  "stuck at design on the second topic" bug): changing runId tears down the old poll and
 *  starts a fresh one. */
export function useRun() {
  const weights = useUIStore((s) => s.weights);
  const settings = useUIStore((s) => s.settings);
  const [run, setRun] = useState<RunResponse | null>(null);
  const [origin, setOrigin] = useState<RunOrigin>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<unknown>(null);
  // The run we are actively polling. null = not polling. A "poll token" (incrementing) is
  // bumped on every start so even same-id edge cases restart cleanly.
  const [pollTarget, setPollTarget] = useState<{ runId: string; token: number } | null>(null);
  const tokenRef = useRef(0);

  // Single source of truth for polling. Re-runs whenever the poll target changes; its
  // cleanup clears the interval, so a new run always cancels the previous poll.
  useEffect(() => {
    if (!pollTarget) return;
    const { runId, token } = pollTarget;
    let stopped = false;

    const tick = async () => {
      if (stopped || token !== tokenRef.current) return;
      try {
        const rec = await api.get<RunRecord>(`/api/run/${runId}`);
        if (stopped || token !== tokenRef.current) return;
        setRun(rec);
        const status = rec.meta?.status ?? "";
        if (TERMINAL.has(status)) {
          setIsRunning(false);
          if (status === "error") setError(new Error(rec.meta?.error ?? "Run failed"));
          setPollTarget(null); // stop
        }
      } catch (e) {
        if (stopped || token !== tokenRef.current) return;
        setIsRunning(false);
        setError(e);
        setPollTarget(null);
      }
    };

    const id = setInterval(tick, POLL_MS);
    tick(); // fire immediately so the first stage shows up fast
    return () => { stopped = true; clearInterval(id); };
  }, [pollTarget]);

  const start = useCallback(
    (query: string) => {
      const token = ++tokenRef.current;
      setPollTarget(null);          // stop any current poll immediately
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
          if (token !== tokenRef.current) return; // a newer run started meanwhile
          setPollTarget({ runId: res.run_id, token });
        })
        .catch((e) => {
          if (token !== tokenRef.current) return;
          setIsRunning(false);
          setError(e);
        });
    },
    [weights, settings],
  );

  const openRecorded = useCallback(async (file: string) => {
    ++tokenRef.current;
    setPollTarget(null);
    const data = await loadRecordedRun(file);
    if (data) { setRun(data); setOrigin("recorded"); setIsRunning(false); }
  }, []);

  const openRunId = useCallback(async (runId: string) => {
    const token = ++tokenRef.current;
    setPollTarget(null);
    try {
      const rec = await api.get<RunRecord>(`/api/run/${runId}`);
      if (token !== tokenRef.current) return;
      setRun(rec);
      setOrigin("live");
      if (!TERMINAL.has(rec.meta?.status ?? "done")) {
        setIsRunning(true);
        setPollTarget({ runId, token }); // resume polling a still-computing shared run
      }
    } catch {
      /* unknown run id — leave the start screen up */
    }
  }, []);

  const reset = useCallback((value: RunResponse | null) => {
    ++tokenRef.current;
    setPollTarget(null);
    setRun(value);
    setIsRunning(false);
    setError(null);
  }, []);

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
