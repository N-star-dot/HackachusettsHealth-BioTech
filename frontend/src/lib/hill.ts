// Expected activity + activity color (BRIEF B.5-B.6).
import { interpolateLab } from "d3-interpolate";

/** a(c) = 100 / (1 + (c/ic50)^1), Hill slope 1 (matches the backend engine). */
export function activity(concNM: number, ic50NM: number): number {
  return 100 / (1 + concNM / ic50NM);
}

// Resazurin ramp: blue (0% activity, target shut down) -> pink (100% active).
function cssVar(name: string): string {
  if (typeof document === "undefined") return name === "--inhibited" ? "#3552a0" : "#d2457f";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    || (name === "--inhibited" ? "#3552a0" : "#d2457f");
}

/** Color for a % activity (0..100) on the resazurin ramp. */
export function activityColor(activityPct: number): string {
  const t = Math.max(0, Math.min(1, activityPct / 100));
  return interpolateLab(cssVar("--inhibited"), cssVar("--active"))(t);
}
