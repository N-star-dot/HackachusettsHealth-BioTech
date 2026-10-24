import { useCallback, useEffect, useRef, useState } from "react";
import { leafSteps } from "../lib/replay";
import type { ProtocolStep } from "../api/types";

export type ReplayStatus = "idle" | "playing" | "paused" | "done";

/** Drives the replay index over the leaf steps at 1x/4x/16x (BRIEF 5.10). Reduced-motion
 *  callers can step manually. */
export function useReplay(steps: ProtocolStep[]) {
  const leaves = leafSteps(steps);
  const [index, setIndex] = useState(0);
  const [status, setStatus] = useState<ReplayStatus>("idle");
  const [speed, setSpeed] = useState(1);
  const raf = useRef<number | null>(null);
  const last = useRef(0);

  const total = leaves.length;

  const tick = useCallback((ts: number) => {
    // 1x: ~400ms/step; scaled by speed. At 16x a ~400-step protocol finishes in ~10s.
    const perStep = 400 / speed;
    if (ts - last.current >= perStep) {
      last.current = ts;
      setIndex((i) => {
        if (i + 1 >= total) { setStatus("done"); return total; }
        return i + 1;
      });
    }
    raf.current = requestAnimationFrame(tick);
  }, [speed, total]);

  useEffect(() => {
    if (status === "playing") {
      raf.current = requestAnimationFrame(tick);
      return () => { if (raf.current) cancelAnimationFrame(raf.current); };
    }
  }, [status, tick]);

  const play = () => { if (index >= total) setIndex(0); setStatus("playing"); };
  const pause = () => setStatus("paused");
  const skipToEnd = () => { setIndex(total); setStatus("done"); };
  const stepBy = (d: number) => setIndex((i) => Math.max(0, Math.min(total, i + d)));

  return { index, total, status, speed, setSpeed, play, pause, skipToEnd, stepBy, leaves };
}
