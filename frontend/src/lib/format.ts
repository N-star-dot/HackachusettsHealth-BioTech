// Number formats (BRIEF section 8). Tabular lining figures are applied via CSS (.num).

/** Concentration in nM: thousands separators from 1000, 3 sig figs 1-999, 2 below 1. */
export function nM(value: number): string {
  if (!isFinite(value)) return "—";
  if (value >= 1000) return `${Math.round(value).toLocaleString("en-US")} nM`;
  if (value >= 1) return `${sig(value, 3)} nM`;
  return `${sig(value, 2)} nM`;
}

export function uL(value: number): string {
  return `${trimZeros(value)} µL`;
}

/** Fold error like "1.31x". */
export function fold(value: number): string {
  return `${value.toFixed(2)}x`;
}

/** A share as a whole percent, or one decimal below 1%. */
export function pct(share: number): string {
  const p = share * 100;
  if (p > 0 && p < 1) return `${p.toFixed(1)}%`;
  return `${Math.round(p)}%`;
}

/** Probability 0..1 as a whole percent. */
export function prob(p: number): string {
  return `${Math.round(p * 100)}%`;
}

function sig(value: number, digits: number): string {
  if (value === 0) return "0";
  const n = Number(value.toPrecision(digits));
  return trimZeros(n);
}

function trimZeros(n: number): string {
  // avoid scientific notation, drop trailing zeros
  return parseFloat(n.toString()).toString();
}
