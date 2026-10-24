import type { Source } from "../../api/types";

// A number's provenance is one of these shapes (BRIEF 5.15).
export type Provenance =
  | { kind: "source"; source: Source; note?: string }
  | { kind: "simulated"; seed: number; runs: number; sources?: Source[] }
  | { kind: "assumed"; note: string }
  | { kind: "derived"; formula: string; inputs: { label: string; source?: Source }[] };

export const src = (source: Source, note?: string): Provenance => ({ kind: "source", source, note });
export const simulated = (seed: number, runs: number, sources?: Source[]): Provenance =>
  ({ kind: "simulated", seed, runs, sources });
export const assumed = (note: string): Provenance => ({ kind: "assumed", note });
export const derived = (formula: string, inputs: { label: string; source?: Source }[]): Provenance =>
  ({ kind: "derived", formula, inputs });
