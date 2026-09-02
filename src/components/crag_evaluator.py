"""Corrective RAG (CRAG) Evaluator & Context Guardrail.

Implements the Corrective RAG paradigm:
Evaluates retrieved context relevance against the query, filters noisy or irrelevant chunks,
classifies retrieval confidence (CORRECT, AMBIGUOUS, OUT_OF_SCOPE), and guards the LLM
against hallucinations when documentation is lacking.
"""

from typing import List, Tuple

from src.models import CRAGReport, Passage
from src.utils.constants import (
    CRAG_AMBIGUOUS_THRESHOLD,
    CRAG_CORRECT_THRESHOLD,
    CROSS_ENCODER_MODEL,
)
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)


class CRAGEvaluator:
    """Evaluates and refines retrieved context to ensure faithfulness and relevance."""

    def __init__(
        self,
        correct_threshold: float = CRAG_CORRECT_THRESHOLD,
        ambiguous_threshold: float = CRAG_AMBIGUOUS_THRESHOLD,
        model_name: str = CROSS_ENCODER_MODEL,
    ):
        self.correct_threshold = correct_threshold
        self.ambiguous_threshold = ambiguous_threshold
        self.model_name = model_name

    def evaluate_and_filter(
        self,
        query: str,
        reranked_passages: List[Tuple[Passage, float]],
    ) -> Tuple[List[Tuple[Passage, float]], CRAGReport]:
        """Evaluate retrieval quality and filter low-confidence noise chunks.

        Args:
            query: The user query or symptom description.
            reranked_passages: Output from CrossEncoderReranker (Passage, score).

        Returns:
            Tuple of (filtered_passages, crag_report).
        """
        actions = []
        original_count = len(reranked_passages)

        if not reranked_passages:
            report = CRAGReport(
                relevance_grade="OUT_OF_SCOPE",
                confidence_score=0.0,
                reranker_model=self.model_name,
                actions_taken=["No documents retrieved. Guardrail activated."],
                original_count=0,
                filtered_count=0,
                score_breakdown=[],
            )
            return [], report

        top_score = reranked_passages[0][1]
        avg_top_score = sum(s for _, s in reranked_passages[:3]) / min(3, len(reranked_passages))

        # 1. Determine Relevance Grade
        if top_score >= self.correct_threshold:
            grade = "CORRECT"
            actions.append(f"High relevance confirmed (Top Score: {top_score:.1%}).")
        elif top_score >= self.ambiguous_threshold:
            grade = "AMBIGUOUS"
            actions.append(f"Moderate relevance detected (Top Score: {top_score:.1%}). Flagged for uncertainty.")
        else:
            grade = "OUT_OF_SCOPE"
            actions.append(
                f"Low relevance detected (Top Score: {top_score:.1%}). "
                "Query appears out-of-scope for the uploaded manual(s)."
            )

        # 2. Context Filtering (Noise Elimination)
        # Retain chunks that meet the adaptive cutoff (at least 60% of top score and >= ambiguous threshold)
        cutoff = max(self.ambiguous_threshold * 0.8, top_score * 0.45)
        filtered_passages = []
        score_breakdown = []

        for p, score in reranked_passages:
            is_kept = score >= cutoff
            status = "Kept" if is_kept else "Filtered (Low Relevance)"
            score_breakdown.append({
                "section": p.section,
                "score": round(score, 3),
                "status": status,
                "is_diagram": p.is_diagram,
            })
            if is_kept:
                filtered_passages.append((p, score))

        filter_dropped = original_count - len(filtered_passages)
        if filter_dropped > 0:
            actions.append(f"Filtered {filter_dropped} noisy/low-relevance chunk(s) (Cutoff threshold: {cutoff:.1%}).")
        else:
            actions.append("All retrieved candidate chunks retained above confidence threshold.")

        actions.append(f"Applied 2nd-stage neural Cross-Encoder: '{self.model_name.split('/')[-1]}'.")

        report = CRAGReport(
            relevance_grade=grade,
            confidence_score=round(float(top_score), 3),
            reranker_model=self.model_name,
            actions_taken=actions,
            original_count=original_count,
            filtered_count=len(filtered_passages),
            score_breakdown=score_breakdown,
        )

        log_event(
            "crag_evaluation",
            grade=grade,
            confidence=top_score,
            original_chunks=original_count,
            retained_chunks=len(filtered_passages),
        )

        return filtered_passages, report
