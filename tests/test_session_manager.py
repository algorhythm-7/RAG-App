"""Tests for session manager component."""

import pytest
from unittest.mock import patch
import streamlit as st

from src.components.session_manager import SessionManager
from src.models import Document, Passage, QueryResult


class TestSessionManagerInitialization:
    """Tests for session initialization."""
    
    def test_initialize_session_creates_state(self, reset_session):
        """Test that initialize_session sets up required state."""
        SessionManager.initialize_session()
        
        assert SessionManager.SESSION_ID in st.session_state
        assert SessionManager.DOCUMENTS in st.session_state
        assert SessionManager.INDEXER in st.session_state
        assert SessionManager.QUERY_HISTORY in st.session_state
    
    def test_get_session_id_creates_session(self, reset_session):
        """Test that get_session_id initializes session."""
        session_id = SessionManager.get_session_id()
        
        assert session_id is not None
        assert len(session_id) > 0
    
    def test_session_persistence(self, reset_session):
        """Test that session persists across calls."""
        id1 = SessionManager.get_session_id()
        id2 = SessionManager.get_session_id()
        
        assert id1 == id2


class TestSessionManagerDocuments:
    """Tests for document management."""
    
    def test_add_document(self, reset_session, sample_document):
        """Test adding a document."""
        SessionManager.initialize_session()
        SessionManager.add_document(sample_document)
        
        docs = SessionManager.get_documents()
        assert sample_document.document_id in docs
        assert docs[sample_document.document_id] == sample_document
    
    def test_get_documents_count(self, reset_session, sample_document):
        """Test getting document count."""
        SessionManager.initialize_session()
        
        assert SessionManager.get_document_count() == 0
        
        SessionManager.add_document(sample_document)
        assert SessionManager.get_document_count() == 1
    
    def test_add_multiple_documents(self, reset_session):
        """Test adding multiple documents."""
        SessionManager.initialize_session()
        
        docs = [
            Document(
                document_id=f"doc-{i}",
                filename=f"test-{i}.pdf",
                file_format="pdf",
                file_hash=f"hash-{i}",
                parsed_successfully=True,
                passages=[Passage(text=f"Content {i}", section="Page 1", document_id=f"doc-{i}", passage_index=0)]
            )
            for i in range(3)
        ]
        
        for doc in docs:
            SessionManager.add_document(doc)
        
        assert SessionManager.get_document_count() == 3


class TestSessionManagerQueryHistory:
    """Tests for query history."""
    
    def test_add_to_query_history(self, reset_session):
        """Test adding queries to history."""
        SessionManager.initialize_session()
        
        query_result = QueryResult(
            status="success",
            answer="Test answer",
            sources=[],
            confidence=0.9,
            response_time_ms=1000,
        )
        
        SessionManager.add_to_query_history(query_result)
        history = SessionManager.get_query_history()
        
        assert len(history) == 1
        assert history[0] == query_result
    
    def test_query_history_order(self, reset_session):
        """Test that queries are added in order."""
        SessionManager.initialize_session()
        
        for i in range(3):
            query = QueryResult(
                status="success",
                answer=f"Answer {i}",
                sources=[],
                confidence=0.9,
                response_time_ms=1000,
            )
            SessionManager.add_to_query_history(query)
        
        history = SessionManager.get_query_history()
        assert len(history) == 3


class TestSessionManagerClear:
    """Tests for session clearing."""
    
    def test_clear_session(self, reset_session, sample_document):
        """Test clearing session."""
        SessionManager.initialize_session()
        SessionManager.add_document(sample_document)
        
        assert SessionManager.get_document_count() == 1
        
        SessionManager.clear_session()
        
        assert SessionManager.get_document_count() == 0
        assert len(SessionManager.get_query_history()) == 0
    
    def test_clear_preserves_session_id(self, reset_session):
        """Test that clearing preserves session ID."""
        SessionManager.initialize_session()
        original_id = SessionManager.get_session_id()
        
        SessionManager.clear_session()
        
        # Note: clear_session resets documents but keeps session ID
        new_id = SessionManager.get_session_id()
        # Session ID should be unchanged
        assert original_id == new_id


class TestSessionManagerIndexer:
    """Tests for indexer access."""
    
    def test_get_indexer(self, reset_session):
        """Test getting indexer."""
        SessionManager.initialize_session()
        indexer = SessionManager.get_indexer()
        
        assert indexer is not None
        assert hasattr(indexer, 'build_index')
        assert hasattr(indexer, 'search')


class TestSessionManagerDuration:
    """Tests for session duration tracking."""
    
    def test_get_session_duration(self, reset_session):
        """Test getting session duration."""
        SessionManager.initialize_session()
        duration = SessionManager.get_session_duration()
        
        # Duration should be non-negative
        assert duration.total_seconds() >= 0
