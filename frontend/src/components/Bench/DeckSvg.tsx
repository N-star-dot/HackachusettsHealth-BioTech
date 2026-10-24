import { useMemo } from "react";
import { motion } from "motion/react";
import type { ReplayState } from "../../lib/replay";
import type { DeckSlot, ProtocolStep } from "../../api/types";
import { activityColor } from "../../lib/hill";
import { ROWS } from "../../lib/plate";
import styles from "./DeckSvg.module.css";

// --- Flex deck geometry (BRIEF 5.10), in millimetres ---------------------------
const SLOT_W = 127.76;
const SLOT_H = 85.48;
const WELL_X0 = 14.38;   // A1 center from slot left
const WELL_Y0 = 11.24;   // A1 center from slot top
const PITCH = 9.0;
const GAP = 6;           // gap between slots on the deck

// Deck is 3 columns x 4 rows; A at the back (top), D at the front (bottom).
const COL = { "1": 0, "2": 1, "3": 2 } as const;
const ROW = { A: 0, B: 1, C: 2, D: 3 } as const;

function slotOrigin(slot: string): { x: number; y: number } {
  const c = COL[slot[1] as keyof typeof COL] ?? 0;
  const r = ROW[slot[0] as keyof typeof ROW] ?? 0;
  return { x: c * (SLOT_W + GAP), y: r * (SLOT_H + GAP) };
}

const DECK_W = 3 * SLOT_W + 2 * GAP;
const DECK_H = 4 * SLOT_H + 3 * GAP;

/** Center of a plate/tiprack well (A1..H12) within its slot, in deck mm. */
function wellCenter(slot: string, well: string): { x: number; y: number } {
  const o = slotOrigin(slot);
  const row = ROWS.indexOf(well[0]);
  const col = parseInt(well.slice(1), 10) - 1;
  return {
    x: o.x + WELL_X0 + (col < 0 ? 0 : col) * PITCH,
    y: o.y + WELL_Y0 + (row < 0 ? 0 : row) * PITCH,
  };
}

const FIXED: DeckSlot[] = [
  { slot: "A3", load_name: "trash_bin", display_name: "Trash bin", role: "trash" },
  { slot: "D1", load_name: "opentrons_flex_96_tiprack_200ul", display_name: "Tip rack", role: "tips" },
  { slot: "D2", load_name: "corning_96_wellplate_360ul_flat", display_name: "Plate", role: "plate" },
  { slot: "D3", load_name: "nest_12_reservoir_15ml", display_name: "Reservoir", role: "reservoir" },
];

interface Props {
  deck?: DeckSlot[] | null;
  state: ReplayState;       // replay state at the current step
  step: ProtocolStep | null; // the current leaf step (for the pipette head + action)
  ic50NM: number;
  reduced: boolean;
}

/** The animated Flex deck (V1): real geometry, liquids colored by computed activity, and a
 *  pipette head that springs to each well. Driven by the pure replay state machine, so the
 *  colors and counters always match the simulator run. */
