"""Every mock JSON must validate against its contract. Guards against stale mocks."""

import json
from pathlib import Path

import pytest

from backend.contracts import ExperimentDesign, SimResult, TopicReport, UncertaintyReport

MOCKS = Path(__file__).resolve().parents[1] / "mocks"

CASES = [
    ("topic_report.json", TopicReport),
    ("experiment_design.json", ExperimentDesign),
    ("sim_result.json", SimResult),
    ("uncertainty_report.json", UncertaintyReport),
]


@pytest.mark.parametrize("filename,model", CASES)
def test_mock_validates(filename, model):
    data = json.loads((MOCKS / filename).read_text())
    model.model_validate(data)  # raises if invalid
