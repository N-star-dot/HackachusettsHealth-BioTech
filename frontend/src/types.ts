// TypeScript mirrors of the Pydantic contracts in backend/contracts.
// Keep these in step with the Python models; mocks/ shows sample payloads.

export type SourceType =
  | "openalex"
  | "pubmed"
  | "chembl_activity"
  | "semantic_scholar"
  | "paper"
  | "spec"
  | "simulator"
  | "simulated";

export interface Source {
  type: SourceType;
  id: string;
  url?: string | null;
}

export interface SafetyGate {
  pass: boolean;
  reasons: string[];
}

export const AXES = ["momentum", "novelty", "evidence", "automatable", "cost_time"] as const;
export type Axis = (typeof AXES)[number];
export type Weights = Record<Axis, number>;

export interface ViabilityMatrix extends Record<Axis, number> {
  weights: Weights;
  total: number;
}

export interface TopicReport {
  query: string;
  topic: { openalex_id: string; name: string };
  counts_by_year: { year: number; works: number; source: Source }[];
  momentum: { p_growth: number; model: string };
  neighbors: { openalex_id: string; name: string; works_last_5y: number; p_growth?: number | null }[];
  matrix: ViabilityMatrix;
  safety: SafetyGate;
}

export interface RationaleItem {
  claim: string;
  pmid: string;
  verified: boolean;
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
}

export interface ProtocolStep {
  i: number;
  action: string;
  uL?: number | null;
  labware?: string | null;
  well?: string | null;
}

export interface SimResult {
  design_id: string;
  protocol_file: string;
  simulator: { pass: boolean; error: string | null; log_lines: number; seconds: number; opentrons_version: string };
  cost: { tips: number; compound_uL: number; plates: number; robot_steps: number };
  steps: ProtocolStep[];
}

export interface NextExperiment {
  change: string;
  p90_fold_error_drop_pct: number;
  extra_tips: number;
  extra_compound_uL: number;
  extra_plates: number;
  score: number;
}

export interface UncertaintyReport {
  design_id: string;
  label: string;
  runs: number;
  seed: number;
  noise: {
    lab_spread_log10: number;
    pipette_cv: number;
    pipette_bias: number;
    reader_cv: number;
    sources: Source[];
  };
  fold_error: { median: number; p90: number };
  outside_range_share: number;
  failed_fit_share: number;
  calibration: { coverage_90: number; pairs: number };
  next_experiments: NextExperiment[];
}

/** Response of POST /api/run. */
export interface RunResponse {
  run_id: string;
  blocked: boolean;
  topic: TopicReport;
  design: ExperimentDesign | null;
  sim: SimResult | null;
  uncertainty: UncertaintyReport | null;
}
