import { COLS, ROWS, useReplay, type Replay } from "../hooks/useReplay";
import type { ExperimentDesign, SimResult } from "../types";

export function RunReplay({ sim, design }: { sim: SimResult; design: ExperimentDesign | null }) {
  const replay = useReplay(sim, design);

  return (
    <div className="card card--wide">
      <div className="card__head">
        <div>
          <p className="eyebrow">03 · Protocol</p>
          <h2>Robot run replay</h2>
        </div>
        <div className="chips">
          {replay.isDemo && <span className="chip chip--sim">Demo steps from design</span>}
          <span className={`chip ${sim.simulator.pass ? "chip--ok" : "chip--bad"}`}>
            Simulator {sim.simulator.pass ? "pass" : "fail"} · Opentrons {sim.simulator.opentrons_version}
          </span>
        </div>
      </div>
      {sim.simulator.error && <p className="notice notice--error mono small">{sim.simulator.error}</p>}

      <div className="replay">
        <PlateView filled={replay.filled} active={replay.activeWell} />
        <ReplayControls replay={replay} />
      </div>
    </div>
  );
}

function PlateView({ filled, active }: { filled: Set<string>; active: string | null }) {
  return (
    <div className="plate-wrap">
      <div className="plate" role="img" aria-label={`96-well plate, ${filled.size} wells filled`}>
        <span />
        {COLS.map((c) => (
          <span key={c} className="plate__label">
            {c}
          </span>
        ))}
        {ROWS.map((r) => (
          <PlateRow key={r} row={r} filled={filled} active={active} />
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

function ReplayControls({ replay }: { replay: Replay }) {
  const { steps, step, last, playing, speed, current, windowStart, log } = replay;

  return (
    <div className="replay__controls">
      <div className="transport">
        <button
          type="button"
          className="icon-btn"
          aria-label={playing ? "Pause replay" : "Play replay"}
          onClick={replay.togglePlay}
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
            onChange={(e) => replay.seek(Number(e.target.value))}
          />
        </div>
        <label className="small muted speed">
          Speed
          <select value={speed} onChange={(e) => replay.setSpeed(Number(e.target.value))}>
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
  );
}
