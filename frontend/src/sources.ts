// Provenance helpers shared across the dashboard.
// Every displayed number traces back to a Source (or a `simulated` block); these
// builders keep that mapping in one place instead of inlined in each component.

import type { AxisProvenance } from "./components/ViabilityMatrix";
import type { RunResponse, Source } from "./types";

/** The OpenAlex topic a run is about. */
export function topicSource(run: RunResponse): Source {
  return { type: "openalex", id: run.topic.topic.openalex_id };
}

/** The Opentrons simulator run, when the pipeline produced one. */
export function simSource(run: RunResponse): Source | null {
  if (!run.sim) return null;
  return {
    type: "simulator",
    id: `${run.sim.design_id} · opentrons ${run.sim.simulator.opentrons_version}`,
  };
}

/** Where each viability-matrix axis score comes from. */
export function axisProvenance(run: RunResponse): AxisProvenance {
  const topic = topicSource(run);
  const sim = simSource(run);
  const automation = sim ? [sim] : [topic];

  return {
    momentum: { source: [topic], note: `Momentum model ${run.topic.momentum.model}` },
    novelty: { source: [topic], note: "Stage 1 score from the topic and its neighbors" },
    evidence: {
      source: run.design ? [topic, run.design.prior_ic50.source] : [topic],
      note: "Stage 1 score",
    },
    automatable: { source: automation, note: "Stage 1 score" },
    cost_time: { source: automation, note: "Stage 1 score" },
  };
}
