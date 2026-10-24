import { useEffect, useMemo, useRef, useState } from "react";
import { mockRun, rerunUncertainty, runPipeline, type DataMode } from "./api";
import { RunReplay } from "./components/RunReplay";
import { Evidence, RunCost } from "./components/SidePanels";
import { TopicPanel } from "./components/TopicPanel";
import { ViabilityMatrix, type AxisProvenance } from "./components/ViabilityMatrix";
import { WhatIf } from "./components/WhatIf";
import type { ExperimentDesign, RunResponse, UncertaintyReport, Weights } from "./types";

const SEED = 42;
const MODE_KEY = "dashboard.mode";

function loadMode(): DataMode {
  try {
    return localStorage.getItem(MODE_KEY) === "api" ? "api" : "mock";
  } catch {
    return "mock";
  }
}

export default function App() {
  const [mode, setMode] = useState<DataMode>(loadMode);
  const [query, setQuery] = useState("kinase inhibitors for liver fibrosis");
  const [runs, setRuns] = useState(1000);
  const [run, setRun] = useState<RunResponse>(() => mockRun());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [weights, setWeights] = useState<Weights>(run.topic.matrix.weights);
  const [design, setDesign] = useState<ExperimentDesign | null>(run.design);
  const [uncertainty, setUncertainty] = useState<UncertaintyReport | null>(run.uncertainty);
  const [whatIfPending, setWhatIfPending] = useState(false);
  const [whatIfError, setWhatIfError] = useState<string | null>(null);
  const whatIfAbort = useRef<AbortController | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(MODE_KEY, mode);
    } catch {
      /* storage unavailable; mode just won't persist */
    }
  }, [mode]);

  function adopt(next: RunResponse) {
    setRun(next);
    setWeights(next.topic.matrix.weights);
    setDesign(next.design);
    setUncertainty(next.uncertainty);
    setWhatIfError(null);
  }

  async function onRun(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "mock") {
      adopt(mockRun(query));
      return;
    }
    setLoading(true);
    try {
      adopt(await runPipeline({ query, runs, seed: SEED, weights }));
    } catch (err) {
      setError(`${(err as Error).message}. Is the backend running? (uvicorn backend.api:app --reload)`);
    } finally {
      setLoading(false);
    }
  }

  // What-if: in live mode, rerun stage 4 shortly after the sliders stop moving.
  useEffect(() => {
    if (mode !== "api" || !design || !run.design || design === run.design) return;
    const t = window.setTimeout(async () => {
      whatIfAbort.current?.abort();
      const ctrl = new AbortController();
      whatIfAbort.current = ctrl;
      setWhatIfPending(true);
      setWhatIfError(null);
      try {
        setUncertainty(await rerunUncertainty(design, runs, SEED, ctrl.signal));
      } catch (err) {
        if ((err as Error).name !== "AbortError") setWhatIfError((err as Error).message);
      } finally {
        if (whatIfAbort.current === ctrl) setWhatIfPending(false);
      }
    }, 350);
    return () => window.clearTimeout(t);
  }, [mode, design, run.design, runs]);

  // Back to the run's own report when the design is reset.
  useEffect(() => {
    if (design === run.design) setUncertainty(run.uncertainty);
  }, [design, run]);

  const axisSources = useMemo<AxisProvenance>(() => {
    const topicSrc = { type: "openalex" as const, id: run.topic.topic.openalex_id };
    const simSrc = run.sim
      ? [{ type: "simulator" as const, id: `${run.sim.design_id} · opentrons ${run.sim.simulator.opentrons_version}` }]
      : [];
    return {
      momentum: { source: [topicSrc], note: `Momentum model ${run.topic.momentum.model}` },
      novelty: { source: [topicSrc], note: "Stage 1 score from the topic and its neighbors" },
      evidence: { source: run.design ? [topicSrc, run.design.prior_ic50.source] : [topicSrc], note: "Stage 1 score" },
      automatable: { source: simSrc.length ? simSrc : [topicSrc], note: "Stage 1 score" },
      cost_time: { source: simSrc.length ? simSrc : [topicSrc], note: "Stage 1 score" },
    };
  }, [run]);

  const safety = run.topic.safety;

  return (
    <div className="app">
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
              <button type="button" aria-pressed={mode === "mock"} onClick={() => setMode("mock")}>
                Mocks
              </button>
              <button type="button" aria-pressed={mode === "api"} onClick={() => setMode("api")}>
                Live API
              </button>
            </div>
            <span className="mono muted small">
              run {run.run_id} · seed {SEED}
            </span>
            <span className={`chip ${safety.pass ? "chip--ok" : "chip--bad"}`}>
              {safety.pass ? "Safety check passed" : "Blocked by safety check"}
            </span>
          </div>
        </div>
      </header>

      <main className="page">
        <form className="card query" onSubmit={onRun}>
          <div className="field field--grow">
            <label htmlFor="query">Research question</label>
            <input id="query" value={query} onChange={(e) => setQuery(e.target.value)} required />
          </div>
          <div className="field field--narrow">
            <label htmlFor="runs">Sim runs</label>
            <input
              id="runs"
              type="number"
              min={1}
              max={5000}
              value={runs}
              onChange={(e) => setRuns(Math.max(1, Math.min(5000, Number(e.target.value) || 1)))}
              className="mono"
            />
          </div>
          <button type="submit" className="btn btn--primary" disabled={loading}>
            {loading ? "Running…" : mode === "mock" ? "Load mocks" : "Run pipeline"}
          </button>
        </form>

        {error && <p className="notice notice--error">{error}</p>}
        {run.blocked && (
          <p className="notice notice--error">
            This topic was blocked by the safety gate{safety.reasons.length ? `: ${safety.reasons.join("; ")}` : ""}. No
            design was produced.
          </p>
        )}

        <section className="row">
          <ViabilityMatrix topic={run.topic} axisSources={axisSources} weights={weights} onWeights={setWeights} />
          <TopicPanel topic={run.topic} />
        </section>

        {design && run.design && uncertainty && (
          <WhatIf
            design={design}
            baseline={run.design}
            report={uncertainty}
            live={mode === "api"}
            pending={whatIfPending}
            error={whatIfError}
            onDesign={setDesign}
          />
        )}

        {(run.sim || run.design) && (
          <section className="row">
            {run.sim && <RunReplay sim={run.sim} design={run.design} />}
            <div className="stack">
              {run.sim && <RunCost sim={run.sim} />}
              {run.design && <Evidence design={run.design} />}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
