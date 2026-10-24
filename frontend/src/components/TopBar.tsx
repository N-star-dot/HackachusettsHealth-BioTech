// The sticky header: brand, mock/live toggle, run id, and the safety chip.

import type { DataMode } from "../api";
import type { SafetyGate } from "../types";

interface Props {
  mode: DataMode;
  onMode: (m: DataMode) => void;
  runId: string;
  seed: number;
  safety: SafetyGate;
}

export function TopBar({ mode, onMode, runId, seed, safety }: Props) {
  return (
    <header className="topbar">
      <div className="topbar__inner">
        <div className="brand">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
            <rect x="3" y="6" width="22" height="16" rx="3" />
            <circle cx="9" cy="12" r="1.6" />
            <circle cx="14" cy="12" r="1.6" />
            <circle cx="19" cy="12" r="1.6" />
            <circle cx="9" cy="17" r="1.6" />
            <circle cx="14" cy="17" r="1.6" />
            <circle cx="19" cy="17" r="1.6" />
          </svg>
          <div>
            <span className="brand__name">Hackachusetts</span>
            <span className="brand__sub">Assay planner</span>
          </div>
        </div>
        <div className="topbar__meta">
          <div className="segmented" role="group" aria-label="Data source">
            <button type="button" aria-pressed={mode === "mock"} onClick={() => onMode("mock")}>
              Mocks
            </button>
            <button type="button" aria-pressed={mode === "api"} onClick={() => onMode("api")}>
              Live API
            </button>
          </div>
          <span className="mono muted small">
            run {runId} · seed {seed}
          </span>
          <span className={`chip ${safety.pass ? "chip--ok" : "chip--bad"}`}>
            {safety.pass ? "Safety check passed" : "Blocked by safety check"}
          </span>
        </div>
      </div>
    </header>
  );
}
