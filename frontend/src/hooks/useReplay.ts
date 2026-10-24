// Playback state for the robot run replay: which step we're on, play/pause, speed,
// and the derived set of filled wells plus the currently active well. Steps come
// from the simulator, or from demo steps when the SimResult is too short to animate.

import { useEffect, useMemo, useState } from "react";
import type { ExperimentDesign, ProtocolStep, SimResult } from "../types";

export const ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"];
export const COLS = Array.from({ length: 12 }, (_, i) => i + 1);

const BASE_STEP_MS = 400;

/** A plate step is one that targets a well on labware whose name mentions "plate". */
function isPlateStep(s: ProtocolStep): boolean {
  return !!s.well && !!s.labware && s.labware.toLowerCase().includes("plate");
}

/**
 * Stand-in steps built from the design, used only when the SimResult carries fewer
 * than two steps (the mock has one). Labelled "demo steps" in the UI so nobody
 * mistakes them for the simulator's own output.
 */
function demoSteps(design: ExperimentDesign): ProtocolStep[] {
  const steps: ProtocolStep[] = [];
  const reps = Math.min(design.replicates, ROWS.length);
  const points = Math.min(design.dilution.points, COLS.length);
  const uL = design.volumes_uL.transfer;
  const push = (s: Omit<ProtocolStep, "i">) => steps.push({ i: steps.length, ...s });

  for (let r = 0; r < reps; r++) {
    for (let p = 0; p < points; p++) {
      push({ action: "pick_up_tip", labware: "tiprack" });
      push({ action: "aspirate", uL, labware: "reservoir", well: "A1" });
      push({ action: "dispense", uL, labware: "plate", well: `${ROWS[r]}${p + 1}` });
      push({ action: "drop_tip", labware: "trash" });
    }
  }
  return steps;
}

export interface Replay {
  isDemo: boolean;
  steps: ProtocolStep[];
  step: number;
  last: number;
  playing: boolean;
  speed: number;
  current: ProtocolStep | undefined;
  filled: Set<string>;
  activeWell: string | null;
  windowStart: number;
  log: ProtocolStep[];
  setSpeed: (n: number) => void;
  seek: (i: number) => void;
  togglePlay: () => void;
}

export function useReplay(sim: SimResult, design: ExperimentDesign | null): Replay {
  const isDemo = sim.steps.length < 2 && !!design;
  const steps = useMemo(
    () => (isDemo && design ? demoSteps(design) : sim.steps),
    [isDemo, design, sim.steps],
  );
  const last = Math.max(0, steps.length - 1);

  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(4);

  // New set of steps: rewind to the start and stop.
  useEffect(() => {
    setStep(0);
    setPlaying(false);
  }, [steps]);

  // Advance one step at a time while playing; stop at the end.
  useEffect(() => {
    if (!playing) return;
    if (step >= last) {
      setPlaying(false);
      return;
    }
    const t = window.setTimeout(() => setStep((s) => Math.min(s + 1, last)), BASE_STEP_MS / speed);
    return () => window.clearTimeout(t);
  }, [playing, step, last, speed]);

  const current = steps[step];

  const filled = useMemo(() => {
    const set = new Set<string>();
    for (let i = 0; i <= step && i < steps.length; i++) {
      const s = steps[i];
      if (isPlateStep(s) && s.action.startsWith("dispense")) set.add(s.well!.toUpperCase());
    }
    return set;
  }, [steps, step]);

  const activeWell = current && isPlateStep(current) ? current.well!.toUpperCase() : null;
  const windowStart = Math.max(0, step - 4);
  const log = steps.slice(windowStart, step + 1);

  function seek(i: number) {
    setPlaying(false);
    setStep(i);
  }

  function togglePlay() {
    if (step >= last) setStep(0);
    setPlaying((p) => !p);
  }

  return {
    isDemo,
    steps,
    step,
    last,
    playing,
    speed,
    current,
    filled,
    activeWell,
    windowStart,
    log,
    setSpeed,
    seek,
    togglePlay,
  };
}
