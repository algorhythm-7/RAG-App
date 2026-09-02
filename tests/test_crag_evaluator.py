"""Unit tests for Corrective RAG (CRAG) evaluator and context guardrail."""

import pytest
from src.components.crag_evaluator import CRAGEvaluator
from src.models import CRAGReport, Passage


@pytest.fixture
def evaluator():
    return CRAGEvaluator(correct_threshold=0.55, ambiguous_threshold=0.28)


@pytest.fixture
def high_relevance_candidates():
    return [
        (
            Passage(
                text="The recommended tire pressure is 32 psi cold for front and rear tires.",
                section="Page 45",
                document_id="doc-1",
            ),
            0.78,
        ),
        (
            Passage(
                text="Tire rotation should be performed every 6,000 miles (10,000 km).",
                section="Page 46",
                document_id="doc-1",
            ),
            0.58,
        ),
        (
            Passage(
                text="Air conditioning compressor clutch relay is in Power Distribution Center.",
                section="Page 112",
                document_id="doc-1",
            ),
            0.12,
        ),
    ]


@pytest.fixture
def out_of_scope_candidates():
    return [
        (
            Passage(
                text="Preheat oven to 350 degrees F and bake cookies for 12 minutes.",
                section="Page 1",
                document_id="doc-2",
            ),
            0.15,
        ),
        (
            Passage(
                text="The moon orbits the Earth once every 27.3 days.",
                section="Page 2",
                document_id="doc-2",
            ),
            0.08,
        ),
    ]


class TestCRAGEvaluator:
    """Tests for CRAGEvaluator grading and filtering."""

    def test_evaluate_correct_grade(self, evaluator, high_relevance_candidates):
        """Test that high-confidence candidates receive CORRECT grade and filter noise."""
        query = "tire pressure specification"
        filtered, report = evaluator.evaluate_and_filter(query, high_relevance_candidates)

        assert isinstance(report, CRAGReport)
        assert report.relevance_grade == "CORRECT"
        assert report.confidence_score >= 0.55
        assert len(filtered) >= 1
        # The AC compressor noise chunk with 0.12 score should be filtered out
        assert len(filtered) < len(high_relevance_candidates)
        assert all(p.section != "Page 112" for p, _ in filtered)

    def test_evaluate_out_of_scope_grade(self, evaluator, out_of_scope_candidates):
        """Test that low-scoring passages trigger OUT_OF_SCOPE guardrail grade."""
        query = "how to bake chocolate chip cookies"
        filtered, report = evaluator.evaluate_and_filter(query, out_of_scope_candidates)

        assert report.relevance_grade == "OUT_OF_SCOPE"
        assert report.confidence_score < 0.28
        assert any("out-of-scope" in a.lower() for a in report.actions_taken)

    def test_evaluate_empty_input(self, evaluator):
        """Test evaluation with zero candidates."""
        filtered, report = evaluator.evaluate_and_filter("any query", [])

        assert filtered == []
        assert report.relevance_grade == "OUT_OF_SCOPE"
        assert report.confidence_score == 0.0

    def test_crag_score_breakdown_metadata(self, evaluator, high_relevance_candidates):
        """Test that score breakdown correctly records section and status."""
        query = "tire pressure"
        _, report = evaluator.evaluate_and_filter(query, high_relevance_candidates)

        assert len(report.score_breakdown) == len(high_relevance_candidates)
        assert report.score_breakdown[0]["status"] == "Kept"
        assert report.score_breakdown[2]["status"] == "Filtered (Low Relevance)"
