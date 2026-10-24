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

interface Pin {
  letter: string;         // A-D
  compound: string;
  tips: number;
  p90: number;
}

interface UIState {
  question: string;
  settings: Settings;
  weights: Record<AxisKey, number>;
  pins: Pin[];
  setQuestion: (q: string) => void;
  setWeight: (axis: AxisKey, value: number) => void;
  resetWeights: () => void;
  setSetting: <K extends keyof Settings>(key: K, value: Settings[K]) => void;
  addPin: (compound: string, tips: number, p90: number) => void;
  removePin: (letter: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  question: "",
  settings: { runs: 1000, seed: 42, readerCv: 0.05 },
  weights: { ...DEFAULT_WEIGHTS },
  pins: [],
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
}));

export { DEFAULT_WEIGHTS };
