"""Stage 2: experiment design (deterministic designer + citation checker). Owner B."""

from backend.stage2_design.citation_checker import check_citations, citation_error_rate
from backend.stage2_design.demo_pairs import get_demo_pair, load_demo_pairs
from backend.stage2_design.designer import design_experiment, design_from_pair

__all__ = [
    "design_experiment",
    "design_from_pair",
    "check_citations",
    "citation_error_rate",
    "get_demo_pair",
    "load_demo_pairs",
]
