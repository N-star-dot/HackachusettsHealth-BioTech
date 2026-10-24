import { useMemo, useState } from "react";
import { QueryForm } from "./components/QueryForm";
import { RunReplay } from "./components/RunReplay";
import { Evidence, RunCost } from "./components/SidePanels";
import { TopBar } from "./components/TopBar";
import { TopicPanel } from "./components/TopicPanel";
import { ViabilityMatrix } from "./components/ViabilityMatrix";
import { WhatIf } from "./components/WhatIf";
import { useDataMode } from "./hooks/useDataMode";
import { SEED, useRun } from "./hooks/useRun";
import { useWhatIf } from "./hooks/useWhatIf";
import { axisProvenance } from "./sources";

export default function App() {
  const [mode, setMode] = useDataMode();
  const [query, setQuery] = useState("kinase inhibitors for liver fibrosis");
  const [runs, setRuns] = useState(1000);

  const state = useRun();
  const { run, weights, design, uncertainty } = state;

  const whatIf = useWhatIf({
    live: mode === "api",
    runs,
    run,
    design,
    setUncertainty: state.setUncertainty,
  });

  const axisSources = useMemo(() => axisProvenance(run), [run]);
  const safety = run.topic.safety;

  return (
    <div className="app">
      <TopBar mode={mode} onMode={setMode} runId={run.run_id} seed={SEED} safety={safety} />

      <main className="page">
        <QueryForm
          query={query}
          onQuery={setQuery}
          runs={runs}
          onRuns={setRuns}
          mode={mode}
          loading={state.loading}
          onSubmit={() => state.submit(mode, query, runs)}
        />

        {state.error && <p className="notice notice--error">{state.error}</p>}
        {run.blocked && (
          <p className="notice notice--error">
            This topic was blocked by the safety gate
            {safety.reasons.length ? `: ${safety.reasons.join("; ")}` : ""}. No design was produced.
          </p>
        )}

        <section className="row">
          <ViabilityMatrix
            topic={run.topic}
            axisSources={axisSources}
            weights={weights}
            onWeights={state.setWeights}
          />
          <TopicPanel topic={run.topic} />
        </section>

        {design && run.design && uncertainty && (
          <WhatIf
            design={design}
            baseline={run.design}
            report={uncertainty}
            live={mode === "api"}
            pending={whatIf.pending}
            error={whatIf.error}
            onDesign={state.setDesign}
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
