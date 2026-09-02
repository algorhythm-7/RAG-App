"""Unit tests for Cross-Encoder 2nd-stage neural reranker."""

import pytest
from src.components.cross_encoder_reranker import CrossEncoderReranker
from src.models import Passage


@pytest.fixture
def reranker():
    return CrossEncoderReranker()


@pytest.fixture
def candidate_passages():
    return [
        (
            Passage(
                text="The recommended cold tire inflation pressure for all four tires is 32 psi (220 kPa).",
                section="Page 45 - Maintenance and Specifications",
                document_id="doc-1",
                passage_index=0,
            ),
            0.50,
        ),
        (
            Passage(
                text="The engine oil capacity is 4.5 quarts (4.3 liters) with filter replacement.",
                section="Page 50 - Fluids and Capacities",
                document_id="doc-1",
                passage_index=1,
            ),
            0.45,
        ),
        (
            Passage(
                text="Diagnostic Trouble Code P0300 indicates Random/Multiple Cylinder Misfire Detected in ignition system.",
                section="Page 88 - Engine Diagnostics DTC",
                document_id="doc-1",
                passage_index=2,
            ),
            0.40,
        ),
    ]


class TestCrossEncoderReranker:
    """Tests for CrossEncoderReranker functionality."""

    def test_rerank_tire_pressure_query(self, reranker, candidate_passages):
        """Test that a tire pressure query correctly ranks tire passage #1 with high score."""
        query = "What is the recommended tire pressure?"
        results = reranker.rerank(query, candidate_passages, top_k=3)

        assert len(results) == 3
        # Top passage should be the tire pressure passage
        top_passage, top_score = results[0]
        assert "tire inflation pressure" in top_passage.text
        assert top_score > results[1][1]
        assert 0.0 <= top_score <= 1.0

    def test_rerank_dtc_boost(self, reranker, candidate_passages):
        """Test that an exact DTC code query boosts the misfire passage to top rank."""
        query = "Check engine light flashing with code P0300"
        results = reranker.rerank(query, candidate_passages, top_k=3)

        top_passage, top_score = results[0]
        assert "P0300" in top_passage.text
        assert top_score > 0.60

    def test_rerank_empty_input(self, reranker):
        """Test that empty candidate list returns empty list gracefully."""
        results = reranker.rerank("any query", [])
        assert results == []

    def test_rerank_top_k_limit(self, reranker, candidate_passages):
        """Test that top_k restricts the number of returned reranked results."""
        results = reranker.rerank("tire pressure", candidate_passages, top_k=1)
        assert len(results) == 1

    def test_rerank_scores_descending(self, reranker, candidate_passages):
        """Test that reranked output is strictly sorted descending by score."""
        results = reranker.rerank("engine oil filter", candidate_passages, top_k=3)
        scores = [s for _, s in results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]
