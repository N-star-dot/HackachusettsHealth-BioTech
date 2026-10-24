"""Stage 2: experiment design (Designer LLM + citation checker). Owner B."""

from backend.stage2_design.citation_checker import check_citations, citation_error_rate
from backend.stage2_design.designer import design_experiment

__all__ = ["design_experiment", "check_citations", "citation_error_rate"]
