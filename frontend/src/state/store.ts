import { create } from "zustand";
import type { AxisKey } from "../api/types";

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

interface UIState {
  question: string;
  settings: Settings;
  weights: Record<AxisKey, number>;
  setQuestion: (q: string) => void;
  setWeight: (axis: AxisKey, value: number) => void;
  resetWeights: () => void;
  setSetting: <K extends keyof Settings>(key: K, value: Settings[K]) => void;
}

export const useUIStore = create<UIState>((set) => ({
  question: "",
  settings: { runs: 1000, seed: 42, readerCv: 0.05 },
  weights: { ...DEFAULT_WEIGHTS },
  setQuestion: (q) => set({ question: q }),
  setWeight: (axis, value) =>
    set((s) => ({ weights: { ...s.weights, [axis]: value } })),
  resetWeights: () => set({ weights: { ...DEFAULT_WEIGHTS } }),
  setSetting: (key, value) =>
    set((s) => ({ settings: { ...s.settings, [key]: value } })),
}));

export { DEFAULT_WEIGHTS };
