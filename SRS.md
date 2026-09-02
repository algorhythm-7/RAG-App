# Software Requirements Specification (SRS)
## "Know My Car" — Owner's Manual Q&A and Diagnostic Assistant

**Version**: 2.0
**Date**: 2026-08-25
**Status**: Draft — reverse-documented from the current implementation

---

## 1. Introduction

### Purpose
This document specifies the requirements for a Streamlit web application that lets a vehicle owner, technician, or fleet manager upload vehicle manuals and then (a) ask plain-language questions about their content, (b) describe a symptom and receive an AI-generated differential diagnosis grounded in the manuals, and (c) find nearby repair shops relevant to that diagnosis. This version supersedes v1.0 and reflects the application as actually implemented, including capabilities added since v1.0 (the symptom diagnosis pipeline and service-station lookup) and known gaps between originally intended and currently enforced behavior.

### Scope
- File upload and in-memory (session-only) storage of manuals (PDF, image, Excel, PowerPoint, video)
- Natural language question answering over uploaded manuals, with source attribution
- Symptom-driven differential diagnosis using a triage → hybrid retrieval → reasoning pipeline over the uploaded manuals
- Locating and mapping nearby repair shops relevant to a diagnosis, via a third-party mapping service
- Session-scoped document, query, and diagnosis history management
- Error handling that keeps the application usable and does not leak internal details
- Open access (no authentication required)

### Out of Scope (Not Implemented, Not Planned for This Version)
- User authentication and authorization
- Persistent document storage across sessions or across app restarts
- Multi-user collaboration or document sharing
- Analytics or usage tracking beyond structured application logs
- Mobile application (web-only)
- Document versioning or change history
- Integration with external vehicle databases or manufacturer APIs
- Automated appointment booking or telephony/calling of repair shops (explicitly excluded from the service-station feature)
- GPS/browser-based geolocation (location is entered as free-text address/city/ZIP only)
- Driving-time/ETA-based ranking of repair shops (straight-line distance is used instead)

### Definitions & Glossary
- **Owner's/Service Manual**: Technical documentation describing vehicle operation, maintenance, repair, and wiring.
- **Session**: A user's active engagement with the Streamlit app, held in server-side `st.session_state`; ends when the browser tab/process ends.
- **Document**: An uploaded file and its extracted `Passage`s (PDF, image, Excel, PowerPoint, video).
- **Passage**: A unit of extracted text (or a diagram + caption) with a section/page reference, used for retrieval.
- **Chunk**: A header-aware, size-bounded split of a passage with overlap, used by the diagnostic pipeline's retrieval index.
- **Query**: A natural language question about uploaded manuals (Query feature).
- **Symptom**: A free-text description of a vehicle problem submitted to the Diagnose feature.
- **Triage**: Stage 1 of the diagnostic pipeline — maps a symptom to candidate vehicle systems and targeted search queries.
- **Hybrid Retrieval**: Combining BM25 lexical search and vector semantic search results via Reciprocal Rank Fusion (RRF).
- **Reasoning**: Stage 2 of the diagnostic pipeline — produces a differential diagnosis from retrieved excerpts.
- **VLM Captioning**: Using a vision-language model to generate a text caption for a diagram/image extracted from a manual, so it becomes searchable.
- **MCP (Model Context Protocol)**: The JSON-RPC 2.0 protocol used to call tools on the hosted Mapbox MCP server for geocoding, place search, and static maps.
- **Feature**: A high-level capability that delivers value to users.
- **Use Case**: A concrete user-system interaction scenario.
- **Functional Requirement (FR)**: A specific, testable behavior the system must exhibit.
- **Non-Functional Requirement (NFR)**: A quality attribute the system must meet.

---

## 2. Product Vision

### Vision Statement
A vehicle owner, technician, or fleet manager can upload one or more vehicle manuals to a simple web application, ask natural-language questions to instantly get sourced answers, describe a symptom to get a manual-grounded differential diagnosis (with cited pages and diagrams), and then find a nearby repair shop suited to that diagnosis — all without manually searching hundreds of pages or leaving the app.

