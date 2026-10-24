# Topic scoring — requirements

Stage 1. Turns a free-text topic into a `TopicReport`: momentum, novelty, viability
matrix, neighbours — with the safety gate running first.

## Requirements
1. **Safety gate runs before any scoring.** A blocked topic yields a failing `SafetyGate`
   and no downstream work.
2. **Real publication counts.** Yearly works per topic from OpenAlex (cached), 2015–2024.
3. **Momentum model.** `HistGradientBoostingClassifier` predicts p(topic grows faster than
   median 2020–2024) from features computed on data **through 2019 only** (counts 2015–2019,
   log-count growth slope, acceleration, volatility, field). Label from 2020–2024 growth vs
   median; 2025–2026 skipped (indexing lag). Must beat the slope-only baseline on held-out
   AUROC to earn its place.
4. **Novelty gap.** The topic's recent works vs its neighbours'. Higher = less crowded.
5. **Viability matrix.** Five axes (momentum, novelty, evidence, automatable, cost_time),
   each 0–1, combined with adjustable weights (dashboard sliders, start equal). Safety is a
   gate, not an axis.

## Acceptance
- `score_topic(query)` returns a valid `TopicReport` with the safety gate applied.
- Momentum model AUROC reported vs the slope baseline in `scripts/eval_metrics.py`.
- Matrix `total` equals the weighted mean of its axes (enforced by the contract validator).

## Status
Working stub in place (`scoring.py`) producing valid reports from heuristics + cached
OpenAlex. TODO: train and load the real HGB model (owner A); wire live novelty from neighbours.
