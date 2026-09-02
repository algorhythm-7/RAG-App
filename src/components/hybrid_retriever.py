"""Hybrid retrieval combining BM25 lexical search, vector semantic search (via RRF),
2-stage Cross-Encoder neural reranking, and Corrective RAG (CRAG) evaluation.
"""

from typing import Dict, List, Optional, Tuple

from src.components.bm25_index import BM25Index
from src.components.crag_evaluator import CRAGEvaluator
from src.components.cross_encoder_reranker import CrossEncoderReranker
from src.components.embedding_generator import EmbeddingGenerator
from src.components.vector_store import VectorStore
from src.models import CRAGReport, Passage
from src.utils.constants import HYBRID_TOP_K, RERANKER_TOP_K, RETRIEVAL_TOP_K, RRF_K
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)


class HybridRetriever:
    """Fuses BM25 and vector search results across search queries via RRF,
    then applies 2nd-stage neural Cross-Encoder reranking and CRAG evaluation."""

    def __init__(
        self,
        bm25_index: BM25Index,
        vector_store: VectorStore,
        embedder: EmbeddingGenerator,
        reranker: Optional[CrossEncoderReranker] = None,
        crag_evaluator: Optional[CRAGEvaluator] = None,
    ):
        self.bm25_index = bm25_index
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = reranker or CrossEncoderReranker()
        self.crag_evaluator = crag_evaluator or CRAGEvaluator()

    def retrieve(
        self,
        search_queries: List[str],
        top_k: int = HYBRID_TOP_K,
        primary_query: Optional[str] = None,
    ) -> List[Tuple[Passage, float]]:
        """Run BM25 + vector search, fuse with RRF, then rerank with Cross-Encoder.

        Args:
            search_queries: Targeted search queries.
            top_k: Number of fused/reranked passages to return.
            primary_query: Original user query or symptom text for Cross-Encoder conditioning.

        Returns:
            List of (Passage, score) tuples, sorted by descending relevance.
        """
        fused_passages = self._fuse_rrf(search_queries, top_k=top_k)
        if not fused_passages:
            return []

        # 2nd-Stage Neural Cross-Encoder Reranking
        ranking_query = primary_query or (search_queries[0] if search_queries else "")
        reranked = self.reranker.rerank(ranking_query, fused_passages, top_k=top_k)
        return reranked

    def retrieve_with_crag(
        self,
        primary_query: str,
        search_queries: List[str],
        top_k: int = RERANKER_TOP_K,
    ) -> Tuple[List[Tuple[Passage, float]], CRAGReport]:
        """Complete 2-stage Hybrid + Cross-Encoder + CRAG evaluation pipeline.

        Args:
            primary_query: The main user query / symptom text.
            search_queries: List of targeted retrieval queries.
            top_k: Max number of final passages to retain for LLM generation.

        Returns:
            Tuple of (filtered_passages, crag_report).
        """
        # 1st Stage: Hybrid retrieval (BM25 + Dense Vector) fused with RRF
        fused_candidates = self._fuse_rrf(search_queries, top_k=HYBRID_TOP_K)

        if not fused_candidates:
            _, report = self.crag_evaluator.evaluate_and_filter(primary_query, [])
            return [], report

        # 2nd Stage: Neural Cross-Encoder Reranking
        reranked = self.reranker.rerank(primary_query, fused_candidates, top_k=top_k)

        # 3rd Stage: Corrective RAG (CRAG) Evaluation & Filtering
        filtered_passages, crag_report = self.crag_evaluator.evaluate_and_filter(primary_query, reranked)

        log_event(
            "retrieve_with_crag",
            grade=crag_report.relevance_grade,
            confidence=crag_report.confidence_score,
            passages_retained=len(filtered_passages),
        )

        return filtered_passages, crag_report

    def _fuse_rrf(self, search_queries: List[str], top_k: int = HYBRID_TOP_K) -> List[Tuple[Passage, float]]:
        """Accumulate Reciprocal Rank Fusion scores across all search queries."""
        fused_scores: Dict[tuple, float] = {}
        passage_by_key: Dict[tuple, Passage] = {}

        for query in search_queries:
            bm25_results = self.bm25_index.search(query, top_k=RETRIEVAL_TOP_K)
            self._accumulate_rrf(bm25_results, fused_scores, passage_by_key)

            try:
                query_embedding = self.embedder.embed_query(query)
                vector_results = self.vector_store.search(query_embedding, top_k=RETRIEVAL_TOP_K)
                self._accumulate_rrf(vector_results, fused_scores, passage_by_key)
            except Exception as e:
                logger.warning(f"Vector search failed for query '{query}': {e}")

        ranked_keys = sorted(fused_scores, key=lambda k: fused_scores[k], reverse=True)[:top_k]
        results = [(passage_by_key[key], fused_scores[key]) for key in ranked_keys]

        log_event("hybrid_retrieve_fused", queries=len(search_queries), fused_results=len(results))
        return results

    def _accumulate_rrf(
        self,
        ranked_results: List[Tuple[Passage, float]],
        fused_scores: Dict[tuple, float],
        passage_by_key: Dict[tuple, Passage],
    ) -> None:
        """Add RRF contributions (1 / (RRF_K + rank)) from one ranked result list."""
        for rank, (passage, _score) in enumerate(ranked_results, start=1):
            key = (passage.document_id, passage.section, passage.passage_index)
            fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
            passage_by_key[key] = passage
