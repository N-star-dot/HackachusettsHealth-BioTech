"""Load the frozen demo (target, compound) pairs. Owner B.

data/demo/demo_pairs.json holds real ChEMBL pairs with their priors and per-paper
values, so the deterministic designer needs no network. Regenerate the file with
scripts/build_demo_pairs.py.
"""

from __future__ import annotations

import json
from pathlib import Path

_DEMO_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "demo_pairs.json"
_EVIDENCE_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "evidence.json"


def load_demo_pairs() -> list[dict]:
    if not _DEMO_PATH.exists():
        return []
    return json.loads(_DEMO_PATH.read_text())


def load_evidence() -> dict[str, dict]:
    """compound_chembl_id -> {pmid -> {pmid, title, abstract, ...}}. Empty if not built."""
    if not _EVIDENCE_PATH.exists():
        return {}
    return json.loads(_EVIDENCE_PATH.read_text())


def evidence_abstracts_for(compound_chembl_id: str) -> dict[str, str]:
    """pmid -> abstract text for one compound (what the checker needs). Empty if absent."""
    ev = load_evidence().get(compound_chembl_id, {})
    return {pmid: rec["abstract"] for pmid, rec in ev.items()}


def get_demo_pair(compound_chembl_id: str | None = None) -> dict | None:
    """Return the pair for `compound_chembl_id`, or the first pair if None/not found."""
    pairs = load_demo_pairs()
    if not pairs:
        return None
    if compound_chembl_id:
        for p in pairs:
            if p.get("compound_chembl_id") == compound_chembl_id:
                return p
    return pairs[0]
