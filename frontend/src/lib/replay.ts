// Replay state machine (BRIEF B.9). Pure and unit-tested: apply each leaf step to a
// well/reservoir/tip model, conserving compound amount and never going negative.
import type { ProtocolStep } from "../api/types";

export interface Liquid { volume_uL: number; conc_nM: number }
export type Wells = Record<string, Liquid>;

export interface ReplayState {
  wells: Wells;        // plate wells by id (e.g. "A1")
  reservoir: Wells;    // reservoir wells: A1 diluent, A2 compound stock
  tip: Liquid | null;  // what the current tip holds
  discarded: Liquid[]; // dropped-tip / blow-out liquid
  tipsUsed: number;
  warnings: string[];
}

const LEAF = new Set(["pick_up_tip", "drop_tip", "aspirate", "dispense", "mix", "blow_out"]);

export function leafSteps(steps: ProtocolStep[]): ProtocolStep[] {
  return steps.filter((s) => LEAF.has(s.action));
}

export function initialState(topNM: number): ReplayState {
  return {
    wells: {},
    reservoir: {
      A1: { volume_uL: 1e9, conc_nM: 0 },      // diluent
      A2: { volume_uL: 1e9, conc_nM: topNM },  // compound stock
    },
    tip: null,
    discarded: [],
    tipsUsed: 0,
    warnings: [],
  };
}

function mix(a: Liquid, vol: number, conc: number): Liquid {
  const total = a.volume_uL + vol;
  if (total <= 0) return { volume_uL: 0, conc_nM: 0 };
  return { volume_uL: total, conc_nM: (a.volume_uL * a.conc_nM + vol * conc) / total };
}

/** Apply one leaf step in place, returning a new state (immutably). */
export function applyStep(state: ReplayState, step: ProtocolStep): ReplayState {
  const s: ReplayState = {
    ...state,
    wells: { ...state.wells },
    reservoir: { ...state.reservoir },
    discarded: [...state.discarded],
    warnings: [...state.warnings],
  };
  const vol = step.uL ?? 0;

  const srcWell = (loc?: { slot: string | null; well: string | null } | null, well?: string | null) => {
    const w = loc?.well ?? well ?? null;
    const slot = loc?.slot ?? step.slot ?? null;
    return { w, slot };
  };

  switch (step.action) {
    case "pick_up_tip":
      s.tip = { volume_uL: 0, conc_nM: 0 };
      s.tipsUsed += 1;
      break;
    case "drop_tip":
      if (s.tip) s.discarded.push(s.tip);
      s.tip = null;
      break;
    case "blow_out":
      if (s.tip) { s.discarded.push(s.tip); s.tip = { volume_uL: 0, conc_nM: 0 }; }
      break;
    case "aspirate": {
      const { w, slot } = srcWell(step.source ?? null, step.well);
      if (!s.tip) s.tip = { volume_uL: 0, conc_nM: 0 };
      const pool = slot === "D3" ? s.reservoir : s.wells;
      const from = w ? pool[w] : undefined;
      const conc = from ? from.conc_nM : 0;
      if (from && slot !== "D3") {
        const take = Math.min(vol, from.volume_uL);
        if (take < vol) s.warnings.push(`${w}: aspirated more than it held`);
        pool[w!] = { volume_uL: from.volume_uL - take, conc_nM: from.conc_nM };
      }
      s.tip = mix(s.tip, vol, conc);
      break;
    }
    case "dispense": {
      const { w, slot } = srcWell(step.dest ?? null, step.well);
      if (w && slot !== "D3") {
        const cur = s.wells[w] ?? { volume_uL: 0, conc_nM: 0 };
        const give = s.tip ? Math.min(vol, s.tip.volume_uL || vol) : vol;
        const conc = s.tip ? s.tip.conc_nM : 0;
        s.wells[w] = mix(cur, give, conc);
        if (s.tip) s.tip = { volume_uL: Math.max(0, s.tip.volume_uL - give), conc_nM: s.tip.conc_nM };
      }
      break;
    }
    case "mix":
      // mixing doesn't change totals
      break;
  }
  return s;
}

export function runReplay(steps: ProtocolStep[], topNM: number): ReplayState[] {
  const leaves = leafSteps(steps);
  const states: ReplayState[] = [initialState(topNM)];
  for (const step of leaves) states.push(applyStep(states[states.length - 1], step));
  return states;
}
