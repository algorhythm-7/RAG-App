"""Session state management."""

import uuid
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.models import Document, DiagnosisResult, LocationResult, TriageResult
from src.components.semantic_indexer import SemanticIndexer
from src.components.embedding_generator import EmbeddingGenerator
from src.components.answer_generator import AnswerGenerator
from src.components.query_processor import QueryProcessor
from src.components.document_parser import DocumentParser
from src.components.chunker import Chunker
from src.components.bm25_index import BM25Index
from src.components.vector_store import VectorStore
from src.components.hybrid_retriever import HybridRetriever
from src.components.triage_llm import TriageLLM
from src.components.reasoning_llm import ReasoningLLM
from src.components.location_llm import LocationLLM
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)


class SessionManager:
    """Manage session state and lifecycle."""
    
    # Session state keys
    SESSION_ID = "session_id"
    DOCUMENTS = "documents"  # Dict[document_id -> Document]
    INDEXER = "indexer"  # SemanticIndexer
    QUERY_HISTORY = "query_history"  # List of QueryResult
    CREATED_AT = "created_at"
    LAST_ACTIVITY = "last_activity"
    CHUNKS = "chunks"  # List[Passage] - header-aware chunks across all documents
    BM25_INDEX = "bm25_index"  # BM25Index
    VECTOR_STORE = "vector_store"  # VectorStore (ChromaDB)
    DIAGNOSIS_HISTORY = "diagnosis_history"  # List of DiagnosisResult
    LAST_TRIAGE = "last_triage"  # TriageResult of the most recent diagnosis run
    LAST_DIAGNOSIS = "last_diagnosis"  # DiagnosisResult of the most recent diagnosis run
    LAST_LOCATION_RESULT = "last_location_result"  # LocationResult (Stage 3: nearest station)
    
    @staticmethod
    def initialize_session():
        """Initialize session state if not already done."""
        if SessionManager.SESSION_ID not in st.session_state:
            session_id = str(uuid.uuid4())
            st.session_state[SessionManager.SESSION_ID] = session_id
            st.session_state[SessionManager.DOCUMENTS] = {}
            st.session_state[SessionManager.INDEXER] = SemanticIndexer()
            st.session_state[SessionManager.QUERY_HISTORY] = []
            st.session_state[SessionManager.CREATED_AT] = datetime.now()
            st.session_state[SessionManager.LAST_ACTIVITY] = datetime.now()
            st.session_state[SessionManager.CHUNKS] = []
            st.session_state[SessionManager.BM25_INDEX] = BM25Index()
            st.session_state[SessionManager.VECTOR_STORE] = VectorStore(collection_name=session_id)
            st.session_state[SessionManager.DIAGNOSIS_HISTORY] = []
            st.session_state[SessionManager.LAST_TRIAGE] = None
            st.session_state[SessionManager.LAST_DIAGNOSIS] = None
            st.session_state[SessionManager.LAST_LOCATION_RESULT] = None
            
            log_event("session_created", session_id=session_id)
    
    @staticmethod
    def get_session_id() -> str:
        """Get the current session ID."""
        SessionManager.initialize_session()
        return st.session_state[SessionManager.SESSION_ID]
    
    @staticmethod
    def get_documents() -> Dict[str, Document]:
        """Get all documents in the session."""
        SessionManager.initialize_session()
        return st.session_state[SessionManager.DOCUMENTS]
    
    @staticmethod
    def get_indexer() -> SemanticIndexer:
        """Get the FAISS indexer."""
        SessionManager.initialize_session()
        return st.session_state[SessionManager.INDEXER]
    
    @staticmethod
    def add_document(document: Document) -> None:
        """Add a document to the session and re-index it for hybrid retrieval
        (header-aware chunking + BM25 + ChromaDB).
        
        Args:
            document: Document to add.
        """
        SessionManager.initialize_session()
        st.session_state[SessionManager.DOCUMENTS][document.document_id] = document
        st.session_state[SessionManager.LAST_ACTIVITY] = datetime.now()
        
        log_event(
            "document_added",
            document_id=document.document_id,
            filename=document.filename,
        )
        
        if document.parsed_successfully:
            SessionManager._reindex_hybrid_pipeline()
    
    @staticmethod
    def _reindex_hybrid_pipeline() -> None:
        """Rebuild the header-aware chunks, BM25 index, and Chroma vector store
        from all documents currently in the session."""
        chunker = Chunker()
        embedder = EmbeddingGenerator()
        
        all_chunks = []
        for document in st.session_state[SessionManager.DOCUMENTS].values():
            if not document.parsed_successfully:
                continue
            chunks = chunker.chunk_passages(document.passages)
            for chunk in chunks:
                chunk.document_id = document.document_id
            all_chunks.extend(chunks)
        
        st.session_state[SessionManager.CHUNKS] = all_chunks
        
        bm25_index = BM25Index()
        bm25_index.build(all_chunks)
        st.session_state[SessionManager.BM25_INDEX] = bm25_index
        
        vector_store = VectorStore(collection_name=st.session_state[SessionManager.SESSION_ID])
        if all_chunks:
            embeddings = embedder.embed_passages(all_chunks)
            vector_store.build(all_chunks, embeddings)
        st.session_state[SessionManager.VECTOR_STORE] = vector_store
        
        log_event("hybrid_reindex", chunk_count=len(all_chunks))
    
    @staticmethod
    def run_diagnosis(symptom_text: str) -> Dict:
        """Run the full two-stage diagnostic pipeline for a symptom description:
        Stage 1 triage (symptom -> systems + search queries), hybrid retrieval
        (BM25 + vector, fused via RRF), then Stage 2 reasoning (differential diagnosis).
        
        Args:
            symptom_text: The driver's symptom description.
        
        Returns:
            Dict with keys "triage" (TriageResult) and "diagnosis" (DiagnosisResult).
        """
        SessionManager.initialize_session()
        
        triage_result = TriageLLM().triage(symptom_text)
        
        bm25_index = st.session_state[SessionManager.BM25_INDEX]
        vector_store = st.session_state[SessionManager.VECTOR_STORE]
        embedder = EmbeddingGenerator()
        retriever = HybridRetriever(bm25_index, vector_store, embedder)
        retrieved = retriever.retrieve(triage_result.search_queries)
        
        diagnosis_result = ReasoningLLM().diagnose(symptom_text, retrieved)
        
        st.session_state[SessionManager.DIAGNOSIS_HISTORY].append(diagnosis_result)
        st.session_state[SessionManager.LAST_TRIAGE] = triage_result
        st.session_state[SessionManager.LAST_DIAGNOSIS] = diagnosis_result
        st.session_state[SessionManager.LAST_LOCATION_RESULT] = None
        st.session_state[SessionManager.LAST_ACTIVITY] = datetime.now()
        
        return {"triage": triage_result, "diagnosis": diagnosis_result}
    
    @staticmethod
    def get_diagnosis_history() -> List[DiagnosisResult]:
        """Get diagnosis history."""
        SessionManager.initialize_session()
        return st.session_state[SessionManager.DIAGNOSIS_HISTORY]
    
    @staticmethod
    def get_last_diagnosis() -> Optional[DiagnosisResult]:
        """Get the DiagnosisResult from the most recent diagnosis run, if any."""
        SessionManager.initialize_session()
        return st.session_state.get(SessionManager.LAST_DIAGNOSIS)
    
    @staticmethod
    def get_last_triage() -> Optional[TriageResult]:
        """Get the TriageResult from the most recent diagnosis run, if any."""
        SessionManager.initialize_session()
        return st.session_state.get(SessionManager.LAST_TRIAGE)
    
    @staticmethod
    def find_service_stations(address_text: str) -> LocationResult:
        """Stage 3: find nearby service stations relevant to the most recent diagnosis,
        via the Location LLM + Mapbox MCP.
        
        Args:
            address_text: The user-entered address/city/ZIP to search near.
        
        Raises:
            ValueError: If no diagnosis has been run yet this session.
        """
        SessionManager.initialize_session()
        diagnosis = st.session_state.get(SessionManager.LAST_DIAGNOSIS)
        if diagnosis is None:
            raise ValueError("Run a diagnosis first.")
        
        location_result = LocationLLM().find_service_stations(diagnosis, address_text)
        st.session_state[SessionManager.LAST_LOCATION_RESULT] = location_result
        st.session_state[SessionManager.LAST_ACTIVITY] = datetime.now()
        return location_result
    
    @staticmethod
    def get_last_location_result() -> Optional[LocationResult]:
        """Get the most recent Stage 3 station-search result, if any."""
        SessionManager.initialize_session()
        return st.session_state.get(SessionManager.LAST_LOCATION_RESULT)
    
    @staticmethod
    def get_query_history() -> List:
        """Get query history."""
        SessionManager.initialize_session()
        return st.session_state[SessionManager.QUERY_HISTORY]
    
    @staticmethod
    def add_to_query_history(query_result) -> None:
        """Add a query result to history.
        
        Args:
            query_result: QueryResult to add.
        """
        SessionManager.initialize_session()
        st.session_state[SessionManager.QUERY_HISTORY].append(query_result)
        st.session_state[SessionManager.LAST_ACTIVITY] = datetime.now()
    
    @staticmethod
    def clear_session() -> None:
        """Clear all session data."""
        session_id = st.session_state.get(SessionManager.SESSION_ID, "unknown")
        
        st.session_state[SessionManager.DOCUMENTS] = {}
        st.session_state[SessionManager.INDEXER] = SemanticIndexer()
        st.session_state[SessionManager.QUERY_HISTORY] = []
        st.session_state[SessionManager.CHUNKS] = []
        st.session_state[SessionManager.BM25_INDEX] = BM25Index()
        st.session_state[SessionManager.VECTOR_STORE] = VectorStore(collection_name=session_id)
        st.session_state[SessionManager.DIAGNOSIS_HISTORY] = []
        st.session_state[SessionManager.LAST_TRIAGE] = None
        st.session_state[SessionManager.LAST_DIAGNOSIS] = None
        st.session_state[SessionManager.LAST_LOCATION_RESULT] = None
        
        log_event("session_cleared", session_id=session_id)
    
    @staticmethod
    def get_document_count() -> int:
        """Get number of documents in session."""
        return len(SessionManager.get_documents())
    
    @staticmethod
    def get_session_duration() -> timedelta:
        """Get how long session has been active."""
        created_at = st.session_state.get(SessionManager.CREATED_AT, datetime.now())
        return datetime.now() - created_at

