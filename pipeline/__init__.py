"""Pipeline workstream (TEAMMATE-owned).

Two responsibilities:
  * ingest/   — pull OpenAlex, PubMed, ChEMBL, Semantic Scholar; cache every response
                to the database on first pull so the demo runs offline.
  * orchestrator.py — run stages 1->4 for a topic, persisting each contract to the DB.

Everything here is designed so the rest of the team mocks against it: the orchestrator
depends only on the stage functions and the data contracts, never on live network.
"""

from pipeline.orchestrator import run_pipeline

__all__ = ["run_pipeline"]
