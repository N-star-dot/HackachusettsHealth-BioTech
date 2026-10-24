"""Stage 3: Opentrons simulator wrapper. Owner B.

Runs the compiled protocol through `opentrons.simulate`, which validates it against
the Flex hardware model in ~0.14s and returns a step-by-step run log. If the
opentrons package is not installed (it pins Python <=3.13 and is heavy), we fall back
to a static analyser that still produces a valid SimResult and a clear message.

The run log is parsed into STRUCTURED ProtocolStep records (B0.4) the dashboard can
replay: action, volume, slot/well, and source/dest locations, filled from the payload
fields first and the human-readable text only as a fallback.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from backend.contracts import (
    CostBreakdown,
    DeckSlot,
    ExperimentDesign,
    ProtocolStep,
    SimResult,
    SimulatorInfo,
    StepLocation,
)
from backend.stage3_protocol.compiler import DECK

try:  # opentrons is optional (install with: pip install -e ".[robot]")
    from opentrons import simulate as _ot_simulate  # type: ignore

    _HAVE_OPENTRONS = True
except Exception:  # pragma: no cover - depends on environment
    _ot_simulate = None
    _HAVE_OPENTRONS = False

# "A1 of Corning 96 Well Plate 360 µL Flat on slot D2"
_LOC = re.compile(r"^(?P<well>[A-P]\d{1,2}) of (?P<labware>.+?) on slot (?P<slot>[A-D][1-4])$")
# "Trash Bin on slot A3"
_SLOT_ONLY = re.compile(r"^(?P<labware>.+?) on slot (?P<slot>[A-D][1-4])$")
_ACTIONS = [
    ("Picking up tip", "pick_up_tip"), ("Dropping tip", "drop_tip"),
    ("Aspirating", "aspirate"), ("Dispensing", "dispense"), ("Mixing", "mix"),
    ("Transferring", "transfer"), ("Blowing out", "blow_out"),
    ("Touching tip", "touch_tip"), ("Moving to", "move_to"),
]
_LEAF_ACTIONS = frozenset(
    {"pick_up_tip", "drop_tip", "aspirate", "dispense", "blow_out", "touch_tip", "move_to"}
)


def _parse_location(value) -> StepLocation | None:
    """Parse a payload location (object or string) into a StepLocation."""
    if value is None:
        return None
    s = str(value)
    m = _LOC.match(s)
    if m:
        return StepLocation(well=m.group("well"), labware=m.group("labware").strip(),
                            slot=m.group("slot"))
    m = _SLOT_ONLY.match(s)
    if m:
        return StepLocation(well=None, labware=m.group("labware").strip(), slot=m.group("slot"))
    return None


# location embedded in a text line, e.g. "... from A1 of Foo on slot D1",
# "... into A1 of Bar on slot D2", "... into Trash Bin on slot A3", possibly followed by
# a trailing clause like " at 716.0 uL/sec" (so we do NOT anchor to end-of-string).
_TEXT_LOC = re.compile(
    r"(?:from|into|to|at)\s+"
    r"(?P<rest>(?:[A-P]\d{1,2} of )?.+? on slot [A-D][1-4])"
)


def _location_from_text(text: str) -> StepLocation | None:
    m = _TEXT_LOC.search(text.strip())
    if not m:
        return None
    return _parse_location(m.group("rest").strip())


def _action_from_text(text: str) -> str:
    for prefix, action in _ACTIONS:
        if text.startswith(prefix):
            return action
    return "other"


def _extract_steps(run_log: list) -> list[ProtocolStep]:
    """Parse the Opentrons run log into structured ProtocolSteps (one per log entry)."""
    steps: list[ProtocolStep] = []
    for i, entry in enumerate(run_log):
        if not isinstance(entry, dict):
            steps.append(ProtocolStep(i=i, action="other"))
            continue
        payload = entry.get("payload", {}) or {}
        text = payload.get("text", "") or ""
        action = _action_from_text(text)

        uL = payload.get("volume")
        try:
            uL = float(uL) if uL is not None else None
        except (TypeError, ValueError):
            uL = None

        # locations: aspirate/dispense use 'location'; transfer uses 'source'/'dest'.
        # Payload fields first, then fall back to parsing the human-readable text.
        primary = _parse_location(payload.get("location")) or _location_from_text(text)
        source = _parse_location(payload.get("source"))
        dest = _parse_location(payload.get("dest"))
        # for aspirate the primary IS the source; for dispense it's the dest
        if source is None and action == "aspirate":
            source = primary
        if dest is None and action == "dispense":
            dest = primary

        loc = primary or source or dest
        reps = payload.get("repetitions")
        try:
            reps = int(reps) if reps is not None else None
        except (TypeError, ValueError):
            reps = None

        steps.append(ProtocolStep(
            i=i,
            action=action,
            uL=uL,
            labware=loc.labware if loc else None,
            well=loc.well if loc else None,
            level=int(entry.get("level", 0) or 0),
            text=text,
            slot=loc.slot if loc else None,
            source=source,
            dest=dest,
            repetitions=reps,
        ))
    return steps


def _deck_slots() -> list[DeckSlot]:
    return [DeckSlot(**d) for d in DECK]


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
                deck=_deck_slots(),
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
                deck=_deck_slots(),
            )

    # --- offline fallback: static check so the pipeline still produces a SimResult ---
    # Return NO steps (B0.4): the dashboard then says replay is unavailable rather than
    # replaying a fabricated run.
    elapsed = time.perf_counter() - start
    text = Path(protocol_file).read_text()
    has_trash = "load_trash_bin" in text
    error = None if has_trash else "Flex protocol missing load_trash_bin(); simulator would halt at first tip drop."
    return SimResult(
        design_id=design.design_id,
        protocol_file=str(protocol_file),
        simulator=SimulatorInfo(
            **{"pass": has_trash}, error=error, log_lines=0,
            seconds=round(elapsed, 3), opentrons_version="10.1.0 (not installed; static check)",
        ),
        cost=cost,
        steps=[],
        deck=_deck_slots(),
    )
