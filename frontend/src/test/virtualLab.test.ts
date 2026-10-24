import { describe, expect, it } from "vitest";
import { bandOf, histogram } from "../components/Uncertainty/VirtualLab";

describe("virtual lab helpers (V2)", () => {
  it("classifies fold error into the right band", () => {
    expect(bandOf(1.2)).toBe("ok");       // within 1.5x
    expect(bandOf(1.5)).toBe("ok");       // boundary is still ok
    expect(bandOf(1.8)).toBe("partial");  // 1.5x to 2x
    expect(bandOf(2)).toBe("partial");    // boundary
    expect(bandOf(3.4)).toBe("flag");     // beyond 2x
  });

  it("bins every value into exactly one bucket and conserves the count", () => {
    const max = 8;
    const bins = 10;
    const edges = Array.from({ length: bins + 1 }, (_, i) => Math.pow(max, i / bins));
    const values = [1, 1.2, 1.5, 2, 3, 5, 7.9, 8]; // includes both ends
    const counts = histogram(values, edges);
    expect(counts.reduce((a, b) => a + b, 0)).toBe(values.length);
    // the max value lands in the last bin (inclusive upper edge)
    expect(counts[counts.length - 1]).toBeGreaterThanOrEqual(1);
  });

  it("clamps sub-1x fold errors into the first bin", () => {
    const edges = [1, 2, 4, 8];
    const counts = histogram([0.5, 0.9, 1], edges);
    expect(counts[0]).toBe(3);
  });
});
