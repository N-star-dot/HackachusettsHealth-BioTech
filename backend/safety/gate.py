"""Safety gate.

Blocks topics that fall outside the intended use: benign, student-scale, in-vitro
dose-response biochemistry. A fail here stops the pipeline before any scoring.

This is intentionally a conservative keyword gate for the hackathon. It is a GATE,
not an axis — a failing topic is blocked no matter how it would otherwise score.
Extend the blocklist in one place; the spec documents the policy.
"""

from __future__ import annotations

from backend.contracts.common import SafetyGate

# Topics we refuse to design experiments for. Kept short and explicit so judges can
# read exactly what is blocked. Case-insensitive substring match on the query.
_BLOCKED_TERMS: tuple[str, ...] = (
    "bioweapon",
    "biological weapon",
    "nerve agent",
    "chemical weapon",
    "select agent",
    "gain of function",
    "gain-of-function",
    "pathogen enhancement",
    "toxin synthesis",
    "human subject",
    "human trial",
    "in vivo human",
)


def check_topic_safety(query: str) -> SafetyGate:
    """Return a SafetyGate for a free-text topic query."""
    q = (query or "").lower()
    reasons = [term for term in _BLOCKED_TERMS if term in q]
    if reasons:
        return SafetyGate(
            **{"pass": False},
            reasons=[f"blocked term: '{t}'" for t in reasons],
        )
    return SafetyGate(**{"pass": True}, reasons=[])
