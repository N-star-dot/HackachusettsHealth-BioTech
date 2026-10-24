import { create } from "zustand";
import type {
  AxisKey,
  ExperimentDesign,
  RunResponse,
  SimResult,
  UncertaintyReport,
} from "../api/types";
import { applyWhatIf, type WhatIfPatch } from "../lib/whatif";
import { hash6 } from "../lib/hash";

export interface Settings {
  runs: number;
  seed: number;
  readerCv: number;
}

const DEFAULT_WEIGHTS: Record<AxisKey, number> = {
  momentum: 0.2,
  novelty: 0.2,
  evidence: 0.2,
  automatable: 0.2,
  cost_time: 0.2,
};

interface Pin {
  letter: string;         // A-D
  compound: string;
  tips: number;
  p90: number;
}

/** The one design/report/sim on screen (W1.3). Everything reads from here, so the
 *  notebook and the bench can never show two different answers. Keyed by the run id so a
 *  new run starts from a clean baseline. */
interface ActiveRun {
  runId: string;
  baseDesign: ExperimentDesign;   // the run's designed values (the baseline)
  baseReport: UncertaintyReport;
  baseSim: SimResult | null;
  patch: WhatIfPatch;             // the current what-if (empty == baseline)
  report: UncertaintyReport;      // the report for the active design (baseline or what-if)
  sim: SimResult | null;          // the sim for the active design
  cache: Record<string, UncertaintyReport>;  // what-if reports by design hash
}

interface UIState {
  question: string;
  settings: Settings;
  weights: Record<AxisKey, number>;
  pins: Pin[];
  active: ActiveRun | null;
  setQuestion: (q: string) => void;
  setWeight: (axis: AxisKey, value: number) => void;
  resetWeights: () => void;
  setSetting: <K extends keyof Settings>(key: K, value: Settings[K]) => void;
  addPin: (compound: string, tips: number, p90: number) => void;
  removePin: (letter: string) => void;
  // W1.3 active-run actions
  loadRun: (run: RunResponse) => void;
  setPatch: (patch: WhatIfPatch) => void;
  resetPatch: () => void;
  keepAsBaseline: () => void;
  applyReport: (report: UncertaintyReport) => void;
  mergeNextExperiments: (reportWithPlan: UncertaintyReport) => void;
  applySim: (sim: SimResult) => void;
  cachedReport: (design: ExperimentDesign) => UncertaintyReport | undefined;
}

/** The active design = baseDesign with the current patch applied. */
export function activeDesign(active: ActiveRun): ExperimentDesign {
  return applyWhatIf(active.baseDesign, active.patch).design;
}

export const useUIStore = create<UIState>((set, get) => ({
  question: "",
  settings: { runs: 1000, seed: 42, readerCv: 0.05 },
  weights: { ...DEFAULT_WEIGHTS },
  pins: [],
  active: null,
  setQuestion: (q) => set({ question: q }),
  setWeight: (axis, value) =>
    set((s) => ({ weights: { ...s.weights, [axis]: value } })),
  resetWeights: () => set({ weights: { ...DEFAULT_WEIGHTS } }),
  setSetting: (key, value) =>
    set((s) => ({ settings: { ...s.settings, [key]: value } })),
  addPin: (compound, tips, p90) =>
    set((s) => {
      if (s.pins.length >= 4) return s;
      const letter = "ABCD"[s.pins.length];
      return { pins: [...s.pins, { letter, compound, tips, p90 }] };
    }),
  removePin: (letter) => set((s) => ({ pins: s.pins.filter((p) => p.letter !== letter) })),

  loadRun: (run) => {
    // Only (re)seed when the run or its design actually changed, so re-renders of the
    // same run keep the active what-if state. A blocked/partial run clears it.
    if (!run.design || !run.uncertainty) {
      set({ active: null });
      return;
    }
    const prev = get().active;
    if (prev && prev.runId === run.run_id && prev.baseDesign.design_id === run.design.design_id) {
      return;
    }
    const key = hash6(run.design);
    set({
      active: {
        runId: run.run_id,
        baseDesign: run.design,
        baseReport: run.uncertainty,
        baseSim: run.sim,
        patch: {},
        report: run.uncertainty,
        sim: run.sim,
        cache: { [key]: run.uncertainty },
      },
    });
  },

  setPatch: (patch) =>
    set((s) => {
      if (!s.active) return s;
      // Live geometry updates immediately; the report for this draft comes from cache if we
      // have it (instant, no request), otherwise we keep the last report until commit lands.
      const design = applyWhatIf(s.active.baseDesign, patch).design;
      const cached = s.active.cache[hash6(design)];
      return {
        active: {
          ...s.active,
          patch,
          report: cached ?? s.active.report,
        },
      };
    }),

  resetPatch: () =>
    set((s) => {
      if (!s.active) return s;
      return { active: { ...s.active, patch: {}, report: s.active.baseReport, sim: s.active.baseSim } };
    }),

  keepAsBaseline: () =>
    set((s) => {
      if (!s.active) return s;
      const design = applyWhatIf(s.active.baseDesign, s.active.patch).design;
      return {
        active: {
          ...s.active,
          baseDesign: design,
          baseReport: s.active.report,
          baseSim: s.active.sim,
          patch: {},
        },
      };
    }),

  applyReport: (report) =>
    set((s) => {
      if (!s.active) return s;
      // Only accept a report for the current draft design; drop stale ones.
      const design = applyWhatIf(s.active.baseDesign, s.active.patch).design;
      if (report.design_id !== design.design_id) return s;
      return {
        active: {
          ...s.active,
          report,
          cache: { ...s.active.cache, [hash6(design)]: report },
        },
      };
    }),

  applySim: (sim) =>
    set((s) => {
      if (!s.active) return s;
      const design = applyWhatIf(s.active.baseDesign, s.active.patch).design;
      if (sim.design_id !== design.design_id) return s;
      return { active: { ...s.active, sim } };
    }),

  mergeNextExperiments: (reportWithPlan) =>
    set((s) => {
      if (!s.active) return s;
      // Only the planner's next_experiments; keep the fast report's fold_error etc. Guard
      // the design_id so a late plan:true response can't attach to a newer draft.
      const design = applyWhatIf(s.active.baseDesign, s.active.patch).design;
      if (reportWithPlan.design_id !== design.design_id) return s;
      const merged: UncertaintyReport = {
        ...s.active.report,
        next_experiments: reportWithPlan.next_experiments,
      };
      return {
        active: {
          ...s.active,
          report: merged,
          cache: { ...s.active.cache, [hash6(design)]: merged },
        },
      };
    }),

  cachedReport: (design) => get().active?.cache[hash6(design)],
}));

export { DEFAULT_WEIGHTS };