### Stakeholders
- **Vehicle Owners**: Primary users seeking quick answers and symptom triage for their vehicle.
- **Technicians / Fleet Managers**: Users diagnosing multiple vehicles and needing manual-grounded, citable reasoning.
- **Developers/Maintainers**: Engineers hosting, monitoring, and updating the application.
- **AI/ML Teams**: Responsible for the parsing, retrieval, and LLM/VLM pipelines.

### User Needs
| ID | Need | Rationale |
|----|------|-----------|
| need-upload-manual | As a user, I need to upload my vehicle manual(s) so that I can query and diagnose against their content. | Enables the core workflow. |
| need-plain-language-query | As a user, I need to ask questions in plain English and get a sourced answer so I don't have to navigate a complex manual. | Improves usability and reduces friction. |
| need-diagnose-symptom | As a user, I need to describe a symptom and get a differential diagnosis grounded in my manual (with citations and diagrams) so I understand likely causes before seeking repair. | Core diagnostic value proposition. |
| need-find-repair-shop | As a user, once I have a diagnosis, I need to find a nearby repair shop suited to the problem so I can act on the diagnosis without leaving the app. | Closes the loop from diagnosis to action. |
| need-error-feedback | As a user, I need clear feedback when an upload, query, or diagnosis fails so I know whether to retry, reformat, or rephrase. | Improves error transparency. |
| need-session-privacy | As a user, I need my uploaded documents and questions to stay private to my session so I don't accidentally expose sensitive information. | Ensures privacy; no server-side persistence. |
| need-review-history | As a user, I need to see my past queries and diagnoses within the session so I can refer back to them. | Supports iterative troubleshooting. |

---

## 3. Features

| ID | Feature Name | Implements Needs | Description |
|----|--------------|------------------|-------------|
| feat-upload | Multi-Format Document Upload & Parsing | need-upload-manual | Upload and parse manuals in PDF, image, Excel, PowerPoint, or video format; extracted content is embedded and indexed for both the Query and Diagnose features. |
| feat-query | Natural-Language Document Query | need-plain-language-query, need-review-history | Ask a question and get an LLM-generated answer with source passages, using semantic (FAISS) search. |
| feat-diagnose | Symptom Triage & Differential Diagnosis | need-diagnose-symptom, need-review-history | Describe a symptom; the system triages it, runs hybrid (BM25 + vector, RRF-fused) retrieval over the manuals, and reasons over the results to produce a differential diagnosis with citations and diagrams. |
| feat-locate | Nearby Service Station Lookup | need-find-repair-shop | Given a diagnosis and a user-entered location, find, rank, and map nearby repair shops via the Mapbox MCP server. |
| feat-session | Session Lifecycle & Management | need-session-privacy | In-memory session state for documents, indexes, and history; manual "Clear All Data" reset; no server-side persistence. |
| feat-error-handling | Error Handling & Feedback | need-error-feedback | Cross-cutting: exceptions in upload/query/diagnose/locate are caught, logged, and surfaced as plain-language messages without internal detail. |

---

## 4. Use Cases

### Actor List
- **User** (vehicle owner, technician, or fleet manager): Uploads manuals, asks questions, describes symptoms, and searches for repair shops.
- **System**: The Streamlit application and its parsing, retrieval, LLM/VLM, and mapping components.

### Use Case Summary

| ID | Use Case Name | Actor | Feature |
|----|---------------|-------|---------|
| uc-upload-document | Upload and Index a Manual | User | feat-upload |
| uc-query-documents | Ask a Question About Uploaded Manuals | User | feat-query |
| uc-diagnose-symptom | Diagnose a Symptom | User | feat-diagnose |
| uc-find-service-station | Find a Nearby Service Station | User | feat-locate |
| uc-manage-session | Manage Session Data | User | feat-session |

### Detailed Use Cases

#### uc-upload-document: Upload and Index a Manual

- **Actor**: User
- **Preconditions**: User is on the Upload page and has a file to upload (PDF, PNG/JPG/JPEG/GIF, XLS/XLSX, PPT/PPTX, or MP4/MOV/AVI/WebM).
- **Success Flow**:
  1. User selects a file and reviews the displayed filename and size.
  2. User clicks "Upload and Index".
  3. System validates the file's extension and size.
  4. System parses the file into passages using a format-specific parser (see FR-upload-*).
  5. System generates embeddings for the document's passages.
  6. System adds the document to the session and rebuilds the semantic (FAISS) index and the hybrid retrieval index (header-aware chunks, BM25, vector store) across all successfully parsed documents in the session.
  7. System displays a success message with the filename and the number of extracted passages.
