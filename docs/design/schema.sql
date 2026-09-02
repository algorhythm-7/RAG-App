-- Database Schema for Document Query Application
-- Note: Version 1.0 uses session-only storage (Streamlit session state, in-memory).
-- This schema documents the logical data model for reference and future migration to persistent storage.
-- If v2 adds persistent storage, this schema would be implemented in SQLite or PostgreSQL.

-- ============================================================================
-- SESSIONS TABLE
-- ============================================================================
-- Stores metadata about user sessions (for v2 with persistence)
-- In v1, this is implicit (Streamlit's built-in session ID)

CREATE TABLE sessions (
  session_id VARCHAR(255) PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(20) DEFAULT 'active' COMMENT 'active, expired, cleared',
  ip_address VARCHAR(45),
  user_agent TEXT
);

-- ============================================================================
-- DOCUMENTS TABLE
-- ============================================================================
-- Stores metadata about uploaded files and their parsed content

CREATE TABLE documents (
  document_id VARCHAR(255) PRIMARY KEY,
  session_id VARCHAR(255) NOT NULL,
  filename VARCHAR(512) NOT NULL,
  file_format VARCHAR(20) NOT NULL COMMENT 'pdf, image, excel, powerpoint, video, unknown',
  file_size_bytes BIGINT,
  file_hash VARCHAR(64) COMMENT 'SHA-256 hash for deduplication',
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  parsed_successfully BOOLEAN DEFAULT FALSE,
  parse_error_message TEXT,
  page_count INTEGER COMMENT 'Estimated pages/sections',
  indexed_at TIMESTAMP,
  embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small' COMMENT 'Model used to generate embeddings',
  
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
  INDEX idx_session_id (session_id),
  INDEX idx_file_hash (file_hash)
);

-- ============================================================================
-- PARSED_CONTENT TABLE
-- ============================================================================
-- Stores extracted text from documents, segmented into passages for retrieval

CREATE TABLE parsed_content (
  passage_id VARCHAR(255) PRIMARY KEY,
  document_id VARCHAR(255) NOT NULL,
  passage_text TEXT NOT NULL COMMENT 'Text chunk (typically 1-2 paragraphs or a page section)',
  passage_index INTEGER COMMENT 'Sequential order within the document',
  section_name VARCHAR(255) COMMENT 'e.g., "Maintenance", "Specifications", page number',
  start_offset INTEGER COMMENT 'Character offset in the original document',
  end_offset INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
  INDEX idx_document_id (document_id)
);

-- ============================================================================
-- EMBEDDINGS TABLE
-- ============================================================================
-- Stores vector embeddings of passages for semantic search
-- Note: In v1, embeddings are stored in memory (FAISS index), not in a database.
-- This table is for reference; in v2 with persistent storage, embeddings would be
-- stored here or in a dedicated vector database (Pinecone, Weaviate, etc.)

CREATE TABLE embeddings (
  embedding_id VARCHAR(255) PRIMARY KEY,
  passage_id VARCHAR(255) NOT NULL UNIQUE,
  embedding BLOB NOT NULL COMMENT 'Vector embedding (serialized as binary)',
  embedding_dimension INTEGER DEFAULT 1536 COMMENT 'OpenAI text-embedding-3-small is 1536-dim',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (passage_id) REFERENCES parsed_content(passage_id) ON DELETE CASCADE,
  INDEX idx_passage_id (passage_id)
);

-- ============================================================================
-- QUERIES TABLE
-- ============================================================================
-- Stores query history for audit and potential analytics (v2)

CREATE TABLE queries (
  query_id VARCHAR(255) PRIMARY KEY,
  session_id VARCHAR(255) NOT NULL,
  query_text TEXT NOT NULL,
  answer_text TEXT,
  answer_status VARCHAR(20) COMMENT 'success, no_results, out_of_scope, error',
  response_time_ms INTEGER,
  confidence_score FLOAT COMMENT 'Confidence of the answer (0-1)',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
  INDEX idx_session_id (session_id),
  INDEX idx_created_at (created_at)
);

-- ============================================================================
-- QUERY_SOURCES TABLE
-- ============================================================================
-- Junction table: links each query to the document passages used to generate its answer

CREATE TABLE query_sources (
  query_source_id VARCHAR(255) PRIMARY KEY,
  query_id VARCHAR(255) NOT NULL,
  passage_id VARCHAR(255) NOT NULL,
  relevance_score FLOAT COMMENT 'Similarity score from vector search (0-1)',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (query_id) REFERENCES queries(query_id) ON DELETE CASCADE,
  FOREIGN KEY (passage_id) REFERENCES parsed_content(passage_id) ON DELETE CASCADE,
  INDEX idx_query_id (query_id),
  INDEX idx_passage_id (passage_id)
);

-- ============================================================================
-- DATA MODEL NOTES FOR v1 (Session-Only)
-- ============================================================================

/*
For Version 1.0, the application uses Streamlit's session state to store:

1. SESSIONS: Implicit (Streamlit's built-in session_id, keyed by browser tab)
2. DOCUMENTS: In-memory dictionary in st.session_state['documents']
   - Structure: {'doc_id_1': Document(filename, format, parsed_text, ...)}
3. PARSED_CONTENT: Stored as part of Document object, not separate table
   - Passages split by document parser, stored in Document.passages list
4. EMBEDDINGS: Stored as FAISS index in memory (st.session_state['faiss_index'])
   - Passage IDs mapped to embedding vectors in-memory
5. QUERIES: In-memory list in st.session_state['query_history']
6. QUERY_SOURCES: Implicit, stored as part of Query object (links to passages)

Cleanup: All data is deleted when the session ends (browser closes, timeout, or user clicks "Clear").

For Version 2.0 (if persistent storage is added):
- Migrate all in-memory structures to corresponding database tables
- Add user authentication and session tracking
- Use a persistent vector database (Pinecone, Weaviate, or PostgreSQL with pgvector)
- Implement session expiration and cleanup jobs
*/

-- ============================================================================
-- EXAMPLE QUERIES FOR v2 IMPLEMENTATION
-- ============================================================================

-- Find all documents uploaded in a session:
-- SELECT filename, file_format, uploaded_at FROM documents WHERE session_id = ?;

-- Find passages in a document:
-- SELECT passage_id, passage_text, section_name FROM parsed_content WHERE document_id = ?;

-- Find query history for a session:
-- SELECT query_text, answer_text, answer_status, created_at FROM queries WHERE session_id = ? ORDER BY created_at DESC;

-- Find sources used for a query:
-- SELECT qs.passage_id, pc.passage_text, d.filename, qs.relevance_score
-- FROM query_sources qs
-- JOIN parsed_content pc ON qs.passage_id = pc.passage_id
-- JOIN documents d ON pc.document_id = d.document_id
-- WHERE qs.query_id = ?;

-- ============================================================================
-- INDEXES AND CONSTRAINTS
-- ============================================================================
-- All foreign keys cascade on delete (session deletion cleans up related data)
-- Indexes on session_id, document_id, passage_id for fast lookups
-- Unique constraint on file_hash to prevent duplicate uploads
-- No unique constraints on query text (users may ask the same question multiple times)

-- ============================================================================
-- FUTURE CONSIDERATIONS (v2+)
-- ============================================================================
-- 1. Add user_id and authentication to track individual users instead of sessions
-- 2. Add shared_document_id for multi-user collaboration on the same document
-- 3. Add annotation table (user comments, corrections) for document feedback
-- 4. Add feedback table (user satisfaction on answers) for model improvement
-- 5. Migrate embeddings to a dedicated vector database for better scalability
-- 6. Add audit_log table for compliance and debugging
-- 7. Add cost_tracking table to bill users by API usage (embedding + LLM tokens)
