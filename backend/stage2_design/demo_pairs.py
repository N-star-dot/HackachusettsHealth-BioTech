"""Load the frozen demo (target, compound) pairs. Owner B.

data/demo/demo_pairs.json holds real ChEMBL pairs with their priors and per-paper
values, so the deterministic designer needs no network. Regenerate the file with
scripts/build_demo_pairs.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_DEMO_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "demo_pairs.json"
_EVIDENCE_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "evidence.json"

# Keyword -> compound_chembl_id for matching a free-text question to a prepared pair.
# Order within each list doesn't matter; longer/more-specific lists are still just OR.
_PAIR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "CHEMBL554": ("her2", "erbb2", "lapatinib"),
    "CHEMBL10": ("p38", "mapk14", "sb-203580", "sb203580"),
    "CHEMBL221959": ("jak", "jak2", "janus kinase", "tofacitinib"),
}


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


def pair_names(pair: dict) -> tuple[str, str]:
    """Split a pair label 'lapatinib on HER2' -> ('lapatinib', 'HER2'). Falls back to ids."""
    label = pair.get("label", "")
    if " on " in label:
        compound, target = label.split(" on ", 1)
        return compound.strip(), target.strip()
    return pair.get("compound_chembl_id", ""), pair.get("target_chembl_id", "")


def _keyword_hit(query: str, keywords: tuple[str, ...]) -> bool:
    """Case-insensitive word-boundary match of any keyword in the query."""
    q = query.lower()
    for kw in keywords:
        # \b doesn't work around hyphens/digits cleanly, so bound on non-alphanumerics
        if re.search(rf"(?<![a-z0-9]){re.escape(kw.lower())}(?![a-z0-9])", q):
            return True
    return False


def match_pair(query: str, compound_chembl_id: str | None = None) -> tuple[dict, str]:
    """Choose a demo pair for a question.

    A supplied compound_chembl_id wins (match 'user'). Else the first keyword hit in the
    query (match 'query'). Else the first pair (match 'default'). Returns (pair, match).
    """
    pairs = load_demo_pairs()
    if not pairs:
        raise RuntimeError("no demo pairs on disk — run scripts/build_demo_pairs.py")
    by_id = {p["compound_chembl_id"]: p for p in pairs}

    if compound_chembl_id and compound_chembl_id in by_id:
        return by_id[compound_chembl_id], "user"

    for p in pairs:  # preserve file order for deterministic 'first hit'
        cid = p["compound_chembl_id"]
        if cid in _PAIR_KEYWORDS and _keyword_hit(query, _PAIR_KEYWORDS[cid]):
            return p, "query"

    return pairs[0], "default"