- **Alternate Flows**:
  - **A1 — Unsupported format**: Extension not in the supported list → error "File format not supported. Please upload PDF, image, Excel, PowerPoint, or video files."; nothing is added to the session.
  - **A2 — File too large**: File exceeds 50 MB → error "File is too large (max 50 MB). Please upload a smaller file."; nothing is added to the session.
  - **A3 — Parse failure**: The format-specific parser raises an error (e.g., corrupted PDF, image with no OCR-detectable text, empty spreadsheet/presentation) → the parse error message is shown to the user and the document is **not** added to the session or indexes.
  - **A4 — PDF primary pipeline failure**: If the primary PDF pipeline (see FR-upload-pdf-primary) throws, the system falls back to a legacy PDF parser before reporting failure (see FR-upload-pdf-fallback).
- **Postconditions**: On success, the document's passages are queryable (feat-query) and retrievable by the diagnostic pipeline (feat-diagnose). On failure, session state is unchanged.

#### uc-query-documents: Ask a Question About Uploaded Manuals

- **Actor**: User
- **Preconditions**: At least one document has been successfully uploaded; user is on the Query page.
- **Success Flow**:
  1. User enters a natural-language question and clicks "Search".
  2. System embeds the question and searches the session's FAISS index for the most similar passages.
  3. System discards results below the relevance threshold.
  4. System sends the remaining passages and the question to an LLM to generate an answer.
  5. System displays the answer, the response time, an aggregate confidence score, and the source passages (grouped by document/section, truncated for display).
  6. The query and its outcome are appended to the session's query history (most recent 5 shown).
- **Alternate Flows**:
  - **A1 — No relevant passages**: All FAISS results fall below the relevance threshold (or the index is empty) → "No relevant information found. Please try rephrasing your question or upload additional documents." is shown; no LLM call is made.
  - **A2 — Answer generation fails**: The LLM call raises an exception → a generic internal-error message is shown; no partial answer is displayed.
  - **A3 — No documents uploaded**: Query page shows a warning and the query form is not usable until a document is uploaded.
- **Postconditions**: The answer (or error) is displayed; the query is recorded in session history.

#### uc-diagnose-symptom: Diagnose a Symptom

- **Actor**: User
- **Preconditions**: At least one document has been successfully uploaded; user is on the Diagnose page.
- **Success Flow**:
  1. User describes the symptom in free text and clicks "Diagnose".
  2. System (Stage 1 — Triage) sends the symptom to a triage LLM, which returns candidate vehicle systems and 2–4 targeted search queries.
  3. System (Hybrid Retrieval) runs each search query against both the BM25 index and the vector store, fuses the two ranked lists per query via Reciprocal Rank Fusion, and merges across queries into a single top-N set of passages.
  4. System (Stage 2 — Reasoning) sends the symptom and the retrieved excerpts to a reasoning LLM, which returns a reasoning trace, ordered diagnostic steps, a ranked differential diagnosis (cause/likelihood/evidence), and cited manual pages.
  5. System displays the triage systems/search queries, the reasoning trace, the diagnostic steps, the differential diagnosis, cited pages, any diagram passages among the retrieved results, a confidence score, and the response time.
  6. The diagnosis becomes the session's "last diagnosis" (enabling uc-find-service-station) and is appended to the diagnosis history.
- **Alternate Flows**:
  - **A1 — Empty symptom text**: User clicks "Diagnose" with no text entered → warning "Please describe the symptom."; pipeline does not run.
  - **A2 — No documents uploaded**: Diagnose page shows a warning and the symptom form is not usable.
  - **A3 — Triage LLM fails**: The system falls back to using the raw symptom text as the sole search query (with no identified systems) and continues the pipeline.
  - **A4 — Vector search fails for a query**: The failure is logged and only BM25 results for that query are used; the pipeline continues without surfacing an error to the user.
  - **A5 — No passages retrieved**: The reasoning stage is skipped; the result shows a reasoning trace stating no relevant passages were found, with no steps or differential.
  - **A6 — Reasoning LLM fails**: The result shows an internal-error message in place of the reasoning trace; any diagram passages already retrieved are still shown; confidence is 0.
