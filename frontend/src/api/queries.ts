// React Query hooks (BRIEF 3.4). Query keys include a stable body hash; POST run uses
// retry 0, GETs retry 1.
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, TIMEOUTS } from "./client";
import { hash6 } from "../lib/hash";
import type {
  RunRecord,
  RunRequest,
  RunResponse,
  UncertaintyReport,
  WhatIfRequest,
} from "./types";

export function useRunMutation() {
  return useMutation({
    retry: 0,
    mutationFn: (req: RunRequest) => api.post<RunResponse>("/api/run", req, TIMEOUTS.run),
  });
}

export function useRunRecord(runId: string | null) {
  return useQuery({
    enabled: !!runId,
    retry: 1,
    queryKey: ["run", runId],
    queryFn: () => api.get<RunRecord>(`/api/run/${runId}`),
  });
}

export function useHealth() {
  return useQuery({
    retry: 1,
    queryKey: ["health"],
    queryFn: () => api.get<{ status: string }>("/api/health"),
    refetchInterval: 15_000,
  });
}

/** Imperative what-if call (used by the lab controls with cancellation). */
export function runUncertainty(req: WhatIfRequest, signal?: AbortSignal) {
  return api.post<UncertaintyReport>("/api/uncertainty", req, TIMEOUTS.uncertainty, signal);
}

export function whatIfKey(req: WhatIfRequest): string {
  return `${req.design.design_id}:${hash6(req)}`;
}
