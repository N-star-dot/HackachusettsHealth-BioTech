import type { Source } from "./types";

export const fmt = {
  num: (n: number, digits = 2) => n.toFixed(digits),
  int: (n: number) => Math.round(n).toLocaleString("en-US"),
  pct: (share: number, digits = 1) => `${(share * 100).toFixed(digits)}%`,
  fold: (n: number) => `${n.toFixed(2)}×`,
  nM: (n: number) => `${n.toLocaleString("en-US", { maximumFractionDigits: 2 })} nM`,
  uL: (n: number) => `${n.toLocaleString("en-US", { maximumFractionDigits: 1 })} µL`,
};

/** A provenance tag for values our own Monte Carlo produced. */
export function simulated(seed: number, runs?: number): Source {
  return { type: "simulated", id: runs ? `seed ${seed} · ${runs.toLocaleString("en-US")} runs` : `seed ${seed}` };
}

const LABELS: Record<Source["type"], string> = {
  openalex: "OpenAlex",
  pubmed: "PubMed",
  chembl_activity: "ChEMBL activity",
  semantic_scholar: "Semantic Scholar",
  paper: "Paper",
  spec: "Spec sheet",
  simulator: "Opentrons simulator",
  simulated: "Simulated",
};

export function sourceLabel(s: Source): string {
  return LABELS[s.type] ?? s.type;
}

/** Best-effort link for a source when the backend did not send a url. */
export function sourceHref(s: Source): string | undefined {
  if (s.url) return s.url;
  if (s.type === "openalex" && /^T\d+$/.test(s.id)) return `https://openalex.org/topics/${s.id}`;
  if (s.type === "pubmed" && /^\d+$/.test(s.id)) return `https://pubmed.ncbi.nlm.nih.gov/${s.id}/`;
  if (s.type === "paper" && s.id.startsWith("doi:")) return `https://doi.org/${s.id.slice(4)}`;
  return undefined;
}
