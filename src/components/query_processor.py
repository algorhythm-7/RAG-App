"""Query processing and passage retrieval."""

from typing import List, Tuple
from src.models import Passage, QueryResult, SourceAttribution
from src.components.embedding_generator import EmbeddingGenerator
from src.components.semantic_indexer import SemanticIndexer
from src.utils.logger import setup_logger, log_event
from src.utils.constants import FAISS_TOP_K, RELEVANCE_THRESHOLD

logger = setup_logger(__name__)


class QueryProcessor:
    """Process user queries and retrieve relevant passages."""
    
    def __init__(self, embedder: EmbeddingGenerator, indexer: SemanticIndexer):
        """Initialize with dependencies.
        
        Args:
            embedder: EmbeddingGenerator instance.
            indexer: SemanticIndexer instance.
        """
        self.embedder = embedder
        self.indexer = indexer
    
    def find_relevant_passages(
        self,
        query_text: str,
        top_k: int = FAISS_TOP_K,
    ) -> Tuple[List[Passage], float]:
        """Find passages relevant to the query.
        
        Args:
            query_text: The user's query.
            top_k: Number of results to return.
        
        Returns:
            Tuple of (relevant_passages, avg_confidence)
        """
        try:
            # Embed the query
            query_embedding = self.embedder.embed_query(query_text)
            
            # Search FAISS index
            results = self.indexer.search(query_embedding, top_k)
            
            logger.info(f"FAISS search returned {len(results)} results")
            logger.info(f"Top scores: {[score for _, score in results[:3]]}")
            
            # Filter by relevance threshold
            relevant = [
                (passage, score)
                for passage, score in results
                if score >= RELEVANCE_THRESHOLD
            ]
            
            logger.info(f"After filtering by threshold {RELEVANCE_THRESHOLD}: {len(relevant)} results")
            
            if not relevant:
                log_event(
                    "find_passages",
                    query=query_text[:50],
                    status="no_results",
                    threshold=RELEVANCE_THRESHOLD,
                )
                return [], 0.0
            
            passages = [p for p, _ in relevant]
            confidence = sum(s for _, s in relevant) / len(relevant)
            
            log_event(
                "find_passages",
                query=query_text[:50],
                passage_count=len(passages),
                avg_confidence=f"{confidence:.2f}",
            )
            
            return passages, confidence
        
        except Exception as e:
            logger.exception(f"Failed to find relevant passages: {e}")
            return [], 0.0
