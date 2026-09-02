"""Hybrid retrieval combining BM25 lexical search and vector semantic search via
Reciprocal Rank Fusion (RRF)."""

from typing import Dict, List, Tuple

from src.components.bm25_index import BM25Index
from src.components.embedding_generator import EmbeddingGenerator
from src.components.vector_store import VectorStore
from src.models import Passage
from src.utils.constants import HYBRID_TOP_K, RETRIEVAL_TOP_K, RRF_K
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)


class HybridRetriever:
    """Fuse BM25 and vector search results across one or more search queries via RRF."""

    def __init__(self, bm25_index: BM25Index, vector_store: VectorStore, embedder: EmbeddingGenerator):
        self.bm25_index = bm25_index
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, search_queries: List[str], top_k: int = HYBRID_TOP_K) -> List[Tuple[Passage, float]]:
        """Run each search query through BM25 + vector search, then fuse the ranked
        result lists with Reciprocal Rank Fusion.

        Args:
            search_queries: Targeted search queries (typically produced by the triage stage).
            top_k: Number of fused passages to return.

        Returns:
            List of (Passage, fused_score) tuples, sorted by descending fused score.
        """
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

        log_event("hybrid_retrieve", queries=len(search_queries), fused_results=len(results))
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
