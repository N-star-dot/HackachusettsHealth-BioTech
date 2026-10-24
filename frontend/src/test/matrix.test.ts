import { describe, expect, it } from "vitest";
import fc from "fast-check";
import { AXES, contribution, weightedTotal } from "../lib/matrix";
import type { AxisKey } from "../api/types";

const axrec = () =>
  fc.record(Object.fromEntries(AXES.map((a) => [a, fc.double({ min: 0, max: 1, noNaN: true })])) as never) as fc.Arbitrary<Record<AxisKey, number>>;
const wrec = () =>
  fc.record(Object.fromEntries(AXES.map((a) => [a, fc.double({ min: 0, max: 1, noNaN: true })])) as never) as fc.Arbitrary<Record<AxisKey, number>>;

describe("weightedTotal (BRIEF B.1)", () => {
  it("matches the backend default-weights total within 1e-6", () => {
    const axes = { momentum: 0.71, novelty: 0.55, evidence: 0.4, automatable: 1, cost_time: 0.62 };
    const weights = { momentum: 0.2, novelty: 0.2, evidence: 0.2, automatable: 0.2, cost_time: 0.2 };
    expect(Math.abs(weightedTotal(axes, weights) - 0.656)).toBeLessThan(1e-6);
  });

  it("stays in [0,1], scale-invariant, contributions sum to total", () => {
    fc.assert(
      fc.property(axrec(), wrec(), (axes, weights) => {
        const total = weightedTotal(axes, weights);
        expect(total).toBeGreaterThanOrEqual(0);
        expect(total).toBeLessThanOrEqual(1 + 1e-9);
        // scale invariance (when weights sum > 0)
        const den = AXES.reduce((s, k) => s + weights[k], 0);
        if (den > 1e-9) {
          const scaled = Object.fromEntries(AXES.map((k) => [k, weights[k] * 3])) as Record<AxisKey, number>;
          expect(Math.abs(weightedTotal(axes, scaled) - total)).toBeLessThan(1e-9);
          const sum = AXES.reduce((s, k) => s + contribution(k, axes, weights), 0);
          expect(Math.abs(sum - total)).toBeLessThan(1e-9);
        }
      }),
      { numRuns: 200 },
    );
  });
});
