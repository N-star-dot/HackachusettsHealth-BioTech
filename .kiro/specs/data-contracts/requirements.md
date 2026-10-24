# Data contracts — requirements

The four JSON contracts are the interface between the five stages. They let three
code owners plus the pipeline teammate build in parallel against mocks.

## Requirements

1. **Four contracts exist and are versioned in one place.** TopicReport, ExperimentDesign,
   SimResult, UncertaintyReport, defined as Pydantic v2 models in `backend/contracts`.
2. **Provenance is mandatory.** Every number either carries a `Source`, or lives inside a
   block explicitly labelled `simulated`. The models enforce this structurally.
3. **Contracts validate.** A mock JSON for each contract lives in `mocks/` and is validated
   in CI (`tests/test_mocks_validate.py`). A stale mock fails the build.
4. **Safety is a gate.** TopicReport carries a `SafetyGate` (pass/reasons) that downstream
   stages must honour — a failing gate stops the pipeline.
5. **Contracts are frozen by 11:00 AM** on build day. Changes after that go through this
   spec first, then the models.

## Acceptance
- `python -m pytest tests/test_mocks_validate.py` passes.
- `run_pipeline()` produces objects that serialise to the contract shapes without manual edits.
