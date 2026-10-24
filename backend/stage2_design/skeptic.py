"""Stage 2: the Skeptic — an LLM debate settled by simulation (B2.5). Owner B.

The Skeptic (Gemini) proposes at most 3 objections to the design, each a concrete change
to one numeric field. We CLAMP each proposal to the B1.1 limits, rerun the uncertainty
engine with the baseline's seed and runs, and record a ReviewTurn. The verdict is
"supported" only if the simulated p90 drops by >= 5%.

Crucial safety properties:
  * the argument is model text and is NEVER verified,
  * the design NEVER changes because of a model's argument — only the simulation decides,
  * without GEMINI_API_KEY (or on any LLM error) we skip and return [].
"""

from __future__ import annotations

import copy
import os

from backend.contracts import ExperimentDesign, ReviewTurn
from backend.stage3_protocol import cost_model
from backend.stage4_uncertainty import run_uncertainty

_FIELDS = ("dilution.top_nM", "dilution.factor", "dilution.points",
           "replicates", "volumes_uL.transfer")


def _apply_and_clamp(design: ExperimentDesign, field: str, value: float) -> ExperimentDesign | None:
    """Return a copy with `field` set to a B1.1-clamped `value`, or None if invalid."""
    d = copy.deepcopy(design)
    try:
        if field == "dilution.top_nM":
            d.dilution.top_nM = max(1.0, min(float(value), 100_000.0))
        elif field == "dilution.factor":
            d.dilution.factor = max(2.0, min(float(value), 10.0))
        elif field == "dilution.points":
            d.dilution.points = max(2, min(int(value), 11))
        elif field == "replicates":
            d.replicates = max(1, min(int(value), 8))
        elif field == "volumes_uL.transfer":
            d.volumes_uL.transfer = max(5.0, min(float(value), 100.0))
        else:
            return None
    except (TypeError, ValueError):
        return None

    # keep diluent consistent with the (possibly changed) factor, enforce 300 µL cap
    d.volumes_uL.diluent = d.volumes_uL.transfer * (d.dilution.factor - 1.0)
    if d.volumes_uL.transfer * d.dilution.factor > 300.0 + 1e-6:
        return None
    if d.dilution.points * d.replicates + d.controls.positive_wells + d.controls.negative_wells > 96:
        return None
    try:
        return ExperimentDesign.model_validate(d.model_dump())
    except Exception:
        return None


def _ask_gemini(design: ExperimentDesign) -> list[dict]:
    """Ask Gemini for <=3 objections as JSON. Returns [] without a key or on any error."""
    if not os.environ.get("GEMINI_API_KEY"):
        return []
    try:
        from google import genai  # google-genai
        from pydantic import BaseModel

        class _Objection(BaseModel):
            field: str
            proposed_value: float
            argument: str

        class _Objections(BaseModel):
            objections: list[_Objection]

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        prompt = (
            "You are a skeptical reviewer of a dose-response experiment design. Propose at "
            "most 3 concrete objections. Each objection changes exactly one of these fields: "
            f"{', '.join(_FIELDS)}. Give field, proposed_value (a number), and a one-sentence "
            "argument. Here is the design as JSON:\n" + design.model_dump_json()
        )
        resp = client.models.generate_content(
            model=os.environ.get("LLM_MODEL", "gemini-1.5-flash"),
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": _Objections.model_json_schema(),
                "temperature": 0,
            },
        )
        parsed = _Objections.model_validate_json(resp.text)
        return [o.model_dump() for o in parsed.objections[:3]]
    except Exception:
        return []


def review_design(
    design: ExperimentDesign, baseline_p90: float, runs: int, seed: int, reader_cv: float
) -> list[ReviewTurn]:
    """Run the Skeptic debate, settled by simulation. Empty when no LLM is available."""
    objections = _ask_gemini(design)
    base_cost = cost_model(design)
    turns: list[ReviewTurn] = []

    for obj in objections:
        field = obj.get("field")
        if field not in _FIELDS:
            continue
        cand = _apply_and_clamp(design, field, obj.get("proposed_value"))
        if cand is None:
            continue
        rep = run_uncertainty(cand, runs=runs, seed=seed, reader_cv=reader_cv,
                              calibrate_coverage=False)
        p90_after = rep.fold_error.p90
        cand_cost = cost_model(cand)
        drop = (baseline_p90 - p90_after) / max(baseline_p90 - 1.0, 1e-6)
        turns.append(ReviewTurn(
            role="skeptic",
            argument=str(obj.get("argument", ""))[:500],  # model text, never verified
            field=field,
            proposed_value=float(obj.get("proposed_value")),
            p90_before=round(baseline_p90, 4),
            p90_after=round(p90_after, 4),
            extra_tips=max(0, cand_cost["tips"] - base_cost["tips"]),
            extra_compound_uL=round(max(0.0, cand_cost["compound_uL"] - base_cost["compound_uL"]), 2),
            verdict="supported" if drop >= 0.05 else "not supported",
        ))
    return turns
