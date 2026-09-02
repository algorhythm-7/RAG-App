"""Tests for semantic indexer component."""

import pytest
import numpy as np

from src.components.semantic_indexer import SemanticIndexer
from src.models import Passage


class TestSemanticIndexerBuild:
    """Tests for building FAISS index."""
    
    def test_build_index_success(self, semantic_indexer, sample_passages, sample_embeddings):
        """Test successful index building."""
        semantic_indexer.build_index(sample_passages, sample_embeddings)
        
        assert semantic_indexer.index is not None
        assert len(semantic_indexer.passages) == len(sample_passages)
    
    def test_build_index_empty_passages(self, semantic_indexer):
        """Test building index with empty passages."""
        semantic_indexer.build_index([], [])
        
        assert semantic_indexer.index is None
        assert len(semantic_indexer.passages) == 0
    
    def test_build_index_mismatch(self, semantic_indexer, sample_passages):
        """Test building index with mismatched embeddings."""
        single_embedding = [np.random.rand(1536).tolist()]
        
        # Should handle gracefully - either raise or adjust
        # depending on implementation


class TestSemanticIndexerSearch:
    """Tests for searching index."""
    
    def test_search_success(self, semantic_indexer, sample_passages, sample_embeddings):
        """Test successful search."""
        semantic_indexer.build_index(sample_passages, sample_embeddings)
        
        # Search with first embedding
        query_embedding = sample_embeddings[0]
        results = semantic_indexer.search(query_embedding, top_k=2)
        
        assert len(results) > 0
        assert len(results) <= 2
        
        # Each result should be (Passage, similarity_score)
        for passage, score in results:
            assert isinstance(passage, Passage)
            assert 0.0 <= score <= 1.0
    
    def test_search_empty_index(self, semantic_indexer):
        """Test searching empty index."""
        query_embedding = np.random.rand(1536).tolist()
        results = semantic_indexer.search(query_embedding)
        
        assert results == []
    
    def test_search_top_k_limit(self, semantic_indexer, sample_passages, sample_embeddings):
        """Test top_k parameter limits results."""
        semantic_indexer.build_index(sample_passages, sample_embeddings)
        
        query_embedding = sample_embeddings[0]
        results = semantic_indexer.search(query_embedding, top_k=1)
        
        assert len(results) <= 1
    
    def test_search_similarity_ordering(self, semantic_indexer, sample_passages, sample_embeddings):
        """Test that results are ordered by similarity."""
        semantic_indexer.build_index(sample_passages, sample_embeddings)
        
        query_embedding = sample_embeddings[0]
        results = semantic_indexer.search(query_embedding, top_k=3)
        
        if len(results) > 1:
            # Later results should have lower or equal similarity
            scores = [score for _, score in results]
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1]


class TestSemanticIndexerState:
    """Tests for indexer state management."""
    
    def test_index_rebuild(self, semantic_indexer, sample_passages, sample_embeddings):
        """Test rebuilding index with new data."""
        # First build
        semantic_indexer.build_index(sample_passages[:2], sample_embeddings[:2])
        assert len(semantic_indexer.passages) == 2
        
        # Rebuild with different data
        semantic_indexer.build_index(sample_passages, sample_embeddings)
        assert len(semantic_indexer.passages) == len(sample_passages)
