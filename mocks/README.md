# Mock contracts

One sample JSON per data contract. Build and test your stage against these so you
never wait on another workstream. They are validated by `tests/test_mocks_validate.py`
against the Pydantic models in `backend/contracts`, so if a contract changes and a
mock goes stale, CI catches it.

| File | Contract | Produced by | Consumed by |
|------|----------|-------------|-------------|
| `topic_report.json` | `TopicReport` | stage 1 | stages 2, 5 |
| `experiment_design.json` | `ExperimentDesign` | stage 2 | stages 3, 4 |
| `sim_result.json` | `SimResult` | stage 3 | stage 5 |
| `uncertainty_report.json` | `UncertaintyReport` | stage 4 | stage 5 |

The values are placeholders, not results. Every number carries a `source`, or sits
inside a block labelled `simulated`.
