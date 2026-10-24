import topicMock from "../../mocks/topic_report.json";
import designMock from "../../mocks/experiment_design.json";
import simMock from "../../mocks/sim_result.json";
import uncertaintyMock from "../../mocks/uncertainty_report.json";
import type { ExperimentDesign, RunResponse, SimResult, TopicReport, UncertaintyReport, Weights } from "./types";

export type DataMode = "mock" | "api";

export interface RunParams {
  query: string;
  runs: number;
  seed: number;
  weights?: Weights;
}

/** The mocks/ payloads shaped like a POST /api/run response. */
export function mockRun(query?: string): RunResponse {
  const topic = structuredClone(topicMock) as TopicReport;
  if (query) topic.query = query;
  return {
    run_id: "mock",
    blocked: !topic.safety.pass,
    topic,
    design: structuredClone(designMock) as ExperimentDesign,
    sim: structuredClone(simMock) as SimResult,
    uncertainty: structuredClone(uncertaintyMock) as UncertaintyReport,
  };
}

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${path} failed (${res.status})${detail ? `: ${detail.slice(0, 200)}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export function runPipeline(params: RunParams, signal?: AbortSignal): Promise<RunResponse> {
  return post<RunResponse>("/api/run", params, signal);
}

export function rerunUncertainty(
  design: ExperimentDesign,
  runs: number,
  seed: number,
  signal?: AbortSignal,
): Promise<UncertaintyReport> {
  return post<UncertaintyReport>("/api/uncertainty", { design, runs, seed }, signal);
}
