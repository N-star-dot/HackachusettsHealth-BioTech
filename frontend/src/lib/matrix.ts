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

/** total = sum(axis_k * w_k) / sum(w); 0 when weights sum to 0. */
export function weightedTotal(
  axes: Record<AxisKey, number>,
  weights: Record<AxisKey, number>,
): number {
  let num = 0;
  let den = 0;
  for (const k of AXES) {
    num += axes[k] * (weights[k] ?? 0);
    den += weights[k] ?? 0;
  }
  return den > 0 ? num / den : 0;
}

/** Contribution of one axis = axis_k * w_k / sum(w). */
export function contribution(
  axis: AxisKey,
  axes: Record<AxisKey, number>,
  weights: Record<AxisKey, number>,
): number {
  let den = 0;
  for (const k of AXES) den += weights[k] ?? 0;
  return den > 0 ? (axes[axis] * (weights[axis] ?? 0)) / den : 0;
}
