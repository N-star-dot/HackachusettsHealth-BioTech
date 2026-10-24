# Protocol & simulator — requirements

Stage 3. A fixed template turns an `ExperimentDesign` into an Opentrons Flex program,
then the simulator passes it or names the exact error.

## Requirements
1. **Fixed-template compiler.** No LLM-generated code runs. The template is parameterised only
   by validated design fields.
2. **Flex-correct output.** Letter-number deck slots (D1, D2...), API level 2.20, and a
   `protocol.load_trash_bin("A3")` call (or the simulator halts at the first tip drop).
3. **Simulator wrapper.** Run through `opentrons.simulate`; on pass, return step log + timing;
   on failure, return the exact error. If opentrons isn't installed, fall back to a static
   check that still produces a valid `SimResult` and a clear message.
4. **Cost breakdown.** tips, compound µL, plates, robot steps — feeds the planner and matrix.

## Acceptance
- `compile_design(design)` writes `protocols/<id>.py`; `simulate_protocol` returns a valid
  `SimResult`. Report simulator pass rate in `scripts/eval_metrics.py`.

## Status
Compiler + wrapper working with offline static fallback. TODO: run in a Python <=3.13 env
with `pip install -e ".[robot]"` to exercise the real simulator and record the ~0.14s timing.
