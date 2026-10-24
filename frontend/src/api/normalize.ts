// The ONLY module that knows backend quirks (BRIEF 3.1 / rule R0.6). Everything else
// reads the normalized shapes below.

import type {
  ExperimentDesign,
  RunRecord,
  RunResponse,
  SimResult,
  TopicReport,
} from "./types";

/** safety.pass (POST) vs safety.passed (GET) -> a single `ok` boolean. */
export function gateOk(gate: { pass?: boolean; passed?: boolean } | undefined): boolean {
  if (!gate) return false;
  return gate.pass ?? gate.passed ?? false;
}

/** Stage-1 counts are offline/invented when the topic id is the T00000 placeholder or
 *  the backend flags offline. Callers must NOT draw offline counts as real. */
export function isOfflineTopic(topic: TopicReport | null): boolean {
  if (!topic) return false;
  return topic.offline === true || topic.topic.openalex_id === "T00000";
}

/** Drop the legacy placeholder neighbor (id T00001 / name starting "placeholder"). */
export function realNeighbors(topic: TopicReport | null) {
  if (!topic) return [];
  return topic.neighbors.filter(
    (n) => n.openalex_id !== "T00001" && !n.name.toLowerCase().startsWith("placeholder"),
  );
}

/** An axis value is "assumed" (a fixed prior, not computed) when its source says so. */
export function axisIsAssumed(topic: TopicReport | null, axis: string): boolean {
  const sources = topic?.matrix.axis_sources as Record<string, { type: string }> | undefined;
  return sources?.[axis]?.type === "assumed";
}

/** Cost counted from the run log vs estimated by formula. */
export function costIsCounted(sim: SimResult | null): boolean {
  return sim?.cost.source?.type === "simulator";
}

/** The simulator verdict as a single boolean. */
export function simOk(sim: SimResult | null): boolean {
  if (!sim) return false;
  return gateOk(sim.simulator);
}

/** Steps are replayable only when they carry structured text (B0.4). */
export function isReplayable(sim: SimResult | null): boolean {
  return !!sim && sim.steps.length > 0 && sim.steps.some((s) => (s.text ?? "").length > 0);
}

/** Verified-rationale summary for the review thread. */
export function verifiedCount(design: ExperimentDesign | null): { verified: number; total: number } {
  if (!design) return { verified: 0, total: 0 };
  const total = design.rationale.length;
  const verified = design.rationale.filter((r) => r.status === "verified").length;
  return { verified, total };
}

/** A RunResponse (POST) and a RunRecord (GET) share this shape for the UI. */
export interface NormalizedRun {
  runId: string;
  blocked: boolean;
  status: string;
  response: RunResponse;
}

export function normalizeRun(raw: RunResponse | RunRecord): NormalizedRun {
  const status = (raw as RunRecord).meta?.status ?? raw.status ?? "done";
  return { runId: raw.run_id, blocked: raw.blocked, status, response: raw };
}
