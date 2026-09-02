# 0001. Use Streamlit as the Web Framework

**Date**: 2026-08-19  
**Status**: Accepted

## Context

The application requires a web-based interface for file upload and natural language querying. The SRS specifies v1 should be simple, require few concurrent users, and have open access (no authentication). The choice of web framework affects time-to-market, maintainability, and whether a separate frontend/backend is needed.

## Decision

We will use **Streamlit** as the web framework, delivering the entire application (UI, business logic, data handling) as a single Python service. Streamlit handles session state, Rerun cycles, and web server setup automatically, reducing boilerplate and time-to-first-working-app.

## Alternatives Considered

1. **Flask/FastAPI + React/Vue**: Traditional frontend/backend separation. Rejected because it requires managing two deployment units, increases complexity, and v1's scale (few concurrent users) doesn't justify the separation. Streamlit's integrated model is simpler.

2. **Streamlit Cloud** (deployment): Streamlit offers managed hosting. Accepted as *deployment* target, but not a framework choice — Streamlit is still the framework either way.

3. **Gradio**: Lightweight alternative for simple interfaces. Rejected because Streamlit has better multi-page support and richer session state management needed for querying documents across sessions.

## Consequences

- **Simpler**: No frontend/backend communication contract to manage. Session state lives in Streamlit's built-in session, reducing boilerplate.
- **Faster to prototype**: Streamlit's `@st.cache_data`, `@st.cache_resource`, and session state decorators handle caching and persistence automatically.
- **Constraint**: Streamlit reruns the entire script on every interaction (on_change, button click, etc.). Must architect to minimize redundant work (see rerun-cost mitigation in the Internal Design section and cache usage).
- **Hosting**: Streamlit apps are single-process Python; not horizontally scalable without significant refactoring. OK for v1 (few concurrent users), but scaling beyond that will require a redesign.
- **No traditional REST API**: The API boundary (Phase 5 in SDD) is implicit in the Streamlit app's UI components and session callbacks, not an explicit OpenAPI spec. This is acceptable for v1 since there are no external API consumers.

---

# 0002. Use Python with LangChain + OpenAI API for Natural Language Querying

**Date**: 2026-08-19  
**Status**: Accepted

## Context

The application must answer natural language questions about document content. This requires:
- Embedding documents and queries into semantic vectors
- Retrieving relevant passages by semantic similarity
- Generating natural language answers (not just retrieving snippets)

A large language model (LLM) is the most practical choice. The question is whether to use an API (OpenAI, Anthropic, etc.) or a locally-run model.

## Decision

We will use **LangChain** as a wrapper library and **OpenAI API** (GPT-4 or GPT-3.5-Turbo) to generate answers. LangChain provides a standard interface for LLMs, vector stores, and document loading, reducing integration time.

## Alternatives Considered

1. **Local LLM (Ollama, LLaMA)**: Runs on device, no API costs, fully private. Rejected because it requires more compute resources, slower inference, and v1's scale (few users) doesn't offset the operational complexity. OpenAI API is simpler.

2. **Anthropic Claude API**: Alternative LLM service. Rejected because OpenAI's API is more mature, widely supported by libraries (LangChain, LlamaIndex), and offers GPT-4 (higher quality) and GPT-3.5-Turbo (cheaper) tiers. Can switch later if needed.

3. **No LLM, rules-based extraction**: Parse documents manually and return exact matches. Rejected because natural language queries require semantic understanding; exact matching fails on rephrasing (e.g., "recommended tire PSI" vs. "tire pressure").

## Consequences

- **Pros**: Simple integration via LangChain. High quality answers. LangChain's abstractions make it easy to swap to a different LLM later if needed.
- **Cons**: Introduces API dependency and cost (per-token billing). Requires valid OpenAI API key at runtime. Network latency for each query (~1–2 sec for inference).
- **Mitigation**: LLM output is not persisted, so no licensing/data-residency issues. Cache LLM calls per session to avoid redundant queries.

---

# 0003. Use FAISS for In-Memory Vector Indexing and Semantic Search

**Date**: 2026-08-19  
**Status**: Accepted

## Context

The application must find relevant passages in uploaded documents to send to the LLM. Without semantic search, a keyword-based approach would miss rephrased questions. The choice is between external vector databases (Pinecone, Weaviate) and in-memory libraries (FAISS, Annoy).

## Decision

We will use **FAISS** (Facebook AI Similarity Search) as the vector store. FAISS indexes embeddings in-memory, runs locally (no external service), and integrates directly with LangChain.

## Alternatives Considered

1. **External vector DB (Pinecone, Weaviate, Milvus)**: Persistent, scalable, managed. Rejected because v1's scope requires session-only storage (documents not persisted); persistent indexing adds no value. FAISS is sufficient.

2. **Annoy, ScaNN, or Faiss alternatives**: Similar in-memory libraries. Rejected because FAISS has best-in-class performance, widest library support (LangChain integration is seamless), and is the de facto standard for this use case.

3. **No semantic search, use keyword/TF-IDF indexing**: Faster to implement. Rejected because it fails on synonyms and rephrased queries (e.g., "tire PSI" vs. "pressure recommendation").

## Consequences

- **Pros**: Fast in-memory search. No external service to manage. Indexes discarded at session end (simplifies cleanup).
- **Cons**: Memory usage grows with number/size of documents. Limited to single-machine (not horizontally scaled). If documents persist in v2, FAISS is not suitable; must migrate to external DB.
- **Mitigation**: v1 is session-only, so max 10 documents < 50 MB each fits comfortably in memory. Monitor during testing. Document migration path in v2 planning.

---

# 0004. Use Session-Only Temporary Storage; No Persistent Database

**Date**: 2026-08-19  
**Status**: Accepted

