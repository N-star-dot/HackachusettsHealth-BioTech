# Data contracts — design

## Shared pieces (`backend/contracts/common.py`)
- `SourceType` enum: `openalex | pubmed | chembl_activity | paper | spec | simulator |
  simulated`.
- `Source { type, id, url? }` — attached to every real number.
- `SafetyGate { pass, reasons[] }` — pass/fail, checked before scoring.

## TopicReport (stage 1)
`query, topic{openalex_id,name}, counts_by_year[{year,works,source}], momentum{p_growth,model},
neighbors[], matrix{5 axes, weights, total}, safety`.
- `ViabilityMatrix` validates `total` == weighted mean of axes (normalised by weight sum),
  so producers can't ship an inconsistent score. Helper `weighted_total()` computes it the
  same way.

## ExperimentDesign (stage 2)
`design_id, topic_id, assay, prior_ic50{median_nM,n,spread_log10,source}, dilution{top,factor,points},
replicates, controls, plate, volumes_uL, pipette, tiprack, rationale[{claim,pmid,verified}]`.
- `Dilution` exposes `bottom_nM()` and `log10_span_each_side(prior)` so the Skeptic can check
  the range covers the prior by >= 2 log units each side.

## SimResult (stage 3)
`design_id, protocol_file, simulator{pass,error,log_lines,seconds,opentrons_version},
cost{tips,compound_uL,plates,robot_steps}, steps[]`.

## UncertaintyReport (stage 4)
`design_id, label="simulated", runs, seed, noise{...,sources[]}, fold_error{median,p90},
outside_range_share, failed_fit_share, calibration{coverage_90,pairs}, next_experiments[]`.
- The whole block is `simulated` because readouts are synthetic, but each **noise level**
  still carries a real `Source` (Kalliokoski DOI, Opentrons spec).

## Why Pydantic v2
Validation at the boundary catches contract drift immediately, `model_dump(by_alias=True)`
gives the JSON shape the dashboard expects (e.g. `pass` not `passed`), and the models double
as living documentation.
