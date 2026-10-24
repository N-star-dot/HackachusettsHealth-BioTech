// The research-question form: the query text, the sim-run count, and submit.

import type { DataMode } from "../api";

interface Props {
  query: string;
  onQuery: (q: string) => void;
  runs: number;
  onRuns: (n: number) => void;
  mode: DataMode;
  loading: boolean;
  onSubmit: () => void;
}

const RUNS_MIN = 1;
const RUNS_MAX = 5000;

export function QueryForm({ query, onQuery, runs, onRuns, mode, loading, onSubmit }: Props) {
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit();
  }

  function handleRuns(e: React.ChangeEvent<HTMLInputElement>) {
    const n = Number(e.target.value) || RUNS_MIN;
    onRuns(Math.max(RUNS_MIN, Math.min(RUNS_MAX, n)));
  }

  return (
    <form className="card query" onSubmit={handleSubmit}>
      <div className="field field--grow">
        <label htmlFor="query">Research question</label>
        <input id="query" value={query} onChange={(e) => onQuery(e.target.value)} required />
      </div>
      <div className="field field--narrow">
        <label htmlFor="runs">Sim runs</label>
        <input
          id="runs"
          type="number"
          min={RUNS_MIN}
          max={RUNS_MAX}
          value={runs}
          onChange={handleRuns}
          className="mono"
        />
      </div>
      <button type="submit" className="btn btn--primary" disabled={loading}>
        {loading ? "Running…" : mode === "mock" ? "Load mocks" : "Run pipeline"}
      </button>
    </form>
  );
}
