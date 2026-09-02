---
name: Document Query Application Agent
description: |
  Specialized agent for the Document Query Application (vehicle owner's manual assistant).
  Understands the project architecture, coding conventions, design decisions, and how to
  navigate the codebase effectively.
author: Development Team
version: 1.0
created: 2026-08-19
applyTo:
  - "src/**/*.py"
  - "tests/**/*.py"
  - "docs/**/*.md"
  - "*.md"
---

# Document Query Application — Agent Customization

## Project Context

This is a **Streamlit-based web application** that allows vehicle owners and fleet managers to upload owner's manuals (PDF, images, Excel, PowerPoint, video) and ask natural language questions about them.

### Key Facts
- **Language**: Python 3.9+
- **Framework**: Streamlit (single-service architecture, no frontend/backend split)
- **LLM**: OpenAI API (GPT-3.5-Turbo or GPT-4)
- **Vector Store**: FAISS (in-memory, session-only)
- **Deployment**: Streamlit Cloud or Docker
- **Status**: v1.0 (draft)

### Architecture at a Glance
```
User → Streamlit Web App → Components (Parser, Embedder, Indexer, etc.) → OpenAI API
                         ↓
                    Session State (in-memory)
```

**See**: [docs/design/SDD.html](docs/design/SDD.html) (open in browser for diagrams)

---

## Coding Conventions

### Python Style

- **Standard**: PEP 8
- **Formatter**: Use `black` (line length = 100) if available
- **Import Order**: Use `isort` (stdlib, third-party, local)
- **Linter**: `flake8` (optional but recommended)
- **Type Hints**: Strongly recommended for all functions
- **Docstrings**: Google-style format for modules, classes, and functions

### Example Function

```python
"""Module docstring explaining purpose."""

from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Passage:
    """A text passage extracted from a document.
    
    Attributes:
        text: The extracted text content.
        section: The document section or page reference.
        document_id: ID of the source document.
    """
    text: str
    section: str
    document_id: str

def extract_passages(file_bytes: bytes) -> List[Passage]:
    """Extract text passages from a file.
    
    Args:
        file_bytes: Raw file bytes (PDF, image, etc.).
    
    Returns:
        List of Passage objects with extracted text.
    
    Raises:
        ParseError: If file cannot be parsed.
    """
    # Implementation
    return passages
```

### File Organization

- **Component files** (src/components/): One responsibility per file
  - `document_parser.py` → parsing only
  - `embedding_generator.py` → embeddings only
  - etc.
- **Page files** (src/pages/): One Streamlit page per file
  - `1_Upload.py` → file upload interface
  - `2_Query.py` → query interface
  - `3_Session.py` → session management
- **Test files** (tests/): Mirror src structure, prefix with `test_`
  - `tests/test_document_parser.py` → tests for document_parser.py
  - etc.

---

## How to Navigate the Codebase

### Understanding a Feature

1. **Read the Requirement**: Find it in [docs/SRS.md](docs/SRS.md)
   - Look for the feature (feat-01, feat-02, etc.)
   - Read the use case (uc-01, uc-02, etc.)
   - Read related functional requirements (FR-*)

2. **See the Design**: Open [docs/design/SDD.html](docs/design/SDD.html) in a browser
   - Component diagram shows how pieces fit together
   - Sequence diagram shows the workflow
   - Internal Design section explains each component's responsibility

3. **Check the ADRs**: If you need to understand *why* a decision was made:
   - Look in [docs/design/adr/](docs/design/adr/)
   - Each ADR has Context, Decision, Alternatives, and Consequences

4. **Find the Code**: Map requirement → design → code
   - Use the Traceability Matrix in [docs/design/SDD.html](docs/design/SDD.html)
   - Example: feat-02 (Multi-Document Query) → component QueryProcessor → src/components/query_processor.py

5. **Read the Tests**: Tests document expected behavior
   - Acceptance tests: [docs/ACCEPTANCE_TESTS.md](docs/ACCEPTANCE_TESTS.md) (AT-01 through AT-06)
   - Component tests: [docs/design/Component-Tests.md](docs/design/Component-Tests.md) (CT-01 through CT-06)
   - Code tests: `tests/test_*.py` (pytest)

### Example: Understanding File Upload Flow

```
Requirement: need-01 "upload owner's manual"
       ↓
Use Case: uc-01 "Upload Owner's Manual" 
       ↓
Feature: feat-01 "File Upload"
       ↓
Functional Requirements: FR-01.1 to FR-01.7
       ↓
Design Components: FileUploadHandler, DocumentParser, EmbeddingGenerator, SemanticIndexer
       ↓
Implementation: 
  - src/pages/1_Upload.py (UI)
  - src/components/document_parser.py (parsing)
  - src/components/embedding_generator.py (embeddings)
  - src/components/session_manager.py (storage)
       ↓
Tests:
  - tests/test_document_parser.py (CT-01.1–01.5)
  - tests/test_session_manager.py (CT-04.1)
  - docs/ACCEPTANCE_TESTS.md (AT-01.1–01.10)
```

---

## When to Check Documentation

### I need to understand the big picture
→ Read [README.md](README.md) (Quick Start & Architecture Overview sections)

### I need to understand product requirements
→ Read [docs/SRS.md](docs/SRS.md) (Features, Use Cases, Requirements)

### I need to understand system design
→ Open [docs/design/SDD.html](docs/design/SDD.html) in browser (diagrams render live)

### I need to understand *why* a decision was made
→ Read the relevant ADR in [docs/design/adr/](docs/design/adr/)
- ADR-0001: Why Streamlit?
- ADR-0002: Why OpenAI API?
- ADR-0003: Why FAISS?
- etc.

### I need to understand what behavior is expected
→ Read [docs/ACCEPTANCE_TESTS.md](docs/ACCEPTANCE_TESTS.md) (Given/When/Then scenarios)

### I need to understand how to test a component
→ Read [docs/design/Component-Tests.md](docs/design/Component-Tests.md) (CT-* specifications with code examples)

### I need to implement a specific component
→ Read the design section in [docs/design/SDD.html](docs/design/SDD.html) (§7 Internal Design) to see its responsibility and dependencies

---

## Common Development Tasks

### Task 1: Add Support for a New File Format

**Steps**:
1. Update `src/components/document_parser.py`:
   - Add a `parse_xyz()` function
   - Return a list of `Passage` objects
   - Handle errors gracefully (raise `ParseError`)

2. Update `src/utils/validators.py`:
   - Add `.xyz` to the list of supported formats

3. Update `src/components/document_parser.py` — `DocumentParser.parse()` method:
   - Route `.xyz` files to `parse_xyz()`

4. Add tests in `tests/test_document_parser.py`:
   - `test_parse_xyz_returns_passages()` (happy path)
   - `test_parse_xyz_handles_corrupted()` (error case)

5. Update `requirements.txt` if you added a new parsing library

6. Test manually:
   ```bash
   streamlit run app.py
   # Upload a .xyz file and verify it works
   ```

7. Update [docs/SRS.md](docs/SRS.md) if the new format was deferred (move from Future Considerations to In Scope)

**Reference**: ADR-0006 (Multi-Format Parsing)

### Task 2: Improve Query Performance (NFR-01.2: < 30 seconds)

**Diagnosis**:
1. Run performance test: `pytest tests/test_performance.py::test_query_response_time -v`
2. Identify bottleneck (embedding? LLM? search?)

**Optimization Options**:
- **Reduce LLM latency**: Switch from GPT-4 to GPT-3.5-Turbo (faster, cheaper)
- **Reduce embedding cost**: Chunk passages larger (faster search, less context)
- **Reduce search latency**: Use fewer top-K passages (trade-off: may miss relevant info)
- **Cache queries**: Store query → answer pairs per session (implement in v2 with persistent DB)

**How to implement**:
1. Update `src/utils/constants.py`: Change relevant timeout or model
2. Update `[docs/design/SDD.html](docs/design/SDD.html)` § Tech Stack table
3. Run tests: `pytest tests/test_performance.py -v`
4. Update [docs/SRS.md](docs/SRS.md) if NFR-01.2 baseline changes

**Reference**: ADR-0002 (LLM choice), ADR-0007 (Caching)

### Task 3: Fix an Error Handling Issue

**Example**: User gets a stack trace instead of a friendly error message.

**Steps**:
1. Locate the error in `src/components/error_handler.py`
2. Ensure it's caught and formatted properly:
   ```python
   try:
       # risky operation
   except SomeException as e:
       ErrorHandler.handle_exception(e, context="my_operation")
       return ErrorResponse(
           status="error",
           error_code="MY_ERROR",
           message="User-friendly message"
       )
   ```

3. Verify the error message does NOT contain:
   - Stack traces
   - API keys
   - File paths
   - Internal library names
   (See ADR-0001 § Consequences for security notes)

4. Add a test in `tests/test_error_handler.py`:
   ```python
   def test_error_message_is_clean():
       # Verify no internal details leak
       pass
   ```

5. Test manually to confirm user sees friendly message

**Reference**: CT-05 (Error Handling Tests), FR-03.* (Error Handling Requirements)

### Task 4: Add a New Component

**Example**: Add a `DocumentSummarizer` component to summarize documents.

**Steps**:
1. Create `src/components/document_summarizer.py` with clear single responsibility
2. Design the interface (inputs/outputs):
   ```python
   def summarize(passages: List[Passage]) -> str:
       """Summarize a list of passages into a single summary."""
   ```

3. Implement functional core (pure logic):
   ```python
   def _build_summary_prompt(passages: List[Passage]) -> str:
       """Build prompt for LLM (no I/O)."""
   ```

4. Implement imperative shell (I/O):
   ```python
   def summarize(passages: List[Passage]) -> str:
       """Call LLM API (with I/O)."""
   ```

5. Add component tests in `tests/test_document_summarizer.py`:
   - Test the functional core (no mocks)
   - Test the shell with mocked API (pytest-mock)

6. Integrate into `src/pages/` or another component (dependency injection)

7. Update [docs/design/SDD.html](docs/design/SDD.html) if it affects the design

**Reference**: [docs/design/SDD.html](docs/design/SDD.html) § Internal Design (Functional Core / Imperative Shell)

### Task 5: Write an Acceptance Test

**When**: After implementing a feature, verify it works end-to-end.

**Steps**:
1. Open [docs/ACCEPTANCE_TESTS.md](docs/ACCEPTANCE_TESTS.md)
2. Find or create an AT-* scenario relevant to your feature
3. Follow the Given/When/Then format:
   ```
   Given <precondition>
   When <action>
   Then <expected result>
   ```

4. Run the Streamlit app: `streamlit run app.py`
5. Manually follow the Given/When/Then steps
6. Verify the expected result

**Example**: AT-01.1 (Upload a PDF)
- Given: Valid PDF file available
- When: Click upload, select PDF, submit
- Then: Success message appears

**Reference**: [docs/ACCEPTANCE_TESTS.md](docs/ACCEPTANCE_TESTS.md)

---

## Design Principles to Follow

### Single Responsibility Principle

Each component has ONE reason to change.

✅ Good:
- `DocumentParser.parse_pdf()` — parses PDFs only
- `EmbeddingGenerator.embed_passages()` — embeds only
- `QueryProcessor.find_relevant_passages()` — searches only

❌ Bad:
- `DocumentHandler.upload_parse_and_embed()` — does too much

### Loose Coupling

Components depend on data structures and abstractions, not implementation details.

✅ Good:
- `QueryProcessor` depends on `Passage` (data class)
- `AnswerGenerator` depends on `QueryResult` (data class)

❌ Bad:
- `AnswerGenerator` depends on `DocumentParser` internals

### Functional Core / Imperative Shell

Pure business logic (no I/O) is separate from I/O handling.

✅ Good:
```python
# Core (pure, testable without mocks)
def _build_prompt(query: str, passages: List[Passage]) -> str:
    return f"Question: {query}\nContext: {passages}"

# Shell (I/O, testable with mocks)
def generate_answer(query: str, passages: List[Passage]) -> str:
    prompt = _build_prompt(query, passages)  # Call core
    response = openai.ChatCompletion.create(prompt=prompt)  # Call API
    return response.content
```

❌ Bad:
```python
def generate_answer(query, passages):
    prompt = f"Question: {query}\nContext: {passages}"
    response = openai.ChatCompletion.create(prompt=prompt)
    return response.content
# (Mixing logic and I/O makes testing harder)
```

### Explicit Dependencies

Components receive their dependencies (dependency injection), not hidden singletons.

✅ Good:
```python
class QueryProcessor:
    def __init__(self, embedder: EmbeddingGenerator, indexer: SemanticIndexer):
        self.embedder = embedder
        self.indexer = indexer
```

❌ Bad:
```python
class QueryProcessor:
    def __init__(self):
        self.embedder = GLOBAL_EMBEDDER  # Hidden dependency
        self.indexer = get_indexer()     # Hidden dependency
```

---

## Testing Strategy

### Test Pyramid

```
         / \
        /   \  Integration Tests (few, slow)
       /     \   — Full workflows (upload + query + session)
      /-------\
     /         \  Component Tests (many, medium)
    /           \   — QueryProcessor, EmbeddingGenerator, etc.
   /             \
  /───────────────\
 /                 \  Unit Tests (many, fast)
/                   \ — Pure logic: parsing, ranking, prompt building
─────────────────────
```

### Test Layer Mapping

| Test Type | Framework | Speed | Mocking | Example |
|-----------|-----------|-------|---------|---------|
| **Unit** | pytest | Fast | Heavy (pure logic) | `test_parse_pdf_returns_passages()` |
| **Component** | pytest + pytest-mock | Medium | Moderate (shell + core) | `test_embed_passages_returns_vectors()` |
| **Integration** | pytest + fixtures | Slow | Minimal | `test_full_upload_and_query_workflow()` |
| **Acceptance** | Manual + Streamlit | Slowest | None | AT-01.1, AT-02.3, etc. |

### Writing Tests

**Pattern 1: Pure Logic (No Mocks)**
```python
def test_parse_pdf_returns_passages():
    """Unit test — no mocking needed."""
    pdf_bytes = load_test_file("manual.pdf")
    passages = DocumentParser.parse_pdf(pdf_bytes)
    assert len(passages) > 0
    assert all(len(p.text) > 0 for p in passages)
```

**Pattern 2: Component with I/O (Mock APIs)**
```python
def test_embed_passages_calls_openai(mocker):
    """Component test — mock OpenAI API."""
    mock_openai = mocker.patch("openai.Embedding.create")
    mock_openai.return_value = {"data": [...]}
    
    passages = [Passage("text", section="Specs")]
    embeddings = EmbeddingGenerator.embed_passages(passages)
    
    assert len(embeddings) == len(passages)
```

**Pattern 3: Integration (Few Mocks, More Setup)**
```python
def test_full_query_workflow(session_manager, mocker):
    """Integration test — mock only external APIs."""
    mock_openai = mocker.patch("openai.ChatCompletion.create")
    mock_openai.return_value = {"choices": [{"message": {"content": "Answer"}}]}
    
    # Setup: upload document
    doc = DocumentUploadHandler.handle_upload("manual.pdf", file_bytes, session_manager)
    
    # Execute: query
    answer = QueryProcessor.process_query("What is tire pressure?", session_manager)
    
    # Verify
    assert "PSI" in answer
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_document_parser.py -v

# Specific test
pytest tests/test_document_parser.py::test_parse_pdf_returns_passages -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Performance tests only
pytest tests/test_performance.py -v
```

---

## When Implementing a Feature

### Checklist

- [ ] **Requirement Exists**: Find the use case (uc-*) and functional requirement (FR-*) in [docs/SRS.md](docs/SRS.md)
- [ ] **Design Reviewed**: Check [docs/design/SDD.html](docs/design/SDD.html) for relevant component
- [ ] **Code Written**: Implement in src/ with type hints and docstrings
- [ ] **Tests Added**: Add component test in tests/ and verify with `pytest`
- [ ] **Acceptance Test Passed**: Manually run relevant AT-* scenario
- [ ] **Docs Updated**: Update README, docstrings, or design docs if needed
- [ ] **Performance Checked**: Run `pytest tests/test_performance.py` if applicable
- [ ] **Errors Handled**: Use `ErrorHandler` to format user messages
- [ ] **Caching Optimized**: Use `@st.cache_data` or `@st.cache_resource` if expensive operation
- [ ] **Code Review**: Ask for feedback on design & implementation

### Example PR Description

```markdown
## Description
Adds support for Excel file uploads (feat-01 enhancement).

## Changes
- Added `DocumentParser.parse_excel()` in src/components/document_parser.py
- Added tests in tests/test_document_parser.py (CT-01.3)
- Updated requirements.txt with pandas dependency

## Testing
- ✅ Component test: `test_parse_excel_extracts_all_sheets()`
- ✅ Acceptance test: AT-01.3 (Excel upload)
- ✅ Performance: < 10s parse time for 100-row spreadsheet

## Related
- Requirement: FR-01.1 (file format support)
- Use Case: uc-01 (Upload Owner's Manual)
- Design: See SDD.html § Internal Design (DocumentParser responsibility)
```

---

## Troubleshooting

### Common Issues

**Issue**: "ImportError: No module named 'xyz'"
→ Run `pip install -r requirements.txt`

**Issue**: "OPENAI_API_KEY not set"
→ Create `.streamlit/secrets.toml` with your API key (see [README.md § Configuration](README.md#configuration))

**Issue**: "Session not found" or "State cleared unexpectedly"
→ Streamlit reruns on every interaction; use `@st.cache_data` and `st.session_state` to preserve data

**Issue**: "Test fails with 'mock not called'"
→ Ensure your mock's return value matches the expected type (dict vs object)

**Issue**: "Performance test times out (> 30s)"
→ Check which component is slow (embeddings, LLM, search?)
→ See Task 2 above (Improve Query Performance)

### Debug Workflow

1. **Enable debug logging**: Set `LOG_LEVEL=DEBUG` environment variable
2. **Add print statements**: Insert `st.write("Debug:", value)` in Streamlit code
3. **Inspect session state**: Print `st.session_state` to see what's stored
4. **Check API logs**: Visit OpenAI console to see embedding/LLM call details
5. **Run tests with print**: `pytest tests/test_foo.py -v -s` (shows print output)

---

## Useful Links

| Resource | Purpose |
|----------|---------|
| [README.md](README.md) | Quick start, installation, running app |
| [docs/SRS.md](docs/SRS.md) | Product requirements & acceptance tests |
| [docs/ACCEPTANCE_TESTS.md](docs/ACCEPTANCE_TESTS.md) | End-to-end test scenarios (AT-*) |
| [docs/design/SDD.html](docs/design/SDD.html) | System design, architecture, diagrams (open in browser) |
| [docs/design/adr/](docs/design/adr/) | Reasoning for key technical decisions |
| [docs/design/openapi.yaml](docs/design/openapi.yaml) | API specification |
| [docs/design/schema.sql](docs/design/schema.sql) | Database schema reference (v2) |
| [docs/design/Component-Tests.md](docs/design/Component-Tests.md) | Component test specs (CT-*) with code examples |
| [agent.md](agent.md) | This file — coding conventions & project guidance |

---

## Key Takeaways

1. **Read the SRS first**: Every feature is driven by a requirement
2. **Check the design doc**: [SDD.html](docs/design/SDD.html) has diagrams and component responsibilities
3. **Look at acceptance tests**: [ACCEPTANCE_TESTS.md](docs/ACCEPTANCE_TESTS.md) shows expected behavior
4. **Write component tests**: Follow the pattern in [Component-Tests.md](docs/design/Component-Tests.md)
5. **Follow design principles**: Single Responsibility, Loose Coupling, Functional Core/Shell
6. **Test thoroughly**: Unit + component + integration + acceptance
7. **Document your work**: Update docstrings, README, or design docs as you go

---

**Questions?** Check the [FAQ section in README.md](README.md#troubleshooting) or see the [Open Questions section in SDD.html](docs/design/SDD.html#open-questions).

**Happy coding!** 🚀
