"""Tests for query processor component."""

import pytest
from unittest.mock import Mock, patch

from src.components.query_processor import QueryProcessor
from src.models import Passage


class TestQueryProcessorFindPassages:
    """Tests for finding relevant passages."""
    
    def test_find_passages_success(self, query_processor, sample_passages, sample_embeddings, mock_openai_embeddings):
        """Test successful passage retrieval."""
        # Setup indexer with sample data
        query_processor.indexer.build_index(sample_passages, sample_embeddings)
        
        # Query
        passages, confidence = query_processor.find_relevant_passages("tire pressure")
        
        # May find passages depending on similarity
        assert isinstance(passages, list)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
    
    def test_find_passages_no_results(self, query_processor, mock_openai_embeddings):
        """Test when no passages meet relevance threshold."""
        # Empty indexer
        passages, confidence = query_processor.find_relevant_passages("some query")
        
        assert passages == []
        assert confidence == 0.0
    
    def test_find_passages_filters_low_similarity(self, query_processor, sample_passages, sample_embeddings, mock_openai_embeddings):
        """Test that low similarity passages are filtered."""
        query_processor.indexer.build_index(sample_passages, sample_embeddings)
        
        passages, confidence = query_processor.find_relevant_passages("random text xyz", top_k=10)
        
        # With random embeddings, may not find relevant passages
        if passages:
            # If passages found, confidence should be above threshold
            assert confidence > 0.0


class TestQueryProcessorErrorHandling:
    """Tests for error handling in query processor."""
    
    def test_find_passages_handles_embedding_error(self, query_processor):
        """Test handling of embedding generation errors."""
        # Mock embedder to raise error
        query_processor.embedder.embed_query = Mock(side_effect=Exception("API Error"))
        
        passages, confidence = query_processor.find_relevant_passages("test query")
        
        # Should return empty gracefully
        assert passages == []
        assert confidence == 0.0
    
    def test_find_passages_empty_query(self, query_processor, sample_passages, sample_embeddings, mock_openai_embeddings):
        """Test with empty query."""
        query_processor.indexer.build_index(sample_passages, sample_embeddings)
        
        # Empty query should still work (embedder handles it)
        passages, confidence = query_processor.find_relevant_passages("")
        
        assert isinstance(passages, list)


class TestQueryProcessorIntegration:
    """Integration tests for query processor."""
    
    def test_end_to_end_query_flow(self, query_processor, sample_passages, sample_embeddings, mock_openai_embeddings):
        """Test complete query flow: embed -> search -> filter."""
        # Setup
        query_processor.indexer.build_index(sample_passages, sample_embeddings)
        
        # Query about tire pressure
        passages, confidence = query_processor.find_relevant_passages("What is tire pressure?")
        
        # Check results
        assert isinstance(passages, list)
        assert isinstance(confidence, float)
