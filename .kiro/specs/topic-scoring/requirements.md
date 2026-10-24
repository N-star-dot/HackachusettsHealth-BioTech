# Topic scoring — requirements

Stage 1. Turns a free-text topic into a `TopicReport`: momentum, novelty, viability
matrix, neighbours — with the safety gate running first.

## Requirements

1. **Safety gate runs before any scoring.** A blocked topic yields a failing `SafetyGate`
   and no downstream work.
2. **Real publication counts.** Yearly works per topic from OpenAlex (cached), 2015–2024.
3. **Momentum model.** `HistGradientBoostingClassifier` predicts p(topic grows faster than
   the median topic, 2020–2024) from features computed on data **through 2019 only**. The
   model must beat the slope-only baseline on held-out AUROC to earn its place.
4. **Novelty gap.** The topic's recent works vs its neighbours'. Higher = less crowded.
5. **Viability matrix.** Five axes (momentum, novelty, evidence, automatable, cost_time),
   each 0–1, combined with adjustable weights (dashboard sliders, start equal). Safety is a
   gate, not an axis.

## Momentum model (hgb-v3) — what shipped

### Features (2015–2019 only; no leakage)
A property test (`tests/test_feature_leakage.py`) asserts that changing any 2020–2024
count never changes any feature.

| Feature | What it measures | corr. with log_slope |
|---------|------------------|----------------------|
| `log_slope` | OLS slope of log10(count+1), 2015–2019 (the baseline signal) | 1.00 |
| `mean_log_level` | mean log10 count — how crowded the topic already is | 0.07 |
| `volatility` | std of residuals around the OLS line (ddof = n−2) | 0.14 |
| `last_year_jump` | log(2019) − log(2018) | 0.47 |
| `curvature` | quadratic coef of a degree-2 fit, x centred on 2017 | 0.02 |
| `field` | OpenAlex field, one-hot | — |

**Design history.** v1 used three noise features (acceleration/volatility as then
defined, works count) → the model *lost* to the baseline. v2 tried recency-weighted,
log-ratio and field-relative slopes, but those were 0.97–0.99 correlated with the plain
slope, so the model only *tied* the baseline. v3 keeps the two features with independent
signal and adds three genuinely independent *shape* features (correlations 0.02–0.47),
which is what finally beat the baseline.

### Label
1 if the topic's 2020–2024 growth (OLS slope of log10 counts) exceeds the **median** topic's
growth, else 0. 2025–2026 are excluded everywhere (OpenAlex indexing lag). The raw growth
value is stored (not as a feature) to compute top-decile precision.

### Evaluation — RepeatedStratifiedKFold (5 splits × 5 repeats = 25 test sets)
A single 80/20 split swings ~±0.025 AUROC — larger than the model-vs-baseline gap — so a
single split is not trustworthy. Repeated CV is the reported number.

| Metric | Model (hgb-v3) | Slope baseline |
|--------|----------------|----------------|
| AUROC (mean ± std) | **0.709 ± 0.024** | 0.697 ± 0.023 |
| Mean paired delta | **+0.013** | — |
| Folds won | **21 of 25** | — |
| Top-10% picks in real top-25% growers | **0.629** | 0.559 (chance = 0.25) |

**Honest caveat.** The ceiling here is the *label*, not the model: past-vs-future growth
rank correlation is ~0.41, and topics near the median boundary have near-coin-flip labels.
On the subset of topics whose label is clearly outside the measurement noise, the slope
alone already scores ~0.86. The learned model's value is a small but consistent AUROC gain
plus a clearly better top-decile precision (0.63 vs 0.56) — which is what the dashboard's
"most promising topics" ranking actually uses.

Rejected approaches, documented so we don't retry them:
- Regression on growth: AUROC 0.677, worse (7/25 wins).
- Dead-band on near-median labels: only "helps" by removing hard topics from the *test*
  set; training-only down-weighting gained nothing.
- Citation/works totals or topic names as features: leak the 2020–2026 answer.

## Acceptance
- `score_topic(query)` returns a valid `TopicReport` with the safety gate applied, using the
  trained model when present and a transparent slope heuristic otherwise.
- `scripts/train_momentum.py` reports the repeated-CV table above and pickles `hgb-v3`.
- Matrix `total` equals the weighted mean of its axes (enforced by the contract validator).
- No 2020–2024 count affects any feature (leakage property test).

## Status
Model trained (hgb-v3) and wired into `score_topic`. Counts pull live from cached OpenAlex.
TODO: live novelty from real neighbours (currently a placeholder neighbour).