## Context

The SRS specifies documents are stored temporarily during a session and cleared when the session ends. The application must decide whether to use a persistent database (to support multi-user scenarios in the future) or session-only storage (simplest for v1).

## Decision

We will use **Streamlit session state** (in-memory, ephemeral) for storing uploaded files, parsed content, embeddings, and query history. No persistent database (no PostgreSQL, SQLite, etc.) in v1.

## Alternatives Considered

1. **SQLite or PostgreSQL for session tracking**: Persistent across sessions, useful if v2 adds user profiles or historical search. Rejected because v1 explicitly defers persistent storage and authentication; a database adds operational complexity (migrations, backups, access control) with no immediate value. YAGNI applies.

2. **Redis for session state**: Distributed session store, useful if scaling to multiple app instances. Rejected for the same reason — v1 is single-instance Streamlit; Redis is premature.

3. **Temporary files on disk + cleanup**: Files written to `/tmp` or a temporary directory, cleaned up on session end. Acceptable alternative to pure in-memory (less memory pressure), but in-memory via Streamlit session is simpler.

## Consequences

- **Pros**: Simplest implementation. No database migrations or schema versioning. Session isolation is automatic. Zero operational overhead.
- **Cons**: Files/embeddings lost on session end or app restart (by design, and per SRS). If v2 adds persistent storage, significant refactoring needed. Multi-instance deployments (load balancing) will not share session state.
- **Mitigation**: Design service boundary clearly (ADR-0001: single Streamlit service, not distributed). Document v2 migration path for persistent storage. Add a warning in the UI if session timeout is approaching.

---

# 0005. Use OpenAI Embeddings for Semantic Vector Representation

**Date**: 2026-08-19  
**Status**: Accepted

## Context

FAISS requires vector embeddings (numerical representations) of document text and queries. Embeddings must be created by some model — either OpenAI's embedding API, a local model (Sentence Transformers), or an open-source library.

## Decision

We will use **OpenAI's Embedding API** (text-embedding-3-small or similar) to generate embeddings for document passages and user queries.

## Alternatives Considered

1. **Sentence Transformers (local)**: Open-source embedding model (e.g., `all-MiniLM-L6-v2`), runs on device, no API cost. Rejected because OpenAI embeddings are higher quality, and the per-query cost is minimal for v1's scale (few users). Simplifies the stack.

2. **No embeddings, keyword-based indexing**: Reject outright; loses semantic understanding (see ADR-0003).

## Consequences

- **Pros**: High-quality embeddings. LangChain integration. Can use same OpenAI API key as for LLM queries.
- **Cons**: API cost (per-token billing for embeddings, separate from LLM calls). Network latency on first upload (embedding all passages). Dependency on external API uptime.
- **Mitigation**: Cache embeddings per document in session state (Streamlit `@st.cache_resource`) so embeddings are computed once per session. Monitor API usage in logs.

---

# 0006. Use Multi-Format File Parsing with PyPDF2, python-pptx, Pandas, Pillow, and moviepy

**Date**: 2026-08-19  
**Status**: Accepted

## Context

The SRS requires support for PDF, images, Excel, PowerPoint, and video files. Each format needs a different parsing library. The choice is whether to use separate libraries (more control, more dependencies) or a unified library.

## Decision

We will use **separate, best-in-class libraries for each format**:
- **PDF**: PyPDF2 (or pdfplumber for better extraction)
- **Images**: Pillow + pytesseract (OCR) or EasyOCR
- **Excel**: pandas.read_excel()
- **PowerPoint**: python-pptx
- **Video**: moviepy (for metadata/captions) or speech-to-text via OpenAI Whisper API

## Alternatives Considered

1. **Single unified library (Unstructured, DocumentLoaders)**: Abstracts format differences. Rejected because it's an extra dependency and less flexible if one format needs special handling. Direct libraries give us control.

2. **Cloud-based parsing (Azure Document Intelligence, AWS Textract)**: Managed services. Rejected because it adds API costs and external dependency; local parsing is sufficient for v1.

## Consequences

- **Pros**: Each library is optimized for its format. Clear error handling per format.
- **Cons**: Many dependencies to manage. Version conflicts possible. Each format has its own learning curve.
- **Mitigation**: Dependency list reviewed at project setup. Parsing is wrapped in a single `DocumentParser` component with a consistent interface, hiding format differences from the rest of the app.

---

# 0007. Use Streamlit's Built-in Caching Decorators to Minimize Rerun Costs

**Date**: 2026-08-19  
**Status**: Accepted

## Context

Streamlit reruns the entire app script on every user interaction (button click, text input, file upload, etc.). Without caching, expensive operations (document parsing, embedding computation, LLM calls) would re-run unnecessarily, killing performance.

## Decision

We will use **@st.cache_data** (for data transformations) and **@st.cache_resource** (for stateful objects like embeddings and FAISS indexes) to cache results across reruns within a session.

## Alternatives Considered

1. **Manual state management**: Use `st.session_state` without decorators. Rejected because decorators handle cache invalidation and scope automatically; manual management is error-prone.

2. **Minimize script reruns by refactoring to multi-page app**: Streamlit's multi-page feature reduces rerun scope. Accepted as a *design pattern* (used in Internal Design, Phase 8), but caching decorators are still needed.

## Consequences

- **Pros**: Simple syntax. Automatic cache invalidation based on input arguments.
- **Cons**: Cache scope is function-level; global state must be carefully managed. Cache keys are based on argument hash, so unhashable types (dicts with mutable values, file objects) can cause issues.
- **Mitigation**: Document caching strategy clearly in code. Use immutable data structures where possible. For large files, cache at a finer granularity (e.g., parsed text, not raw file object).

---