- **Postconditions**: A `DiagnosisResult` is displayed and stored as the session's last diagnosis; diagnosis history grows by one entry.

#### uc-find-service-station: Find a Nearby Service Station

- **Actor**: User
- **Preconditions**: A diagnosis has been produced earlier in the session (uc-diagnose-symptom); user is on the Diagnose page's "Find Nearest Service Station" section.
- **Success Flow**:
  1. User enters a location (address, city, or ZIP) and clicks "Find nearest station".
  2. System asks a location LLM to choose a Mapbox search category and a free-text fallback query based on the diagnosis's likely causes.
  3. System geocodes the entered location via the Mapbox MCP server.
  4. System searches for nearby stations by category; if that returns nothing, it retries with the free-text fallback query.
  5. System ranks candidate stations by straight-line distance from the geocoded location and keeps the closest 5.
  6. System best-effort enriches each station with phone number and website.
  7. System renders a static map image with the user's location and the station locations as markers.
  8. System displays the map and the ranked station list (name, address, distance in miles, phone, website where available).
- **Alternate Flows**:
  - **A1 — No diagnosis yet**: Clicking before any diagnosis has been run → error "Run a diagnosis first."
  - **A2 — Empty location**: User clicks "Find nearest station" with no text entered → warning "Please enter a location."
  - **A3 — Geocoding fails or returns nothing**: Error message shown ("Could not look up that location: …" or "No location found for that address."); no station search is attempted.
  - **A4 — Station search fails**: Both the category search and the fallback text search error → "Station search failed: …".
  - **A5 — No stations found**: Category and fallback searches both succeed but return zero results → "No nearby service stations found." (informational, not an error).
  - **A6 — Map rendering fails**: Logged and treated as non-fatal; the station list is still shown without a map image.
  - **A7 — Per-station enrichment fails**: Logged and treated as non-fatal; that station's phone/website are simply left blank.
- **Postconditions**: The result (station list, map, or error/info message) is stored as the session's last location result and displayed until replaced or the session is cleared.

#### uc-manage-session: Manage Session Data

- **Actor**: User (session is also auto-initialized by the System on first page load)
- **Preconditions**: The application is loaded in a browser.
- **Success Flow**:
  1. On first load, the system creates a session ID and empty document, index, and history state.
  2. The sidebar continuously shows the document count and elapsed session duration.
  3. The Session page shows document count, query count, session duration, and a per-document list (parse status, passage count).
  4. User clicks "Clear All Data" to reset all documents, indexes, and history to empty.
- **Alternate Flows**:
  - **A1 — Browser/tab closed**: All in-memory session state is discarded implicitly; nothing is written to disk beforehand.
- **Postconditions**: After a manual clear, the session is empty and ready for new uploads, equivalent to a fresh session.

---

## 5. Functional Requirements

