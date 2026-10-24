"""Safety gate. Runs BEFORE any scoring in stage 1."""

from backend.safety.gate import check_topic_safety

__all__ = ["check_topic_safety"]
