import { describe, expect, it } from "vitest";
import fc from "fast-check";
import { plannedLayout } from "../lib/plate";
import { activity } from "../lib/hill";
import { concentrations } from "../lib/dilution";

describe("plannedLayout (BRIEF B.7)", () => {
  it("places wells uniquely inside 8x12 and counts correctly", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 4, max: 11 }),
        fc.integer({ min: 1, max: 8 }),
        fc.integer({ min: 0, max: 4 }),
        fc.integer({ min: 0, max: 4 }),
        (points, replicates, pos, neg) => {
          // valid regime only (brief limits)
          fc.pre(points * replicates + pos + neg <= 96 && pos + neg <= 8);
          const layout = plannedLayout({
            dilution: { top_nM: 2400, factor: 3, points },
            replicates,
            controls: { positive_wells: pos, negative_wells: neg },
          });
          const used = layout.wells.filter((w) => w.kind !== "empty");
          // unique positions
          const ids = new Set(used.map((w) => w.id));
          expect(ids.size).toBe(used.length);
          // all inside the grid
          used.forEach((w) => {
            expect(w.row).toBeGreaterThanOrEqual(0);
            expect(w.row).toBeLessThan(8);
            expect(w.col).toBeGreaterThanOrEqual(0);
            expect(w.col).toBeLessThan(12);
          });
          expect(layout.wellsUsed).toBe(points * replicates + pos + neg);
        },
      ),
      { numRuns: 200 },
    );
  });
});

describe("hill activity (BRIEF B.5)", () => {
  it("is 50 at ic50, monotonic in concentration, within (0,100)", () => {
    expect(activity(120, 120)).toBeCloseTo(50, 6);
    // concentrations() runs high -> low, so activity runs low -> high (less inhibition)
    const cs = concentrations(12000, 3, 10);
    let prev = -Infinity;
    for (const c of cs) {
      const a = activity(c, 120);
      expect(a).toBeGreaterThan(0);
      expect(a).toBeLessThan(100);
      expect(a).toBeGreaterThan(prev);
      prev = a;
    }
  });
});
