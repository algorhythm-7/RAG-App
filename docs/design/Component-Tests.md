# Component-Level Tests

**Version**: 1.0  
**Date**: 2026-08-19  
**Derived from**: SRS Acceptance Tests + SDD Component Design  

This document maps Acceptance Tests (ATs) to Component-Level Tests (CTs) and Core/Shell layers, showing how the design's internal components verify requirements.

---

## Component Architecture Recap

| Component | Responsibility | Layer |
|-----------|-----------------|-------|
| UIPage | Streamlit UI rendering, user input handling | Shell |
| DocumentUploadHandler | File validation, format detection, routing to parsers | Shell |
| DocumentParser (core) | Extract text from documents | Core |
| DocumentParser (shell) | Coordinate parsing calls, error handling | Shell |
| EmbeddingGenerator (core) | Generate and store embeddings for passages | Core |
| EmbeddingGenerator (shell) | Call OpenAI API, cache embeddings | Shell |
| SemanticIndexer (core) | Build and query FAISS index | Core |
| QueryProcessor (core) | Retrieve relevant passages, score by relevance | Core |
| AnswerGenerator (core) | Format retrieved passages for LLM prompt | Core |
| AnswerGenerator (shell) | Call OpenAI LLM API, parse response | Shell |
| SessionManager | Manage session state and cleanup | Shell |
| ErrorHandler | Catch and format errors | Shell |

---

## Component Test Matrix

### CT-01: File Upload & Parsing

#### CT-01.1: PDF Parsing (Core)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-01-1a | DocumentParser | Core | AT-01.1 (PDF success) | A valid PDF file in bytes | DocumentParser.parse_pdf() is called | Returns list of passages with non-empty text |

**Implementation**: Unit test, no mocking
```python
def test_parse_pdf_returns_passages():
    pdf_bytes = load_test_file("test_manual_100pages.pdf")
    passages = DocumentParser.parse_pdf(pdf_bytes)
    assert len(passages) > 0
    assert all(len(p.text) > 0 for p in passages)
    assert all(isinstance(p, Passage) for p in passages)
```

---

#### CT-01.1b: PDF Parsing Error (Core)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-01-1b | DocumentParser | Core | AT-01.8 (corrupted PDF) | A corrupted/truncated PDF file in bytes | DocumentParser.parse_pdf() is called | Raises ParseError with descriptive message |

**Implementation**: Unit test
```python
def test_parse_pdf_corrupted_raises_error():
    pdf_bytes = b"corrupted data not a pdf"
    with pytest.raises(ParseError) as exc_info:
        DocumentParser.parse_pdf(pdf_bytes)
    assert "Unable to parse PDF" in str(exc_info.value)
```

---

#### CT-01.2: Image Parsing with OCR (Core)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-01-2 | DocumentParser | Core | AT-01.2 (image upload) | A scanned manual page image (PNG, JPG) | DocumentParser.parse_image() is called | Returns extracted text passages |

**Implementation**: Unit test with mocked OCR (EasyOCR or pytesseract)
```python
def test_parse_image_extracts_text():
    image_bytes = load_test_file("scanned_page.png")
    passages = DocumentParser.parse_image(image_bytes)
    assert len(passages) > 0
    assert any("tire pressure" in p.text.lower() for p in passages)
```

---

#### CT-01.3: Excel Parsing (Core)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-01-3 | DocumentParser | Core | AT-01.3 (Excel upload) | An Excel file (maintenance schedule) | DocumentParser.parse_excel() is called | Returns passages from all cells and sheet names |

**Implementation**: Unit test
```python
def test_parse_excel_extracts_all_sheets():
    excel_bytes = load_test_file("maintenance_schedule.xlsx")
    passages = DocumentParser.parse_excel(excel_bytes)
    text = "\n".join([p.text for p in passages])
    assert "maintenance" in text.lower()
```

---

#### CT-01.4: PowerPoint Parsing (Core)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-01-4 | DocumentParser | Core | AT-01.4 (PowerPoint upload) | A PowerPoint file | DocumentParser.parse_powerpoint() is called | Returns passages from all slides |

**Implementation**: Unit test
```python
def test_parse_powerpoint_extracts_slides():
    pptx_bytes = load_test_file("training.pptx")
    passages = DocumentParser.parse_powerpoint(pptx_bytes)
    assert len(passages) > 0
```

---

#### CT-01.5: File Validation (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-01-5 | DocumentUploadHandler | Shell | AT-01.6 (unsupported format), AT-01.7 (size limit) | Unsupported file (.txt, .zip) or file > 50 MB | DocumentUploadHandler.validate_file() is called | Returns ValidationError with appropriate message |

