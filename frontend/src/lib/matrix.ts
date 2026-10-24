// Viability matrix math (BRIEF B.1). Matches the backend's weighted_total exactly.
import type { AxisKey } from "../api/types";

export const AXES: AxisKey[] = ["momentum", "novelty", "evidence", "automatable", "cost_time"];

export const AXIS_MEANING: Record<AxisKey, string> = {
  momentum: "How likely the field is to grow.",
  novelty: "How uncrowded the topic is.",
  evidence: "How much published data gives a starting point.",
  automatable: "Whether a robot can run the first experiment.",
  cost_time: "How cheap and quick the first experiment is.",
};

export const AXIS_LABEL: Record<AxisKey, string> = {
  momentum: "Momentum",
  novelty: "Novelty gap",
  evidence: "Evidence",
  automatable: "Automatable",
  cost_time: "Cost and time",
};

/** total = sum(axis_k * w_k) / sum(w) over the available axes; 0 when weights sum to 0.
 *  Axes in `unavailable` are excluded from both numerator and weight sum (H2). */
export function weightedTotal(
  axes: Record<AxisKey, number>,
  weights: Record<AxisKey, number>,
  unavailable: readonly string[] = [],
): number {
  const skip = new Set(unavailable);
  let num = 0;
  let den = 0;
  for (const k of AXES) {
    if (skip.has(k)) continue;
    num += axes[k] * (weights[k] ?? 0);
    den += weights[k] ?? 0;
  }
  return den > 0 ? num / den : 0;
}

/** Contribution of one axis = axis_k * w_k / sum(w) over the available axes. */
export function contribution(
  axis: AxisKey,
  axes: Record<AxisKey, number>,
  weights: Record<AxisKey, number>,
  unavailable: readonly string[] = [],
): number {
  if (unavailable.includes(axis)) return 0;
  const skip = new Set(unavailable);
  let den = 0;
  for (const k of AXES) { if (!skip.has(k)) den += weights[k] ?? 0; }
  return den > 0 ? (axes[axis] * (weights[axis] ?? 0)) / den : 0;
}
