"""Build the frozen evidence set for the demo pairs. Owner B.

For each demo pair: take the document_chembl_ids behind its prior, fetch each ChEMBL
document (pubmed_id, title, year), skip documents with no pubmed_id, then one batched
PubMed EFetch per pair for the abstracts. Keep at most 8 papers with an abstract per
pair. Freeze to data/demo/evidence.json (committed) so the demo + checker run offline.

    python scripts/build_evidence.py

Everything is cached in api_cache, so re-runs are offline and free.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from pipeline.ingest import chembl, pubmed

_DEMO = Path(__file__).resolve().parents[1] / "data" / "demo" / "demo_pairs.json"
_OUT = Path(__file__).resolve().parents[1] / "data" / "demo" / "evidence.json"
_MAX_PER_PAIR = 8


def main() -> int:
    if not _DEMO.exists():
        print("demo_pairs.json missing — run scripts/build_demo_pairs.py", file=sys.stderr)
        return 1
    pairs = json.loads(_DEMO.read_text())

    evidence: dict[str, dict] = {}  # compound_chembl_id -> {pmid -> {pmid,title,abstract,year,...}}
    for pair in pairs:
        compound = pair["compound_chembl_id"]
        doc_ids = pair.get("document_ids", [])

        # ChEMBL documents -> pubmed metadata (skip those without a pubmed id)
        docs = []
        for doc_id in doc_ids:
            meta = chembl.fetch_document(doc_id)
            if meta:
                docs.append(meta)
        pmid_meta = {d["pubmed_id"]: d for d in docs}

        # one batched EFetch for all PMIDs of this pair
        abstracts = pubmed.fetch_abstracts(list(pmid_meta.keys()))

        pair_evidence: dict[str, dict] = {}
        for pmid, art in abstracts.items():
            meta = pmid_meta.get(pmid, {})
            pair_evidence[pmid] = {
                "pmid": pmid,
                "title": art["title"],
                "abstract": art["abstract"],
                "year": meta.get("year"),
                "journal": meta.get("journal"),
                "document_chembl_id": meta.get("document_chembl_id"),
            }
            if len(pair_evidence) >= _MAX_PER_PAIR:
                break

        evidence[compound] = pair_evidence
        print(f"  {pair['label']}: {len(docs)} docs w/ pubmed id, "
              f"{len(pair_evidence)} abstracts kept")

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(evidence, indent=2))
    total = sum(len(v) for v in evidence.values())
    print(f"\nWrote evidence for {len(evidence)} pairs ({total} abstracts) to {_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
