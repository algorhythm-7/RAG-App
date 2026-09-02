"""Pytest configuration and fixtures for the application."""

import pytest
import io
from unittest.mock import Mock, MagicMock, patch
from PIL import Image
import numpy as np

from src.models import Passage, Document, QueryResult
from src.components.document_parser import DocumentParser
from src.components.embedding_generator import EmbeddingGenerator
from src.components.semantic_indexer import SemanticIndexer
from src.components.query_processor import QueryProcessor
from src.components.answer_generator import AnswerGenerator
from src.components.session_manager import SessionManager


# ============================================================================
# File Fixtures
# ============================================================================

@pytest.fixture
def sample_pdf_bytes():
    """Create mock PDF bytes for testing."""
    # Simple PDF header
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< >>
stream
BT
/F1 12 Tf
100 700 Td
(Sample PDF content for testing) Tj
ET
endstream
endobj
xref
0 5
trailer
<< /Size 5 /Root 1 0 R >>
startxref
234
%%EOF"""
    return pdf_content


@pytest.fixture
def sample_image_bytes():
    """Create a simple test image."""
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


@pytest.fixture
def sample_excel_bytes():
    """Create mock Excel bytes for testing."""
    import pandas as pd
    df = pd.DataFrame({'Column1': ['Value1', 'Value2'], 'Column2': [1, 2]})
    excel_bytes = io.BytesIO()
    df.to_excel(excel_bytes, index=False)
    return excel_bytes.getvalue()


@pytest.fixture
def sample_passages():
    """Create sample passages for testing."""
    return [
        Passage(
            text="The tire pressure should be checked monthly for safety.",
            section="Page 1",
            document_id="doc-1",
            passage_index=0,
        ),
        Passage(
            text="Recommended tire pressure is 32 PSI for front and 30 PSI for rear.",
            section="Page 2",
            document_id="doc-1",
            passage_index=1,
        ),
        Passage(
            text="Oil changes should be done every 5000 miles or 6 months.",
            section="Page 3",
            document_id="doc-1",
            passage_index=2,
        ),
    ]


@pytest.fixture
def sample_embeddings():
    """Create sample embedding vectors."""
    return [
        np.random.rand(1536).tolist() for _ in range(3)
    ]


@pytest.fixture
def sample_document():
    """Create a sample document."""
    passages = [
        Passage(text="Test content 1", section="Page 1", document_id="doc-1", passage_index=0),
        Passage(text="Test content 2", section="Page 2", document_id="doc-1", passage_index=1),
    ]
    return Document(
        document_id="doc-1",
        filename="test.pdf",
        file_format="pdf",
        file_hash="abc123",
        parsed_successfully=True,
        passages=passages,
    )


# ============================================================================
# Component Fixtures
# ============================================================================

@pytest.fixture
def parser():
    """Create a DocumentParser instance."""
    return DocumentParser()


@pytest.fixture
def semantic_indexer():
    """Create a SemanticIndexer instance."""
    return SemanticIndexer()


@pytest.fixture
def query_result_success():
    """Create a successful QueryResult."""
    return QueryResult(
        status="success",
        answer="The tire pressure should be 32 PSI for front and 30 PSI for rear.",
        sources=[
            {
                "document_id": "doc-1",
                "document_name": "manual.pdf",
                "section": "Page 2",
                "passage": "Recommended tire pressure is 32 PSI..."
            }
        ],
        confidence=0.85,
        response_time_ms=1200,
    )


# ============================================================================
# Mock Fixtures for External APIs
# ============================================================================

@pytest.fixture
def mock_openai_embeddings(monkeypatch):
    """Mock OpenAI embedding API."""
    from unittest.mock import MagicMock
    
    def mock_create(model, input):
        # Return mock embeddings in new API format
        class MockEmbedding:
            def __init__(self, embedding):
                self.embedding = embedding
        
        class MockResponse:
            def __init__(self, embeddings):
                self.data = embeddings
        
        if isinstance(input, list):
            embeddings = [
                MockEmbedding(np.random.rand(1536).tolist())
                for _ in input
            ]
        else:
            embeddings = [MockEmbedding(np.random.rand(1536).tolist())]
        
        return MockResponse(embeddings)
    
    with patch('openai.OpenAI') as mock_client_class:
        mock_client = MagicMock()
        mock_client.embeddings.create = mock_create
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_openai_chat(monkeypatch):
    """Mock OpenAI ChatCompletion API."""
    from unittest.mock import MagicMock
    
    def mock_create(model, messages, **kwargs):
        class MockMessage:
            def __init__(self):
                self.content = "This is a mock LLM response to your query."
        
        class MockChoice:
            def __init__(self):
                self.message = MockMessage()
        
        class MockResponse:
            def __init__(self):
                self.choices = [MockChoice()]
        
        return MockResponse()
    
    with patch('openai.OpenAI') as mock_client_class:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_client_class.return_value = mock_client
        yield mock_client


# ============================================================================
# Integration Fixtures
# ============================================================================

@pytest.fixture
def embedder_with_mock(mock_openai_embeddings):
    """Create an EmbeddingGenerator with mocked model."""
    from unittest.mock import patch, MagicMock
    # Mock sentence-transformers.SentenceTransformer
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
    with patch('sentence_transformers.SentenceTransformer', return_value=mock_model):
        yield EmbeddingGenerator()


@pytest.fixture
def query_processor(semantic_indexer, embedder_with_mock):
    """Create a QueryProcessor with dependencies."""
    return QueryProcessor(embedder_with_mock, semantic_indexer)


@pytest.fixture
def answer_generator_mock(mock_openai_chat):
    """Create an AnswerGenerator with mocked API."""
    from unittest.mock import patch
    with patch('src.utils.constants.OPENROUTER_API_KEY', 'sk-or-v1-test-key'):
        yield AnswerGenerator()


# ============================================================================
# Session Fixtures
# ============================================================================

@pytest.fixture
def reset_session():
    """Clear Streamlit session state before test."""
    import streamlit as st
    # Reset session state
    st.session_state.clear()
    yield
    # Cleanup
    st.session_state.clear()
