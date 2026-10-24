import { describe, expect, it } from "vitest";
import {
  axisIsAssumed,
  costIsCounted,
  gateOk,
  isOfflineTopic,
  isReplayable,
  realNeighbors,
  simOk,
  verifiedCount,
} from "../api/normalize";
import { hash6 } from "../lib/hash";
import type { ExperimentDesign, SimResult, TopicReport } from "../api/types";

describe("gateOk", () => {
  it("reads pass (POST) and passed (GET)", () => {
    expect(gateOk({ pass: true })).toBe(true);
    expect(gateOk({ passed: true })).toBe(true);
    expect(gateOk({ pass: false })).toBe(false);
    expect(gateOk(undefined)).toBe(false);
  });
});

describe("topic quirks", () => {
  const base: TopicReport = {
    query: "x",
    topic: { openalex_id: "T10966", name: "Liver" },
    counts_by_year: [],
    momentum: { p_growth: 0.5, model: "hgb-v3" },
    neighbors: [
      { openalex_id: "T00001", name: "placeholder neighbor", works_last_5y: 1 },
      { openalex_id: "T222", name: "Real topic", works_last_5y: 10 },
    ],
    matrix: {
      momentum: 0.7, novelty: 0.5, evidence: 0.4, automatable: 1, cost_time: 0.6,
      weights: { momentum: 0.2, novelty: 0.2, evidence: 0.2, automatable: 0.2, cost_time: 0.2 },
      total: 0.64,
      axis_sources: { novelty: { type: "assumed", id: "fixed-prior" } },
    },
    safety: { pass: true, reasons: [] },
  };

  it("detects offline topics", () => {
    expect(isOfflineTopic(base)).toBe(false);
    expect(isOfflineTopic({ ...base, topic: { openalex_id: "T00000", name: "x" } })).toBe(true);
    expect(isOfflineTopic({ ...base, offline: true })).toBe(true);
  });

  it("drops placeholder neighbors", () => {
    const real = realNeighbors(base);
    expect(real).toHaveLength(1);
    expect(real[0].openalex_id).toBe("T222");
  });

  it("flags assumed axes", () => {
    expect(axisIsAssumed(base, "novelty")).toBe(true);
    expect(axisIsAssumed(base, "momentum")).toBe(false);
  });
});

describe("sim quirks", () => {
  const sim: SimResult = {
    design_id: "d-001",
    protocol_file: "protocols/d-001.py",
    simulator: { pass: true, error: null, log_lines: 10, seconds: 0.1, opentrons_version: "10.1.0" },
    cost: { tips: 11, compound_uL: 50, plates: 1, robot_steps: 100, source: { type: "simulator", id: "x" } },
    steps: [{ i: 0, action: "pick_up_tip", text: "Picking up tip" }],
  };

  it("reads simulator pass + counted cost + replayable", () => {
    expect(simOk(sim)).toBe(true);
    expect(costIsCounted(sim)).toBe(true);
    expect(isReplayable(sim)).toBe(true);
  });

  it("non-replayable when steps have no text", () => {
    expect(isReplayable({ ...sim, steps: [{ i: 0, action: "other" }] })).toBe(false);
    expect(isReplayable({ ...sim, steps: [] })).toBe(false);
  });
});

describe("verifiedCount", () => {
  it("counts verified rationale", () => {
    const d = { rationale: [
      { status: "verified" }, { status: "unverified" }, { status: "verified" },
    ] } as unknown as ExperimentDesign;
    expect(verifiedCount(d)).toEqual({ verified: 2, total: 3 });
  });
});

describe("hash6", () => {
  it("is stable regardless of key order", () => {
    expect(hash6({ a: 1, b: 2 })).toBe(hash6({ b: 2, a: 1 }));
  });
  it("is 6 hex chars", () => {
    expect(hash6({ x: 1 })).toMatch(/^[0-9a-f]{6}$/);
  });
});