### feat-upload: Multi-Format Document Upload & Parsing
- **fr-upload-accepted-formats**: The system shall accept files with extensions `.pdf`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.mp4`, `.mov`, `.avi`, `.webm`. _(uc-upload-document)_
- **fr-upload-reject-unsupported-format**: The system shall reject any other extension with the message "File format not supported. Please upload PDF, image, Excel, PowerPoint, or video files." _(uc-upload-document)_
- **fr-upload-reject-oversized-file**: The system shall reject files larger than 50 MB with the message "File is too large (max 50 MB). Please upload a smaller file." _(uc-upload-document)_
- **fr-upload-pdf-primary**: For PDF files, the system shall extract per-page markdown text and embedded diagram images, and shall caption each diagram with a vision-language model so its content becomes searchable text. _(uc-upload-document)_
- **fr-upload-pdf-fallback**: If the primary PDF pipeline raises an exception, the system shall fall back to a legacy parser that extracts page text (preferring a table-aware library, falling back to a basic PDF text extractor) and OCRs embedded images (preferring a high-accuracy OCR engine, falling back to a general-purpose OCR engine) before reporting a parse failure. _(uc-upload-document)_
- **fr-upload-image-ocr**: For image files, the system shall run OCR over the full image and extract all detected text as a single passage; if no text is detected, the upload shall fail with the parse-failure message. _(uc-upload-document)_
- **fr-upload-excel-parse**: For Excel files, the system shall extract one passage per worksheet containing that sheet's tabular content. _(uc-upload-document)_
- **fr-upload-powerpoint-parse**: For PowerPoint files, the system shall extract one passage per slide containing that slide's text shapes. _(uc-upload-document)_
- **fr-upload-video-stub**: For video files, the system shall accept the upload and record a single placeholder passage noting that speech-to-text transcription is not yet implemented; no audio/caption content is extracted. _(uc-upload-document)_
- **fr-upload-parse-failure-message**: If parsing fails for any format, the system shall display "Unable to parse this file. Please check the file integrity and try again. If the problem persists, try a different format." and shall not add the document to the session. _(uc-upload-document)_
- **fr-upload-reindex-on-success**: On a successful parse, the system shall generate embeddings for the document's passages, then rebuild both the semantic (FAISS) index and the hybrid retrieval index (chunks, BM25, vector store) from all currently successfully-parsed documents in the session. _(uc-upload-document)_
- **fr-upload-success-feedback**: On success, the system shall display the uploaded filename and the number of extracted passages. _(uc-upload-document)_

### feat-query: Natural-Language Document Query
- **fr-query-input**: The system shall accept a natural-language question via a text input field. _(uc-query-documents)_
- **fr-query-semantic-search**: The system shall embed the question and retrieve the most similar passages from the session's FAISS index, discarding any result below the configured relevance threshold. _(uc-query-documents)_
- **fr-query-no-results-message**: If no passages meet the relevance threshold, the system shall display "No relevant information found. Please try rephrasing your question or upload additional documents." and shall not call the answer-generation LLM. _(uc-query-documents)_
- **fr-query-answer-generation**: If relevant passages are found, the system shall send the question and the retrieved passages to an LLM and display the generated answer. _(uc-query-documents)_
- **fr-query-source-attribution**: The system shall display, for each answer, the contributing document and section/page identifiers and an excerpt of the source passage. _(uc-query-documents)_
- **fr-query-error-message**: If answer generation fails or times out, the system shall display a plain-language error message and shall not display a partial or fabricated answer. _(uc-query-documents)_
- **fr-query-history**: The system shall record each submitted query (text, timestamp, outcome status) in the session and display the most recent entries. _(uc-query-documents)_

### feat-diagnose: Symptom Triage & Differential Diagnosis
- **fr-diagnose-triage**: The system shall send the user's symptom description to a triage LLM and obtain candidate vehicle systems and 2–4 targeted search queries; on failure, it shall fall back to using the raw symptom text as the sole search query. _(uc-diagnose-symptom)_
- **fr-diagnose-hybrid-retrieval**: For each search query, the system shall retrieve candidates from both a lexical (BM25) index and a vector (semantic) index and fuse the two ranked lists using Reciprocal Rank Fusion; results across all search queries shall be merged into a single ranked set. _(uc-diagnose-symptom)_
- **fr-diagnose-reasoning**: The system shall send the symptom and the retrieved excerpts to a reasoning LLM, constrained to using only the provided excerpts, and obtain a reasoning trace, ordered diagnostic steps, a ranked differential diagnosis (cause, likelihood, evidence), and cited manual pages. _(uc-diagnose-symptom)_
- **fr-diagnose-surface-diagrams**: Any retrieved passage that represents a diagram (with its captured image) shall be displayed alongside the diagnosis. _(uc-diagnose-symptom)_
- **fr-diagnose-empty-input-guard**: The system shall reject an empty symptom description with a warning and shall not run the pipeline. _(uc-diagnose-symptom)_
- **fr-diagnose-no-docs-guard**: The system shall prevent starting a diagnosis when no documents have been uploaded. _(uc-diagnose-symptom)_
- **fr-diagnose-empty-retrieval-handling**: If hybrid retrieval returns no passages, the system shall skip the reasoning call and display a message that no relevant passages were retrieved, with no diagnostic steps or differential. _(uc-diagnose-symptom)_
- **fr-diagnose-reasoning-failure-handling**: If the reasoning LLM call fails, the system shall display a plain-language error in place of the reasoning trace while still showing any diagrams already retrieved. _(uc-diagnose-symptom)_
- **fr-diagnose-history**: The system shall record each completed diagnosis in the session's diagnosis history and retain the most recent diagnosis as the active context for the service-station lookup. _(uc-diagnose-symptom)_

### feat-locate: Nearby Service Station Lookup
- **fr-locate-require-diagnosis**: The system shall require that a diagnosis exists in the session before a station search can run, and shall show an actionable error otherwise. _(uc-find-service-station)_
- **fr-locate-geocode-address**: The system shall geocode the user-entered location text via the mapping service and report an error if it cannot be geocoded. _(uc-find-service-station)_
- **fr-locate-category-search-with-fallback**: The system shall determine a repair-shop search category and a free-text fallback query from the diagnosis's likely causes, search by category first, and use the fallback free-text search if the category search returns no results. _(uc-find-service-station)_
- **fr-locate-rank-by-distance**: The system shall rank candidate stations by straight-line distance from the geocoded location and present the closest 5. _(uc-find-service-station)_
- **fr-locate-enrich-details**: The system shall attempt to enrich each candidate station with a phone number and website; a failure to do so for one station shall not block displaying the others. _(uc-find-service-station)_
- **fr-locate-render-map**: The system shall attempt to render a static map showing the user's location and the candidate stations; a failure to render the map shall not block displaying the station list. _(uc-find-service-station)_
- **fr-locate-error-messages**: The system shall display a distinct, plain-language message for each of: missing diagnosis, empty location, geocoding failure, no location found, station-search failure, and zero stations found. _(uc-find-service-station)_

### feat-session: Session Lifecycle & Management
- **fr-session-auto-init**: The system shall initialize an empty session (ID, documents, indexes, histories) automatically on first use, without requiring sign-in. _(uc-manage-session)_
- **fr-session-in-memory-only**: The system shall hold all documents, indexes, and history exclusively in server-side, per-session memory; nothing shall be written to a database or shared disk location. _(uc-manage-session)_
- **fr-session-stats-display**: The system shall display, at all times, the current document count and elapsed session duration, and, on the Session page, the query count and a per-document parse-status list. _(uc-manage-session)_
- **fr-session-manual-clear**: The system shall let the user reset all documents, indexes, and history for the current session on demand. _(uc-manage-session)_

### feat-error-handling: Error Handling & Feedback (cross-cutting)
- **fr-error-no-crash**: An exception raised during upload, query, diagnosis, or station lookup shall be caught and shall not terminate the application session; the user shall be able to continue using the app. _(uc-upload-document, uc-query-documents, uc-diagnose-symptom, uc-find-service-station)_
- **fr-error-plain-language-messages**: Every user-facing error message shall be plain language and shall not include stack traces, internal exception class names, library names/versions, file paths, or API keys/secrets. _(uc-upload-document, uc-query-documents, uc-diagnose-symptom, uc-find-service-station)_
- **fr-error-logging**: Errors and key pipeline events (uploads, parses, retrieval, reasoning, station lookups) shall be logged with identifying metadata (e.g., filename, counts, timings) for debugging, without logging full document or answer content. _(uc-upload-document, uc-query-documents, uc-diagnose-symptom, uc-find-service-station)_

---

## 6. Non-Functional Requirements

- **nfr-file-size-limit**: The system shall enforce a maximum individual file size of 50 MB at upload time.
- **nfr-llm-call-timeout**: Every LLM call (answer generation, triage, reasoning, location term selection) and every Mapbox MCP call shall use a bounded timeout (30 seconds by default) rather than blocking indefinitely.
- **nfr-relevance-filtering**: The Query feature shall discard FAISS results below a configured similarity threshold before answer generation, so low-confidence passages are not presented as sourced evidence.
- **nfr-retrieval-fusion-determinism**: Hybrid retrieval fusion (RRF) shall use a fixed, configurable constant so that ranking behavior is deterministic and tunable without code changes.
- **nfr-chunking-bounds**: Header-aware chunking used by the diagnostic pipeline shall bound chunk size and carry a fixed trailing overlap between sub-chunks of the same section, so retrieval does not lose context at chunk boundaries.
- **nfr-secret-handling**: API keys and access tokens (LLM provider key, mapping service token) shall be read from Streamlit secrets or environment variables and shall never be displayed in the UI or written to logs.
- **nfr-no-persistence**: No uploaded file content, extracted passage text, or generated answer/diagnosis shall be written to disk or an external database; all such data shall live only in the Streamlit session's in-memory state.
- **nfr-graceful-degradation**: A failure in a non-essential sub-step (per-query vector search during hybrid retrieval, per-station detail enrichment, static map rendering) shall degrade the result rather than abort the overall operation.
- **nfr-modularity**: Parsing, embedding, indexing, retrieval, LLM orchestration, and mapping integration shall each be implemented as separate, independently testable components under `src/components/`.
- **nfr-test-coverage**: Each component listed in nfr-modularity shall have at least one corresponding automated test module under `tests/`.
- **nfr-browser-based**: The application shall be usable from recent desktop versions of Chrome, Firefox, Safari, and Edge, requiring no client installation beyond a browser.

---

## 7. Future Considerations (Explicitly Deferred)

The following are discussed or scaffolded in the codebase (constants/fields exist) but are **not enforced or not implemented** today, and are candidates for a future version rather than oversights:

1. **Duplicate-file detection**: A file hash is computed at validation time, but no check currently prevents the same file from being uploaded and re-indexed twice.
2. **Per-session document limit**: A maximum-documents-per-session constant exists but is not currently enforced anywhere in the upload flow.
3. **Session auto-timeout**: A session-timeout constant exists but there is no server-side timer; sessions only end when the browser/process ends or the user clicks "Clear All Data".
4. **Video transcription**: Video uploads currently produce a placeholder passage only; speech-to-text transcription is not implemented.
5. **Query-history replay**: Past queries are listed but cannot currently be re-run or expanded to show their original answer.
6. **User Authentication & Authorization**: Login/logout, per-user document libraries, role-based access.
7. **Persistent Storage**: Saving documents, queries, and diagnoses across sessions or restarts.
8. **Telephony/booking integration**: Calling or booking an appointment with a found repair shop — explicitly excluded from feat-locate per product decision.
9. **GPS/browser geolocation and ETA-based ranking**: feat-locate deliberately uses manual address entry and straight-line distance instead.
10. **Mobile App**: iOS/Android native applications.
11. **External Integrations**: Vehicle manufacturer databases, maintenance scheduling systems, fleet management platforms.
12. **Analytics**: Usage tracking or metrics beyond structured application logs.
13. **Custom/fine-tuned models**: The diagnostic and captioning models are general-purpose LLMs/VLMs, not automotive-fine-tuned.

---

## 8. Traceability

### Requirements Flow

```
User Needs (need-*)
  ↓
