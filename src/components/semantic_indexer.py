"""Semantic search using FAISS vector index."""

from typing import List, Tuple
import numpy as np
import faiss

from src.models import Passage
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)


class SemanticIndexer:
    """Build and query FAISS index for semantic search."""
    
    def __init__(self):
        """Initialize the indexer."""
        self.index = None
        self.passages = []
    
    def build_index(self, passages: List[Passage], embeddings: List[List[float]]) -> None:
        """Build FAISS index from passages and embeddings.
        
        Args:
            passages: List of passages.
            embeddings: List of embedding vectors.
        """
        if not passages or not embeddings:
            logger.warning("Cannot build index with empty passages or embeddings")
            self.index = None
            self.passages = []
            return
        
        try:
            # Convert embeddings to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Create FAISS index
            dimension = embeddings_array.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(embeddings_array)
            
            # Store passages for later retrieval
            self.passages = passages
            
            log_event(
                "build_index",
                passage_count=len(passages),
                embedding_dimension=dimension,
            )
        except Exception as e:
            logger.exception(f"Failed to build FAISS index: {e}")
            self.index = None
            self.passages = []
            raise
    
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[Passage, float]]:
        """Search for most similar passages.
        
        Args:
            query_embedding: Query embedding vector.
            top_k: Number of top results to return.
        
        Returns:
            List of (Passage, similarity_score) tuples, sorted by relevance.
        """
        if self.index is None or not self.passages:
            logger.warning("Index is empty, cannot search")
            return []
        
        try:
            # Convert query to numpy array
            query_array = np.array([query_embedding], dtype=np.float32)
            
            # Search
            distances, indices = self.index.search(query_array, min(top_k, len(self.passages)))
            
            # Convert distances to similarity scores (L2 distance -> cosine-like similarity)
            # Smaller distance = more similar
            # Normalize: similarity = 1 / (1 + distance)
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.passages):
                    passage = self.passages[idx]
                    # Convert L2 distance to similarity score (0-1)
                    similarity = 1.0 / (1.0 + distance)
                    results.append((passage, similarity))
            
            return results
        except Exception as e:
            logger.exception(f"Search failed: {e}")
            return []
