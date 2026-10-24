import { useEffect, useMemo, useState } from "react";
import type { ExperimentDesign, ProtocolStep, SimResult } from "../types";

const ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"];
const COLS = Array.from({ length: 12 }, (_, i) => i + 1);

/**
 * Stand-in steps built from the design, used only when the SimResult carries fewer
 * than two steps (the mock has one). Shown with a "demo steps" label so nobody
 * mistakes it for the simulator's output.
 */
function demoSteps(design: ExperimentDesign): ProtocolStep[] {
  const steps: ProtocolStep[] = [];
  const reps = Math.min(design.replicates, ROWS.length);
  const points = Math.min(design.dilution.points, COLS.length);
  const uL = design.volumes_uL.transfer;
  const push = (s: Omit<ProtocolStep, "i">) => steps.push({ i: steps.length, ...s });
  for (let r = 0; r < reps; r++) {
    for (let p = 0; p < points; p++) {
      push({ action: "pick_up_tip", labware: "tiprack" });
      push({ action: "aspirate", uL, labware: "reservoir", well: "A1" });
      push({ action: "dispense", uL, labware: "plate", well: `${ROWS[r]}${p + 1}` });
      push({ action: "drop_tip", labware: "trash" });
    }
  }
  return steps;
}

const isPlate = (s: ProtocolStep) => !!s.well && !!s.labware && s.labware.toLowerCase().includes("plate");

export function RunReplay({ sim, design }: { sim: SimResult; design: ExperimentDesign | null }) {
  const isDemo = sim.steps.length < 2 && !!design;
  const steps = useMemo(() => (isDemo && design ? demoSteps(design) : sim.steps), [isDemo, design, sim.steps]);
  const last = Math.max(0, steps.length - 1);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(4);

  useEffect(() => {
    setStep(0);
    setPlaying(false);
  }, [steps]);

  useEffect(() => {
    if (!playing) return;
    if (step >= last) {
      setPlaying(false);
      return;
    }
    const t = window.setTimeout(() => setStep((s) => Math.min(s + 1, last)), 400 / speed);
    return () => window.clearTimeout(t);
  }, [playing, step, last, speed]);

  const current = steps[step];
  const filled = useMemo(() => {
    const set = new Set<string>();
    for (let i = 0; i <= step && i < steps.length; i++) {
      const s = steps[i];
      if (isPlate(s) && s.action.startsWith("dispense")) set.add(s.well!.toUpperCase());
    }
    return set;
  }, [steps, step]);
  const activeWell = current && isPlate(current) ? current.well!.toUpperCase() : null;
  const windowStart = Math.max(0, step - 4);
  const log = steps.slice(windowStart, step + 1);

  return (
    <div className="card card--wide">
      <div className="card__head">
        <div>
          <p className="eyebrow">03 · Protocol</p>
          <h2>Robot run replay</h2>
        </div>
        <div className="chips">
          {isDemo && <span className="chip chip--sim">Demo steps from design</span>}
          <span className={`chip ${sim.simulator.pass ? "chip--ok" : "chip--bad"}`}>
            Simulator {sim.simulator.pass ? "pass" : "fail"} · Opentrons {sim.simulator.opentrons_version}
          </span>
        </div>
      </div>
      {sim.simulator.error && <p className="notice notice--error mono small">{sim.simulator.error}</p>}

      <div className="replay">
        <div className="plate-wrap">
          <div className="plate" role="img" aria-label={`96-well plate, ${filled.size} wells filled`}>
            <span />
            {COLS.map((c) => (
              <span key={c} className="plate__label">
                {c}
              </span>
            ))}
            {ROWS.map((r) => (
              <PlateRow key={r} row={r} filled={filled} active={activeWell} />
            ))}
          </div>
          <div className="legend small muted">
            <span>
              <i className="well-dot well-dot--filled" /> Filled
            </span>
            <span>
              <i className="well-dot well-dot--active" /> Current
            </span>
            <span>
              <i className="well-dot" /> Empty
            </span>
          </div>
        </div>

        <div className="replay__controls">
          <div className="transport">
            <button
              type="button"
              className="icon-btn"
              aria-label={playing ? "Pause replay" : "Play replay"}
              onClick={() => {
                if (step >= last) setStep(0);
                setPlaying((p) => !p);
              }}
              disabled={steps.length === 0}
            >
              {playing ? (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <rect x="3" y="2.5" width="3.5" height="11" rx="1" />
                  <rect x="9.5" y="2.5" width="3.5" height="11" rx="1" />
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path d="M4 2.5v11l9-5.5z" />
                </svg>
              )}
            </button>
            <div className="transport__scrub">
              <label htmlFor="replay-step" className="small strong">
                Step <span className="mono">{steps.length ? step + 1 : 0}</span> of{" "}
                <span className="mono">{steps.length}</span>
              </label>
              <input
                id="replay-step"
                type="range"
                min={0}
                max={last}
                value={step}
                onChange={(e) => {
                  setPlaying(false);
                  setStep(Number(e.target.value));
                }}
              />
            </div>
            <label className="small muted speed">
              Speed
              <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
                <option value={1}>1×</option>
                <option value={4}>4×</option>
                <option value={16}>16×</option>
              </select>
            </label>
          </div>

          <ol className="steplog mono small" start={windowStart}>
            {log.map((s) => (
              <li key={s.i} className={s.i === current?.i ? "is-current" : undefined}>
                <span className="muted">#{s.i}</span>
                <span>{s.action}</span>
                <span>{s.uL != null ? `${s.uL} µL` : ""}</span>
                <span className="muted">{[s.labware, s.well].filter(Boolean).join(" ")}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}

function PlateRow({ row, filled, active }: { row: string; filled: Set<string>; active: string | null }) {
  return (
    <>
      <span className="plate__label">{row}</span>
      {COLS.map((c) => {
        const name = `${row}${c}`;
        const cls = name === active ? "well well--active" : filled.has(name) ? "well well--filled" : "well";
        return <span key={name} className={cls} title={name} />;
      })}
    </>
  );
}
