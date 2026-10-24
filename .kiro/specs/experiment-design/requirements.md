# Experiment design — requirements

Stage 2. The Designer LLM writes an `ExperimentDesign` as **JSON, never code**.

## Requirements
1. **LLM writes JSON only.** No generated code ever runs; the stage-3 compiler is a fixed template.
2. **Grounded design.** Inputs: the topic, top PubMed abstracts, and the ChEMBL IC50 prior.
   The dilution range must cover the prior by ~2 log units each side.
3. **Every claim cites a PMID.** The citation checker resolves each PMID and compares titles;
   unverified claims get a red flag. Report citation error rate before/after checking.
4. **Skeptic (optional, cut first).** Checks for controls, >=3 replicates, >=2 log-unit range
   each side, and no transfer < 5 µL; sends fixes back, at most 2 rounds.
5. **Debate ablation (stretch).** Designer alone vs Designer+Skeptic on 10 topics; report either way.

## Acceptance
- `design_experiment(topic_id)` returns a valid `ExperimentDesign`.
- `check_citations` marks items verified only when the PMID resolves (offline => none verified).

## Status
Deterministic stub designer in place so downstream stages run offline. TODO: wire the LLM
(set `OPENAI_API_KEY`), connect the checker to `pipeline.ingest.pubmed.fetch_title`.