Features (feat-*)
  ↓
Use Cases (uc-*)
  ↓
Functional Requirements (fr-*) & Non-Functional Requirements (nfr-*)
  ↓
Acceptance Tests (at-*) [See ACCEPTANCE_TESTS.md]
```

### Mapping Summary

- **need-upload-manual** → **feat-upload** → **uc-upload-document** → `fr-upload-*`
- **need-plain-language-query**, **need-review-history** → **feat-query** → **uc-query-documents** → `fr-query-*`
- **need-diagnose-symptom**, **need-review-history** → **feat-diagnose** → **uc-diagnose-symptom** → `fr-diagnose-*`
- **need-find-repair-shop** → **feat-locate** → **uc-find-service-station** → `fr-locate-*`
- **need-session-privacy** → **feat-session** → **uc-manage-session** → `fr-session-*`
- **need-error-feedback** → **feat-error-handling** → (cross-cutting alternate flows of all use cases) → `fr-error-*`

### Cross-References

- Every functional requirement above references the use case(s) it implements.
- Non-functional requirements apply across features rather than to a single use case.
- Acceptance tests (in [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md)) verify each use case's success and alternate flows and the requirements they realize.

---

## End of SRS

**Document Approval & Review Status**:
- [ ] Product Owner Review
- [ ] Development Team Review
- [ ] QA Lead Review