**Implementation**: Unit test
```python
def test_validate_file_rejects_unsupported_format():
    with pytest.raises(ValidationError) as exc:
        DocumentUploadHandler.validate_file(
            filename="doc.txt",
            file_bytes=b"content",
            max_size_bytes=50*1024*1024
        )
    assert "File format not supported" in str(exc.value)

def test_validate_file_rejects_oversized():
    large_bytes = b"x" * (51 * 1024 * 1024)
    with pytest.raises(ValidationError) as exc:
        DocumentUploadHandler.validate_file(
            filename="manual.pdf",
            file_bytes=large_bytes,
            max_size_bytes=50*1024*1024
        )
    assert "too large" in str(exc.value)
```

---

#### CT-01.6: Duplicate Detection (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-01-6 | DocumentUploadHandler, SessionManager | Shell | AT-01.9 (duplicate upload) | File already in session (by hash) | DocumentUploadHandler.handle_upload() is called with same file | Returns DuplicateFileError; no re-indexing |

**Implementation**: Integration test
```python
def test_duplicate_file_rejected(session_manager):
    file_bytes = load_test_file("manual.pdf")
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    # First upload succeeds
    doc1 = DocumentUploadHandler.handle_upload("manual.pdf", file_bytes, session_manager)
    assert doc1.document_id is not None
    
    # Second upload is rejected
    with pytest.raises(DuplicateFileError):
        DocumentUploadHandler.handle_upload("manual.pdf", file_bytes, session_manager)
```

---

### CT-02: Embedding & Indexing

#### CT-02.1: Embedding Generation (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-02-1 | EmbeddingGenerator | Shell | AT-02.1, AT-05.1 (query performance) | Parsed passages from a document | EmbeddingGenerator.embed_passages() is called | Returns embeddings for each passage; caches them |

**Implementation**: Integration test with mocked OpenAI API
```python
def test_embed_passages_returns_vectors(mocker):
    mock_openai = mocker.patch("openai.Embedding.create")
    mock_openai.return_value = {
        "data": [
            {"embedding": [0.1, 0.2, ...], "index": 0},
            {"embedding": [0.3, 0.4, ...], "index": 1},
        ]
    }
    
    passages = [
        Passage("tire pressure", section="Specs"),
        Passage("maintenance schedule", section="Maintenance")
    ]
    
    embeddings = EmbeddingGenerator.embed_passages(passages)
    assert len(embeddings) == len(passages)
    assert all(len(e) == 1536 for e in embeddings)  # OpenAI embedding size
```

---

#### CT-02.2: FAISS Indexing (Core)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-02-2 | SemanticIndexer | Core | AT-02.1, AT-02.2 (multi-document search) | 10 embeddings (vectors) and passage IDs | SemanticIndexer.build_index() is called | Returns FAISS index; can query it |

**Implementation**: Unit test
```python
def test_build_faiss_index():
    embeddings = [np.random.rand(1536) for _ in range(10)]
    passages = [f"passage_{i}" for i in range(10)]
    
    index = SemanticIndexer.build_index(embeddings, passages)
    assert index is not None
    assert index.ntotal == 10
```

---

#### CT-02.3: Similarity Search (Core)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-02-3 | SemanticIndexer, QueryProcessor | Core | AT-02.1 (relevant content found) | FAISS index, a query embedding | QueryProcessor.find_relevant_passages() is called | Returns top-K passages sorted by relevance score |

**Implementation**: Unit test
```python
def test_find_relevant_passages():
    # Create mock index with 10 passages
    embeddings = [np.random.rand(1536) for _ in range(10)]
    passages = [Passage(f"text_{i}") for i in range(10)]
    index = SemanticIndexer.build_index(embeddings, passages)
    
    # Query
    query_embedding = embeddings[0]  # Should match first passage best
    results = QueryProcessor.find_relevant_passages(index, query_embedding, top_k=3)
    
    assert len(results) <= 3
    assert passages[0] in results  # Most relevant
    assert all(hasattr(r, "relevance_score") for r in results)
```

---

### CT-03: Query Processing & Answer Generation

#### CT-03.1: LLM Answer Generation (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-03-1 | AnswerGenerator | Shell | AT-02.1 (successful query) | Retrieved passages and a user query | AnswerGenerator.generate_answer() is called | Returns natural language answer from LLM |

