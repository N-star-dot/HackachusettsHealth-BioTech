import { useReducedMotion } from "motion/react";
import { labwareName } from "../../lib/labware";
import { Replay } from "./Replay";
import { DeckSvg } from "./DeckSvg";
import { initialState } from "../../lib/replay";
import { isReplayable } from "../../api/normalize";
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

/** The Flex deck (BRIEF 5.10, V1). When the run is replayable, the animated deck + replay
 *  render together; otherwise the deck layout is drawn in its starting state. No logos. */
export function Deck({ sim, design }: Props) {
  const reduced = useReducedMotion() ?? false;
  const deck = sim?.deck?.length ? sim.deck : FIXED;
  const loaded = new Map(deck.map((s) => [s.slot, s]));
  const replayable = sim && design && isReplayable(sim);

  return (
    <div className={styles.bench}>
      {replayable ? (
        <Replay key={sim!.design_id} sim={sim!} design={design!} />
      ) : (
        <DeckSvg
          deck={deck}
          state={initialState(design?.dilution.top_nM ?? 1)}
          step={null}
          ic50NM={design?.prior_ic50.median_nM ?? 1}
          reduced={reduced}
        />
      )}
      <p className={styles.caption}>
        Flex deck, {12 - loaded.size} of 12 slots free.{" "}
        {sim?.deck?.length ? "Layout from the simulator." : "Fixed compiler layout."}
      </p>
      <ul className={styles.legend}>
        {[...loaded.values()].map((s) => (
          <li key={s.slot}>{s.slot}: {labwareName(s.load_name) || s.display_name}</li>
        ))}
      </ul>
    </div>
  );
}
