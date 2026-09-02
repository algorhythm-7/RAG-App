"""Tests for answer generator component."""

import pytest
from unittest.mock import Mock, patch
import time

from src.components.answer_generator import AnswerGenerator
from src.models import Passage, QueryResult


class TestAnswerGeneratorSuccess:
    """Tests for successful answer generation."""
    
    def test_generate_answer_success(self, answer_generator_mock, sample_passages):
        """Test successful answer generation."""
        result = answer_generator_mock.generate_answer(
            "What is tire pressure?",
            sample_passages
        )
        
        assert result.status == "success"
        assert len(result.answer) > 0
        assert len(result.sources) > 0
        assert result.confidence > 0
        assert result.response_time_ms > 0
    
    def test_generate_answer_no_passages(self, answer_generator_mock):
        """Test answer generation with no passages."""
        result = answer_generator_mock.generate_answer(
            "What is tire pressure?",
            []
        )
        
        assert result.status == "no_results"
        assert "No information" in result.answer or "not found" in result.answer
        assert len(result.sources) == 0
    
    def test_generate_answer_single_passage(self, answer_generator_mock):
        """Test with single passage."""
        passages = [
            Passage(
                text="The tire pressure should be 32 PSI.",
                section="Page 1",
                document_id="doc-1",
                passage_index=0,
            )
        ]
        
        result = answer_generator_mock.generate_answer(
            "tire pressure",
            passages
        )
        
        assert result.status == "success"
        assert len(result.sources) == 1


class TestAnswerGeneratorPrompt:
    """Tests for prompt building."""
    
    def test_build_prompt_includes_query(self, answer_generator_mock, sample_passages):
        """Test that prompt includes user query."""
        prompt = answer_generator_mock._build_prompt(
            "What is recommended tire pressure?",
            sample_passages
        )
        
        assert "What is recommended tire pressure?" in prompt
        assert "QUESTION:" in prompt
    
    def test_build_prompt_includes_passages(self, answer_generator_mock, sample_passages):
        """Test that prompt includes passage content."""
        prompt = answer_generator_mock._build_prompt(
            "tire pressure",
            sample_passages
        )
        
        # Check some passage content is included
        assert any(p.text[:50] in prompt for p in sample_passages)
    
    def test_build_prompt_includes_section_refs(self, answer_generator_mock, sample_passages):
        """Test that prompt includes section references."""
        prompt = answer_generator_mock._build_prompt(
            "test",
            sample_passages
        )
        
        # Check section headers are included
        assert any(p.section in prompt for p in sample_passages)


class TestAnswerGeneratorSources:
    """Tests for source attribution building."""
    
    def test_build_sources_unique_docs(self, answer_generator_mock, sample_passages):
        """Test that sources are deduplicated by document."""
        sources = answer_generator_mock._build_sources(sample_passages)
        
        # Should have at least one source
        assert len(sources) > 0
        
        # Each source should have required fields
        for source in sources:
            assert "document_id" in source
            assert "section" in source
            assert "passage" in source
    
    def test_build_sources_truncates_long_passages(self, answer_generator_mock):
        """Test that long passages are truncated in sources."""
        long_text = "x" * 1000
        passages = [
            Passage(
                text=long_text,
                section="Long Section",
                document_id="doc-1",
                passage_index=0,
            )
        ]
        
        sources = answer_generator_mock._build_sources(passages)
        
        assert len(sources[0]["passage"]) < len(long_text)
        assert "..." in sources[0]["passage"]


class TestAnswerGeneratorErrorHandling:
    """Tests for error handling."""
    
    def test_generate_answer_api_error(self, answer_generator_mock):
        """Test handling of API errors."""
        passages = [
            Passage(text="Test", section="Page 1", document_id="doc-1", passage_index=0)
        ]
        
        # Mock API to raise error
        with patch('openai.ChatCompletion.create', side_effect=Exception("API Error")):
            result = answer_generator_mock.generate_answer("test", passages)
            
            assert result.status == "error"
    
    def test_generate_answer_timeout(self, answer_generator_mock):
        """Test handling of timeout."""
        passages = [
            Passage(text="Test", section="Page 1", document_id="doc-1", passage_index=0)
        ]
        
        # Mock API to timeout
        with patch('openai.ChatCompletion.create', side_effect=TimeoutError("Timeout")):
            result = answer_generator_mock.generate_answer("test", passages, timeout_seconds=1)
            
            # Should handle timeout gracefully


class TestAnswerGeneratorPerformance:
    """Tests for performance requirements."""
    
    def test_answer_generation_response_time(self, answer_generator_mock, sample_passages):
        """Test that answer generation completes in reasonable time."""
        start = time.time()
        result = answer_generator_mock.generate_answer(
            "test query",
            sample_passages
        )
        elapsed = time.time() - start
        
        # Response time should be logged
        assert result.response_time_ms > 0
        # Should complete reasonably fast (< 30s as per requirement)
        assert elapsed < 30
