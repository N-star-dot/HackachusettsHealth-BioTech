import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { Deck } from "../components/Bench/Deck";
import type { SimResult } from "../api/types";

const sim = (deck?: SimResult["deck"]): SimResult => ({
  design_id: "d-001", protocol_file: "protocols/d-001.py",
  simulator: { pass: true, error: null, log_lines: 10, seconds: 0.1, opentrons_version: "10.1.0" },
  cost: { tips: 11, compound_uL: 50, plates: 1, robot_steps: 100 },
  steps: [],
  deck,
});

describe("Deck (BRIEF 5.10)", () => {
  it("renders with the fixed layout when sim.deck is absent", () => {
    const { getByText, getAllByText } = render(<Deck sim={sim()} />);
    expect(getByText(/Fixed compiler layout/)).toBeTruthy();
    expect(getAllByText(/tip rack/i).length).toBeGreaterThan(0);
  });

  it("renders from sim.deck when present", () => {
    const { getByText } = render(<Deck sim={sim([
      { slot: "D2", load_name: "corning_96_wellplate_360ul_flat", display_name: "Plate", role: "plate" },
    ])} />);
    expect(getByText(/Layout from the simulator/)).toBeTruthy();
  });
});