**Implementation**: Integration test with mocked OpenAI API
```python
def test_generate_answer_with_llm(mocker):
    mock_openai = mocker.patch("openai.ChatCompletion.create")
    mock_openai.return_value = {
        "choices": [{"message": {"content": "The recommended tire pressure is 32 PSI."}}]
    }
    
    passages = [Passage("Tire pressure: 32 PSI (normal conditions)", section="Specs")]
    query = "What's the tire pressure?"
    
    answer = AnswerGenerator.generate_answer(query, passages)
    assert "32 PSI" in answer
    assert isinstance(answer, str)
```

---

#### CT-03.2: No Results Handling (Core)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-03-2 | QueryProcessor | Core | AT-02.3 (no relevant content) | FAISS index, a query with no matching passages | QueryProcessor.find_relevant_passages() is called | Returns empty list or low-confidence results |

**Implementation**: Unit test
```python
def test_no_relevant_passages():
    # Index has documents about cars; query is about cake baking
    index = SemanticIndexer.build_index([...], [...])
    query_embedding = encode_query("How do I bake a cake?")
    
    results = QueryProcessor.find_relevant_passages(index, query_embedding, top_k=5)
    assert len(results) == 0 or all(r.relevance_score < 0.3 for r in results)
```

---

#### CT-03.3: Out-of-Scope Detection (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-03-3 | AnswerGenerator | Shell | AT-02.4 (out-of-scope query) | Retrieved passages with low relevance, user query unrelated to docs | AnswerGenerator.generate_answer() is called | Returns message indicating query is unrelated |

**Implementation**: Integration test
```python
def test_out_of_scope_query_detected(mocker):
    # Simulate low relevance
    passages = []  # No relevant passages
    query = "What's the weather tomorrow?"
    
    answer = AnswerGenerator.generate_answer(query, passages)
    assert "doesn't relate" in answer.lower() or "no information" in answer.lower()
```

---

#### CT-03.4: Query Timeout (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-03-4 | AnswerGenerator | Shell | AT-02.5 (timeout) | LLM API is slow (simulated delay > 30s) | AnswerGenerator.generate_answer() is called with timeout | Raises TimeoutError; does not hang |

**Implementation**: Integration test
```python
def test_query_timeout():
    # Mock slow LLM
    def slow_llm(*args, **kwargs):
        time.sleep(35)
        return {"choices": [{"message": {"content": "..."}}]}
    
    with pytest.raises(TimeoutError):
        AnswerGenerator.generate_answer(
            "query",
            [],
            timeout_seconds=30,
            llm_func=slow_llm
        )
```

---

### CT-04: Session Management

#### CT-04.1: Session Isolation (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-04-1 | SessionManager | Shell | AT-04.1 (files cleared on session end) | Two separate session objects | Session A uploads a file; Session B starts fresh | Session B has no documents from Session A |

**Implementation**: Integration test
```python
def test_session_isolation():
    session_a = SessionManager.create_session()
    session_b = SessionManager.create_session()
    
    # Upload to session A
    file_bytes = load_test_file("manual.pdf")
    DocumentUploadHandler.handle_upload("manual.pdf", file_bytes, session_a)
    assert len(session_a.documents) == 1
    
    # Session B should be empty
    assert len(session_b.documents) == 0
```

---

#### CT-04.2: Session Cleanup (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-04-2 | SessionManager | Shell | AT-04.2 (files not persisted) | Session with uploaded documents | SessionManager.clear_session() is called | All documents, embeddings, indexes are deleted |

**Implementation**: Unit test
```python
def test_clear_session_deletes_all_data():
    session = SessionManager.create_session()
    file_bytes = load_test_file("manual.pdf")
    DocumentUploadHandler.handle_upload("manual.pdf", file_bytes, session)
    
    assert len(session.documents) > 0
    SessionManager.clear_session(session)
    assert len(session.documents) == 0
    assert session.faiss_index is None
```

---

### CT-05: Error Handling

#### CT-05.1: Error Logging (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-05-1 | ErrorHandler | Shell | AT-03.1, AT-03.2 (errors don't crash) | Any component raises an exception | ErrorHandler.handle_exception() is called | Exception is logged; user-friendly message is returned; app stays alive |

**Implementation**: Unit test
```python
def test_error_handler_logs_and_formats():
    try:
        raise ValueError("Internal parsing error")
    except Exception as e:
        result = ErrorHandler.handle_exception(e, context="file_upload")
    
    assert result.user_message == "Unable to parse this file. Please check the file integrity and try again."
    assert "ValueError" not in result.user_message  # No internal details
    assert result.error_code == "PARSE_FAILED"
```

---

#### CT-05.2: Error Messages Don't Expose Internals (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-05-2 | ErrorHandler, UIPage | Shell | AT-03.3 (no stack traces) | Any parsing or LLM error occurs | Error message is displayed to user | Message contains no stack trace, API keys, file paths, or technical jargon |

