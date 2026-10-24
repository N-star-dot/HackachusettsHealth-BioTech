// Hand-written wire types mirroring backend/contracts (BRIEF Appendix A). Switch to the
// generated src/api/schema.d.ts once RunResponse appears in /openapi.json (npm run gen:api).
// Fields marked "added" may be missing — read them as optional.

export type SourceType =
  | "openalex" | "pubmed" | "chembl_activity" | "semantic_scholar" | "paper"
  | "spec" | "simulator" | "simulated" | "assumed";

export interface Source { type: SourceType; id: string; url?: string | null }

export interface SafetyGate { pass?: boolean; passed?: boolean; reasons: string[] }

export type AxisKey = "momentum" | "novelty" | "evidence" | "automatable" | "cost_time";

export interface TopicReport {
  query: string;
  topic: { openalex_id: string; name: string };
  counts_by_year: { year: number; works: number; source: Source }[];
  momentum: { p_growth: number; model: string };
  neighbors: {
    openalex_id: string; name: string; works_last_5y: number; p_growth?: number | null;
  }[];
  matrix: Record<AxisKey, number> & {
    weights: Record<AxisKey, number>;
    total: number;
    axis_sources?: Partial<Record<AxisKey, Source>>;
    axis_notes?: Partial<Record<AxisKey, string>>;
  };
  safety: SafetyGate;
  offline?: boolean;
}

export interface RationaleItem {
  claim: string;
  pmid: string;
  evidence_type: "chembl_activity" | "abstract_quote" | string;
  evidence_id: string;
  quote?: string | null;
  model_note?: string | null;
  status: "verified" | "partial" | "unverified" | string;
  reason?: string | null;
  verified: boolean;
  url?: string | null;
  document_chembl_id?: string | null;
}

export interface ReviewTurn {
  role: "skeptic"; argument: string; field: string; proposed_value: number;
  p90_before: number; p90_after: number; extra_tips: number; extra_compound_uL: number;
  verdict: "supported" | "not supported" | string;
}

export interface ExperimentDesign {
  design_id: string;
  topic_id: string;
  assay: { type: string; readout: string; target_chembl_id: string; compound_chembl_id: string };
  prior_ic50: { median_nM: number; n_measurements: number; spread_log10: number; source: Source };
  dilution: { top_nM: number; factor: number; points: number };
  replicates: number;
  controls: { positive_wells: number; negative_wells: number };
  plate: { labware: string; layout: string };
  volumes_uL: { transfer: number; diluent: number };
  pipette: string;
  tiprack: string;
  rationale: RationaleItem[];
  notes?: string[];
  review?: ReviewTurn[];
}

export interface StepLocation { slot: string | null; well: string | null; labware: string | null }

export interface ProtocolStep {
  i: number;
  action: string;
  uL?: number | null;
  labware?: string | null;
  well?: string | null;
  level?: number;
  text?: string;
  slot?: string | null;
  source?: StepLocation | null;
  dest?: StepLocation | null;
  repetitions?: number | null;
}

export interface DeckSlot {
  slot: string; load_name: string; display_name: string;
  role: "tips" | "plate" | "reservoir" | "trash" | string;
  contents?: Record<string, string>;
}

export interface SimResult {
  design_id: string;
  protocol_file: string;
  simulator: {
    pass?: boolean; passed?: boolean; error: string | null;
    log_lines: number; seconds: number; opentrons_version: string;
  };
  cost: { tips: number; compound_uL: number; plates: number; robot_steps: number; source?: Source | null };
  steps: ProtocolStep[];
  deck?: DeckSlot[];
}

export interface NextExperiment {
  change: string;
  p90_fold_error_drop_pct: number;
  extra_tips: number;
  extra_compound_uL: number;
  extra_plates: number;
  score: number;
  design?: ExperimentDesign | null;
  p90_after?: number | null;
}

export interface UncertaintyReport {
  design_id: string;
  label: string;
  runs: number;
  seed: number;
  noise: {
    lab_spread_log10: number; pipette_cv: number; pipette_bias: number; reader_cv: number;
    sources: Source[];
    field_sources?: Partial<Record<"lab_spread_log10" | "pipette_cv" | "pipette_bias" | "reader_cv", Source>>;
  };
  fold_error: { median: number; p90: number };
  outside_range_share: number;
  failed_fit_share: number;
  calibration: { coverage_90: number; pairs: number };
  next_experiments: NextExperiment[];
  samples?: { true_ic50_nM: number[]; recovered_ic50_nM: number[]; fold_error: number[] } | null;
  curve?: { concentrations_nM: number[]; activity_p10: number[]; activity_p50: number[]; activity_p90: number[] } | null;
}

export interface PairInfo {
  label: string; compound_chembl_id: string; target_chembl_id: string;
  compound_name: string; target_name: string; match: "user" | "query" | "default" | string;
}

export interface RunResponse {
  run_id: string;
  blocked: boolean;
  status?: string;
  pair?: PairInfo | null;
  topic: TopicReport | null;
  design: ExperimentDesign | null;
  sim: SimResult | null;
  uncertainty: UncertaintyReport | null;
}

export interface RunRecord extends RunResponse {
  meta: { run_id: string; query: string; created_at: string; status: string; error?: string | null };
}

export interface RunRequest {
  query: string;
  weights?: Record<AxisKey, number>;
  runs?: number;
  seed?: number;
  reader_cv?: number;
  compound_chembl_id?: string | null;
  openalex_topic_id?: string | null;
  mode?: "sync" | "async";
}

export interface WhatIfRequest {
  design: ExperimentDesign;
  runs?: number;
  seed?: number;
  reader_cv?: number;
  plan?: boolean;
}
