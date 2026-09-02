"""Query processing, passage retrieval, and Corrective RAG (CRAG) evaluation."""

from typing import List, Optional, Tuple

from src.components.crag_evaluator import CRAGEvaluator
from src.components.cross_encoder_reranker import CrossEncoderReranker
from src.components.embedding_generator import EmbeddingGenerator
from src.components.semantic_indexer import SemanticIndexer
from src.models import CRAGReport, Passage
from src.utils.constants import FAISS_TOP_K, RELEVANCE_THRESHOLD, RERANKER_TOP_K
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)


class QueryProcessor:
    """Process user queries, retrieve relevant passages with 2-stage neural reranking,
    and evaluate context relevance via CRAG."""

    def __init__(
        self,
        embedder: EmbeddingGenerator,
        indexer: SemanticIndexer,
        reranker: Optional[CrossEncoderReranker] = None,
        crag_evaluator: Optional[CRAGEvaluator] = None,
    ):
        self.embedder = embedder
        self.indexer = indexer
        self.reranker = reranker or CrossEncoderReranker()
        self.crag_evaluator = crag_evaluator or CRAGEvaluator()

    def find_relevant_passages(
        self,
        query_text: str,
        top_k: int = FAISS_TOP_K,
    ) -> Tuple[List[Passage], float]:
        """Find passages relevant to the query with 2-stage Cross-Encoder reranking.

        Args:
            query_text: The user's query.
            top_k: Number of results to return.

        Returns:
            Tuple of (relevant_passages, avg_confidence)
        """
        passages, confidence, _ = self.find_relevant_passages_with_crag(query_text, top_k=top_k)
        return passages, confidence

    def find_relevant_passages_with_crag(
        self,
        query_text: str,
        top_k: int = RERANKER_TOP_K,
    ) -> Tuple[List[Passage], float, CRAGReport]:
        """Find passages, apply Cross-Encoder 2nd-stage reranking, and run CRAG evaluation.

        Args:
            query_text: The user's natural language query.
            top_k: Number of top reranked passages to return.

        Returns:
            Tuple of (filtered_passages, confidence_score, crag_report).
        """
        try:
            # 1st Stage: Vector Embedding Search
            query_embedding = self.embedder.embed_query(query_text)
            candidates = self.indexer.search(query_embedding, top_k=top_k * 2)

            if not candidates:
                _, report = self.crag_evaluator.evaluate_and_filter(query_text, [])
                return [], 0.0, report

            # 2nd Stage: Neural Cross-Encoder Reranking
            reranked = self.reranker.rerank(query_text, candidates, top_k=top_k)

            # 3rd Stage: Corrective RAG (CRAG) Evaluation & Noise Filtering
            filtered, crag_report = self.crag_evaluator.evaluate_and_filter(query_text, reranked)

            if not filtered:
                log_event("find_passages_crag", query=query_text[:50], status="out_of_scope")
                return [], 0.0, crag_report

            passages = [p for p, _ in filtered]
            confidence = crag_report.confidence_score

            log_event(
                "find_passages_crag",
                query=query_text[:50],
                passage_count=len(passages),
                grade=crag_report.relevance_grade,
                confidence=confidence,
            )

            return passages, confidence, crag_report

        except Exception as e:
            logger.exception(f"Failed to find relevant passages: {e}")
            _, report = self.crag_evaluator.evaluate_and_filter(query_text, [])
            return [], 0.0, report