export function DeckSvg({ deck, state, step, ic50NM, reduced }: Props) {
  const slots = useMemo(() => (deck?.length ? deck : FIXED), [deck]);
  const bySlot = useMemo(() => new Map(slots.map((s) => [s.slot, s])), [slots]);

  // where is the tip right now? dest for dispense, source for aspirate, else well/slot.
  const target = step
    ? (step.dest ?? step.source ?? (step.well && step.slot ? { slot: step.slot, well: step.well } : null))
    : null;
  const head = target?.slot && target?.well ? wellCenter(target.slot, target.well) : null;
  const holding = state.tip != null && state.tip.volume_uL > 0;

  return (
    <svg viewBox={`-4 -4 ${DECK_W + 8} ${DECK_H + 8}`} className={styles.svg}
         role="img" aria-label="Opentrons Flex deck replay">
      {/* deck base */}
      <rect x={-4} y={-4} width={DECK_W + 8} height={DECK_H + 8} rx={14}
            fill="var(--deck)" />
      {["A1","A2","A3","B1","B2","B3","C1","C2","C3","D1","D2","D3"].map((slot) => {
        const o = slotOrigin(slot);
        const item = bySlot.get(slot);
        return (
          <g key={slot}>
            <rect x={o.x} y={o.y} width={SLOT_W} height={SLOT_H} rx={6}
                  fill={item ? "var(--slot)" : "none"} stroke="var(--rule)" strokeWidth={0.8} />
            <text x={o.x + 3} y={o.y + 7} className={styles.slotLabel}>{slot}</text>
            {item?.role === "tips" && <TipRack slot={slot} usedTips={state.tipsUsed} />}
            {item?.role === "plate" && <Plate slot={slot} wells={state.wells} ic50NM={ic50NM} />}
            {item?.role === "reservoir" && <Reservoir slot={slot} />}
            {item?.role === "trash" && <Trash slot={slot} />}
          </g>
        );
      })}

      {/* pipette head on a gantry line */}
      {head && (
        <>
          <line x1={head.x} y1={-4} x2={head.x} y2={head.y} stroke="var(--ink)" strokeWidth={0.6} opacity={0.4} />
          <motion.g
            animate={{ x: head.x, y: head.y }}
            transition={reduced ? { duration: 0 } : { type: "spring", stiffness: 380, damping: 36 }}
          >
            <circle r={3.2} fill="var(--ink)" />
            <rect x={-1.1} y={0} width={2.2} height={7} rx={1}
                  fill={holding ? activityColor(tipActivity(state)) : "var(--sheet)"}
                  stroke="var(--ink)" strokeWidth={0.4} />
          </motion.g>
        </>
      )}
    </svg>
  );
}

/** Target activity of what the tip holds, for coloring (blue stock to pink diluent). */
function tipActivity(state: ReplayState): number {
  const c = state.tip?.conc_nM ?? 0;
  // high concentration => target inhibited => blue (low activity); near 0 => pink.
  return c <= 0 ? 100 : Math.max(0, Math.min(100, 100 / (1 + c / 1)));
}

function TipRack({ slot, usedTips }: { slot: string; usedTips: number }) {
  const tips = [];
  let n = 0;
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 12; c++) {
      const { x, y } = wellCenter(slot, `${ROWS[r]}${c + 1}`);
      const used = n < usedTips;
      tips.push(
        <circle key={`${r}-${c}`} cx={x} cy={y} r={3}
                fill={used ? "none" : "var(--sheet)"}
                stroke={used ? "var(--rule)" : "var(--ink)"} strokeWidth={0.5}
                opacity={used ? 0.4 : 1} />,
      );
      n++;
    }
  }
  return <>{tips}</>;
}

function Plate({ slot, wells, ic50NM }: { slot: string; wells: ReplayState["wells"]; ic50NM: number }) {
  const cells = [];
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 12; c++) {
      const id = `${ROWS[r]}${c + 1}`;
      const { x, y } = wellCenter(slot, id);
      const w = wells[id];
      const filled = w && w.volume_uL > 0.5;
      const color = filled ? activityColor(100 / (1 + (w!.conc_nM) / ic50NM)) : "var(--sheet)";
      cells.push(
        <circle key={id} cx={x} cy={y} r={3.4}
                fill={filled ? color : "none"}
                stroke="var(--rule)" strokeWidth={0.5} opacity={filled ? 1 : 0.6} />,
      );
    }
  }
  return <>{cells}</>;
}

function Reservoir({ slot }: { slot: string }) {
  const o = slotOrigin(slot);
  const troughs = [];
  for (let i = 0; i < 12; i++) {
    const x = o.x + 6 + i * ((SLOT_W - 12) / 12);
    // A1 diluent (pink), A2 compound stock (blue), rest empty
    const fill = i === 0 ? activityColor(100) : i === 1 ? activityColor(0) : "var(--sheet)";
    troughs.push(
      <rect key={i} x={x} y={o.y + 12} width={(SLOT_W - 12) / 12 - 1.5} height={SLOT_H - 24}
            rx={1.5} fill={fill} stroke="var(--rule)" strokeWidth={0.4} />,
    );
  }
  return <>{troughs}</>;
}

function Trash({ slot }: { slot: string }) {
  const o = slotOrigin(slot);
  return (
    <rect x={o.x + 8} y={o.y + 10} width={SLOT_W - 16} height={SLOT_H - 20} rx={4}
          fill="none" stroke="var(--graphite)" strokeDasharray="3 3" strokeWidth={0.8} />
  );
}
