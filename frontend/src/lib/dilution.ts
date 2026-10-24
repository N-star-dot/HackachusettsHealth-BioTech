// Dilution geometry (BRIEF B.2-B.4).

/** c_i = top_nM / factor^i for i in 0..points-1. */
export function concentrations(topNM: number, factor: number, points: number): number[] {
  return Array.from({ length: points }, (_, i) => topNM / factor ** i);
}

export function bottomNM(topNM: number, factor: number, points: number): number {
  return topNM / factor ** (points - 1);
}

/** Coverage of the prior: log10 units above and below the prior median (B.3). */
export function coverage(topNM: number, factor: number, points: number, priorNM: number) {
  const above = Math.log10(topNM / priorNM);
  const below = Math.log10(priorNM / bottomNM(topNM, factor, points));
  return { above, below };
}

/** Designer's target half-width h = max(2, 1.645 * spread) (B.4). */
export function targetHalfWidth(spreadLog10: number): number {
  return Math.max(2, 1.645 * spreadLog10);
}