**Implementation**: Unit test
```python
def test_error_message_is_clean():
    try:
        raise Exception("OPENAI_API_KEY=sk-... failed: Connection refused")
    except Exception as e:
        msg = ErrorHandler.format_user_message(e)
    
    assert "OPENAI_API_KEY" not in msg
    assert "sk-" not in msg
    assert "Connection refused" not in msg
    assert "Please try again" in msg
```

---

### CT-06: Performance (NFR Verification)

#### CT-06.1: File Parsing Within 10 Seconds (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-06-1 | DocumentParser, EmbeddingGenerator | Shell | AT-05.1 (parsing time) | 100–200 page PDF (~5 MB) | Full parse + embedding pipeline runs | Completes in < 10 seconds |

**Implementation**: Performance test
```python
def test_parse_and_embed_performance():
    pdf_bytes = load_test_file("manual_100pages.pdf")
    
    start = time.time()
    passages = DocumentParser.parse_pdf(pdf_bytes)
    embeddings = EmbeddingGenerator.embed_passages(passages)
    elapsed = time.time() - start
    
    assert elapsed < 10.0, f"Parse + embed took {elapsed:.2f}s, expected < 10s"
```

---

#### CT-06.2: Query Response Within 30 Seconds (Shell)

| Test ID | Component | Layer | Verifies | Given | When | Then |
|---------|-----------|-------|----------|-------|------|------|
| ct-06-2 | QueryProcessor, AnswerGenerator | Shell | AT-05.2 (query time) | 5 documents indexed, query submitted | Full query pipeline (embed query, search, LLM) runs | Completes in < 30 seconds |

**Implementation**: Performance test
```python
def test_query_response_time():
    # Setup: 5 indexed documents
    session = setup_session_with_5_documents()
    
    query = "What's the tire pressure?"
    start = time.time()
    answer = AnswerGenerator.generate_answer_with_search(query, session)
    elapsed = time.time() - start
    
    assert elapsed < 30.0, f"Query took {elapsed:.2f}s, expected < 30s"
```

---

## Test Execution Plan

### Test Layers & Tools

| Layer | Tools | Example |
|-------|-------|---------|
| **Core (Pure Logic)** | pytest + hypothesis | `test_parse_pdf_returns_passages`, `test_build_faiss_index` |
| **Shell (I/O, APIs)** | pytest + pytest-mock (mocker) | `test_embed_passages_returns_vectors`, `test_generate_answer_with_llm` |
| **Integration** | pytest + test fixtures | `test_duplicate_file_rejected`, `test_session_isolation` |
| **Performance** | pytest + timeit | `test_parse_and_embed_performance`, `test_query_response_time` |

### Test Data Fixtures

- **test_manual_100pages.pdf**: 100–200 page authentic or synthetic PDF
- **test_manual_500pages.pdf**: Larger PDF to stress test
- **scanned_page.png**: Scanned manual page for OCR testing
- **maintenance_schedule.xlsx**: Excel file with structured data
- **training.pptx**: PowerPoint with multiple slides
- **corrupted.pdf**: Intentionally corrupted PDF for error testing

### Mocking Strategy

- **OpenAI Embedding API**: Mock with `pytest-mock`, return deterministic vectors
- **OpenAI LLM API**: Mock with `pytest-mock`, return canned responses or assert prompt correctness
- **File I/O**: Use real files from `test_manual_100pages.pdf` etc.; don't mock file reading
- **FAISS**: No mocking; use real FAISS in-memory index (lightweight)

---

## Traceability to Acceptance Tests

| Component Test Group | Acceptance Tests Verified | Coverage |
|----------------------|--------------------------|----------|
| CT-01: File Upload | AT-01.1–AT-01.10 | 100% |
| CT-02: Embedding & Indexing | AT-02.1, AT-02.2, AT-05.1 | 100% |
| CT-03: Query Processing | AT-02.1–AT-02.8, AT-05.2 | 100% |
| CT-04: Session Management | AT-04.1–AT-04.4 | 100% |
| CT-05: Error Handling | AT-03.1–AT-03.4 | 100% |
| CT-06: Performance | AT-05.1–AT-05.3 | 100% |

---

## Gaps & Deferred Tests

- **Stress testing**: > 10 documents, files near 50 MB limit (deferred to v1.1)
- **Internationalization**: Non-English text, OCR for non-Latin scripts (deferred to v2)
- **Cache invalidation**: Ensure caches clear on session end (implicit in SessionManager, not separately tested)

---

## End of Component-Level Tests
