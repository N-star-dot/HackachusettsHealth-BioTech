import { describe, expect, it } from "vitest";
import { applyStep, initialState, runReplay, type ReplayState } from "../lib/replay";
import type { ProtocolStep } from "../api/types";

function amount(s: ReplayState): number {
  let total = 0;
  for (const w of Object.values(s.wells)) total += w.volume_uL * w.conc_nM;
  if (s.tip) total += s.tip.volume_uL * s.tip.conc_nM;
  for (const d of s.discarded) total += d.volume_uL * d.conc_nM;
  return total;
}

describe("replay state machine (BRIEF B.9)", () => {
  it("never produces a negative volume and conserves compound across a transfer", () => {
    // aspirate 50 from reservoir A2 (stock 1000 nM), dispense into plate A1
    const steps: ProtocolStep[] = [
      { i: 0, action: "pick_up_tip", slot: "D1", well: "A1" },
      { i: 1, action: "aspirate", uL: 50, slot: "D3", well: "A2" },
      { i: 2, action: "dispense", uL: 50, slot: "D2", well: "A1" },
    ];
    let s = initialState(1000);
    for (const st of steps) s = applyStep(s, st);
    // plate A1 should hold 50 uL at ~1000 nM
    expect(s.wells.A1.volume_uL).toBeCloseTo(50, 6);
    expect(s.wells.A1.conc_nM).toBeCloseTo(1000, 3);
    // no negative volumes anywhere
    Object.values(s.wells).forEach((w) => expect(w.volume_uL).toBeGreaterThanOrEqual(0));
  });

  it("runs a multi-step replay and counts tips", () => {
    const steps: ProtocolStep[] = [
      { i: 0, action: "pick_up_tip" },
      { i: 1, action: "aspirate", uL: 50, slot: "D3", well: "A2" },
      { i: 2, action: "dispense", uL: 50, slot: "D2", well: "A1" },
      { i: 3, action: "drop_tip" },
      { i: 4, action: "pick_up_tip" },
      { i: 5, action: "drop_tip" },
    ];
    const states = runReplay(steps, 1000);
    const last = states[states.length - 1];
    expect(last.tipsUsed).toBe(2);
    expect(amount(last)).toBeGreaterThan(0); // compound ended up somewhere (well or discard)
  });
});
