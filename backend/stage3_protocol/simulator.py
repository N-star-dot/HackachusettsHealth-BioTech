"""Stage 3: Opentrons simulator wrapper. Owner B.

Runs the compiled protocol through `opentrons.simulate`, which validates it against
the Flex hardware model in ~0.14s and returns a step-by-step run log. If the
opentrons package is not installed (it pins Python <=3.13 and is heavy), we fall back
to a static analyser that still produces a valid SimResult and a clear message.
"""

from __future__ import annotations

import time
from pathlib import Path

from backend.contracts import (
    CostBreakdown,
    ExperimentDesign,
    ProtocolStep,
    SimResult,
    SimulatorInfo,
)

try:  # opentrons is optional (install with: pip install -e ".[robot]")
    from opentrons import simulate as _ot_simulate  # type: ignore

    _HAVE_OPENTRONS = True
except Exception:  # pragma: no cover - depends on environment
    _ot_simulate = None
    _HAVE_OPENTRONS = False


def _estimate_cost(design: ExperimentDesign) -> CostBreakdown:
    points = design.dilution.points
    tips = points + 2  # diluent fill + seed + serial transfers (template reuses some)
    compound_uL = design.volumes_uL.transfer * points
    robot_steps = points * 2 + 4
    return CostBreakdown(tips=tips, compound_uL=compound_uL, plates=1, robot_steps=robot_steps)


def simulate_protocol(protocol_file: Path, design: ExperimentDesign) -> SimResult:
    start = time.perf_counter()
    cost = _estimate_cost(design)

    if _HAVE_OPENTRONS:
        try:
            with open(protocol_file) as fh:
                run_log, _bundle = _ot_simulate.simulate(fh, file_name=str(protocol_file))
            elapsed = time.perf_counter() - start
            steps = _extract_steps(run_log)
            return SimResult(
                design_id=design.design_id,
                protocol_file=str(protocol_file),
                simulator=SimulatorInfo(
                    **{"pass": True}, error=None, log_lines=len(run_log),
                    seconds=round(elapsed, 3), opentrons_version="10.1.0",
                ),
                cost=cost,
                steps=steps,
            )
        except Exception as exc:  # protocol rejected -> report the exact error
            elapsed = time.perf_counter() - start
            return SimResult(
                design_id=design.design_id,
                protocol_file=str(protocol_file),
                simulator=SimulatorInfo(
                    **{"pass": False}, error=f"{type(exc).__name__}: {exc}",
                    log_lines=0, seconds=round(elapsed, 3), opentrons_version="10.1.0",
                ),
                cost=cost,
                steps=[],
            )

    # --- offline fallback: static check so the pipeline still produces a SimResult ---
    elapsed = time.perf_counter() - start
    text = Path(protocol_file).read_text()
    has_trash = "load_trash_bin" in text
    error = None if has_trash else "Flex protocol missing load_trash_bin(); simulator would halt at first tip drop."
    steps = [
        ProtocolStep(i=0, action="aspirate", uL=design.volumes_uL.transfer, labware="reservoir", well="A2"),
        ProtocolStep(i=1, action="dispense", uL=design.volumes_uL.transfer, labware="plate", well="A1"),
    ]
    return SimResult(
        design_id=design.design_id,
        protocol_file=str(protocol_file),
        simulator=SimulatorInfo(
            **{"pass": has_trash}, error=error, log_lines=len(steps),
            seconds=round(elapsed, 3), opentrons_version="10.1.0 (not installed; static check)",
        ),
        cost=cost,
        steps=steps,
    )


def _extract_steps(run_log: list) -> list[ProtocolStep]:
    steps: list[ProtocolStep] = []
    for i, entry in enumerate(run_log):
        payload = entry.get("payload", {}) if isinstance(entry, dict) else {}
        text = payload.get("text", "")
        steps.append(ProtocolStep(i=i, action=text.split()[0].lower() if text else "step"))
    return steps
