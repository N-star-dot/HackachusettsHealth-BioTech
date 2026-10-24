import { labwareName } from "../../lib/labware";
import { Replay } from "./Replay";
import type { DeckSlot, ExperimentDesign, SimResult } from "../../api/types";
import styles from "./Deck.module.css";

interface Props {
  sim?: SimResult | null;
  design?: ExperimentDesign | null;
}

// Fixed compiler layout, used when sim.deck is absent (BRIEF 5.10).
const FIXED: DeckSlot[] = [
  { slot: "A3", load_name: "trash_bin", display_name: "Trash bin", role: "trash" },
  { slot: "D1", load_name: "opentrons_flex_96_tiprack_200ul", display_name: "Flex 96 tip rack, 200 µL", role: "tips" },
  { slot: "D2", load_name: "corning_96_wellplate_360ul_flat", display_name: "Corning 96-well plate, 360 µL, flat", role: "plate" },
  { slot: "D3", load_name: "nest_12_reservoir_15ml", display_name: "NEST 12-well reservoir, 15 mL", role: "reservoir", contents: { A1: "diluent", A2: "compound" } },
];

const DECK_SLOTS = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "D1", "D2", "D3"];

/** The Flex deck schematic (BRIEF 5.10). A-row at the top (back of the robot), D at the
 *  bottom; 3 columns. No logos — everything is drawn. Renders with or without sim.deck. */
export function Deck({ sim, design }: Props) {
  const loaded = new Map((sim?.deck?.length ? sim.deck : FIXED).map((s) => [s.slot, s]));

  return (
    <div className={styles.bench}>
      <div className={styles.deck} aria-label="Opentrons Flex deck">
        {DECK_SLOTS.map((slot) => {
          const item = loaded.get(slot);
          return (
            <div key={slot} className={`${styles.slot} ${item ? styles[item.role] ?? "" : ""}`}>
              <span className={styles.slotLabel}>{slot}</span>
              {item && <span className={styles.load}>{roleShort(item)}</span>}
            </div>
          );
        })}
      </div>
      <p className={styles.caption}>
        Flex deck schematic. {sim?.deck?.length ? "Layout from the simulator." : "Fixed compiler layout."}
      </p>
      <ul className={styles.legend}>
        {[...loaded.values()].map((s) => (
          <li key={s.slot}>{s.slot}: {labwareName(s.load_name) || s.display_name}</li>
        ))}
      </ul>
      {sim && design && <Replay sim={sim} design={design} />}
    </div>
  );
}

function roleShort(s: DeckSlot): string {
  switch (s.role) {
    case "tips": return "tips";
    case "plate": return "plate";
    case "reservoir": return "reservoir";
    case "trash": return "trash";
    default: return "";
  }
}
