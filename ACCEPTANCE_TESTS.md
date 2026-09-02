# Acceptance Tests (AT)
## "Know My Car" — Owner's Manual Q&A and Diagnostic Assistant

**Version**: 2.0
**Date**: 2026-08-25
**Status**: Draft — reverse-documented from the current implementation

This document provides testable Given/When/Then scenarios that verify each use case and functional requirement from [SRS.md](SRS.md).

---

## at-upload-*: Upload and Index a Manual (uc-upload-document)

| AT ID | Use Case | Requirement(s) | Given | When | Then |
| --- | --- | --- | --- | --- | --- |
| at-upload-pdf-success | uc-upload-document | fr-upload-accepted-formats, fr-upload-pdf-primary, fr-upload-reindex-on-success, fr-upload-success-feedback | A valid PDF manual (< 50 MB) | User uploads it and clicks "Upload and Index" | Per-page text and diagram captions are extracted; a success message shows the filename and passage count; the document is queryable |
| at-upload-image-success | uc-upload-document | fr-upload-accepted-formats, fr-upload-image-ocr | An image file (PNG/JPG/JPEG/GIF) containing visible text | User uploads it | OCR extracts the visible text as a single passage; success message is shown |
| at-upload-image-no-text | uc-upload-document | fr-upload-image-ocr, fr-upload-parse-failure-message | An image with no OCR-detectable text | User uploads it | Upload fails with "Unable to parse this file…"; document is not added to the session |
| at-upload-excel-success | uc-upload-document | fr-upload-accepted-formats, fr-upload-excel-parse | An Excel file with one or more sheets | User uploads it | One passage per sheet is extracted; success message is shown |
| at-upload-powerpoint-success | uc-upload-document | fr-upload-accepted-formats, fr-upload-powerpoint-parse | A PowerPoint file with text on slides | User uploads it | One passage per slide is extracted; success message is shown |
| at-upload-video-stub | uc-upload-document | fr-upload-video-stub | A video file (MP4/MOV/AVI/WebM) | User uploads it | Upload succeeds with a single placeholder passage noting transcription is not implemented; no audio content is extracted |
| at-upload-unsupported-format | uc-upload-document (A1) | fr-upload-reject-unsupported-format | A file with an unsupported extension (e.g., ".docx", ".zip") | User attempts to upload it | Upload is rejected with "File format not supported. Please upload PDF, image, Excel, PowerPoint, or video files."; nothing is added to the session |
| at-upload-oversized-file | uc-upload-document (A2) | fr-upload-reject-oversized-file | A file larger than 50 MB | User attempts to upload it | Upload is rejected with "File is too large (max 50 MB). Please upload a smaller file." |
| at-upload-corrupted-pdf | uc-upload-document (A3, A4) | fr-upload-pdf-fallback, fr-upload-parse-failure-message | A corrupted or malformed PDF | System attempts the primary PDF pipeline, then the legacy fallback | Both fail; "Unable to parse this file…" is shown; document is not added to the session |
| at-upload-reindex-across-documents | uc-upload-document | fr-upload-reindex-on-success | One document already uploaded successfully | User uploads a second valid document | Both the FAISS index and the hybrid (BM25 + vector) index are rebuilt to include passages from both documents |
| at-upload-no-dedup-gap | uc-upload-document | (nfr — documents known gap) | A file already uploaded successfully in this session | User uploads the exact same file again | The file is parsed and indexed again (no duplicate-detection currently prevents this) — confirms the documented gap, not a defect |

---

## at-query-*: Ask a Question About Uploaded Manuals (uc-query-documents)

| AT ID | Use Case | Requirement(s) | Given | When | Then |
| --- | --- | --- | --- | --- | --- |
| at-query-relevant-answer | uc-query-documents | fr-query-input, fr-query-semantic-search, fr-query-answer-generation, fr-query-source-attribution | A manual with a tire-pressure section is uploaded | User asks "What's the recommended tire pressure?" | An answer is generated and displayed with source document/section and response time/confidence |
| at-query-multi-document | uc-query-documents | fr-query-semantic-search | Two manuals are uploaded, each with tire-pressure content | User asks "What's the tire pressure?" | Retrieval draws from the combined FAISS index across both documents; sources reflect the contributing document(s) |
| at-query-no-relevant-passages | uc-query-documents (A1) | fr-query-no-results-message | A manual is uploaded with no content related to the question | User asks "How do I bake a cake?" | "No relevant information found. Please try rephrasing your question or upload additional documents." is shown; no LLM call is made |
| at-query-answer-generation-failure | uc-query-documents (A2) | fr-query-error-message | Relevant passages are found | The answer-generation LLM call raises an exception | A generic error message is shown; no partial/fabricated answer is displayed |
| at-query-no-documents | uc-query-documents (A3) | fr-diagnose-no-docs-guard (analogous session guard) | No documents uploaded yet | User navigates to the Query page | A warning is shown and the query form is not usable |
| at-query-history-recorded | uc-query-documents | fr-query-history | One or more queries have been submitted | User views the Query page | The most recent queries (up to 5) are listed with their text |

---

## at-diagnose-*: Diagnose a Symptom (uc-diagnose-symptom)

| AT ID | Use Case | Requirement(s) | Given | When | Then |
| --- | --- | --- | --- | --- | --- |
| at-diagnose-happy-path | uc-diagnose-symptom | fr-diagnose-triage, fr-diagnose-hybrid-retrieval, fr-diagnose-reasoning, fr-diagnose-history | A service manual is uploaded | User describes a symptom (e.g., "AC blows warm air at highway speed") and clicks "Diagnose" | Triage identifies systems/search queries; hybrid retrieval returns fused passages; reasoning produces steps, differential diagnosis, and cited pages; result is added to diagnosis history and becomes the active diagnosis |
| at-diagnose-diagrams-surfaced | uc-diagnose-symptom | fr-diagnose-surface-diagrams | A manual with an extractable diagram relevant to the symptom is uploaded | A diagnosis run retrieves that diagram passage | The diagram image and its section label are displayed alongside the diagnosis |
| at-diagnose-empty-symptom | uc-diagnose-symptom (A1) | fr-diagnose-empty-input-guard | User is on the Diagnose page | User clicks "Diagnose" with no symptom text entered | Warning "Please describe the symptom." is shown; pipeline does not run |
| at-diagnose-no-documents | uc-diagnose-symptom (A2) | fr-diagnose-no-docs-guard | No documents uploaded | User navigates to the Diagnose page | A warning is shown; the symptom form is not usable |
| at-diagnose-triage-failure-fallback | uc-diagnose-symptom (A3) | fr-diagnose-triage | A manual is uploaded | The triage LLM call fails | The pipeline falls back to using the raw symptom text as the sole search query and continues to retrieval and reasoning |
| at-diagnose-vector-search-partial-failure | uc-diagnose-symptom (A4) | fr-diagnose-hybrid-retrieval, nfr-graceful-degradation | A manual is uploaded | The vector store search fails for one search query | The failure is logged; BM25 results for that query are still used; the pipeline completes without a user-visible error |
| at-diagnose-empty-retrieval | uc-diagnose-symptom (A5) | fr-diagnose-empty-retrieval-handling | A manual is uploaded but contains nothing related to the symptom | Hybrid retrieval returns zero passages | Reasoning is skipped; a message states no relevant passages were retrieved; steps/differential are empty |
| at-diagnose-reasoning-failure | uc-diagnose-symptom (A6) | fr-diagnose-reasoning-failure-handling | Passages were retrieved | The reasoning LLM call fails | A plain-language error is shown in place of the reasoning trace; any already-retrieved diagrams are still shown; confidence is 0 |

---

## at-locate-*: Find a Nearby Service Station (uc-find-service-station)

| AT ID | Use Case | Requirement(s) | Given | When | Then |
| --- | --- | --- | --- | --- | --- |
| at-locate-happy-path | uc-find-service-station | fr-locate-geocode-address, fr-locate-category-search-with-fallback, fr-locate-rank-by-distance, fr-locate-enrich-details, fr-locate-render-map | A diagnosis has been produced this session | User enters a valid address and clicks "Find nearest station" | Address is geocoded; up to 5 stations are found, ranked by straight-line distance, enriched with phone/website where available, and shown with a static map |
| at-locate-no-diagnosis-yet | uc-find-service-station (A1) | fr-locate-require-diagnosis | No diagnosis has been run this session | User attempts to search for a station | Error "Run a diagnosis first." is shown |
| at-locate-empty-address | uc-find-service-station (A2) | fr-locate-error-messages | A diagnosis exists | User clicks "Find nearest station" with no address entered | Warning "Please enter a location." is shown |
| at-locate-geocode-failure | uc-find-service-station (A3) | fr-locate-geocode-address, fr-locate-error-messages | A diagnosis exists | The mapping service fails to geocode the entered address, or returns no result | An error message identifying the geocoding failure ("Could not look up that location: …" or "No location found for that address.") is shown |
| at-locate-station-search-failure | uc-find-service-station (A4) | fr-locate-category-search-with-fallback, fr-locate-error-messages | Address geocodes successfully | Both the category search and the fallback text search fail | "Station search failed: …" is shown |
| at-locate-zero-stations | uc-find-service-station (A5) | fr-locate-error-messages | Address geocodes successfully | Category and fallback searches both succeed but return no stations | "No nearby service stations found." is shown (informational, not an error) |
| at-locate-map-render-failure | uc-find-service-station (A6) | fr-locate-render-map, nfr-graceful-degradation | Stations are found | Static map rendering fails | The station list is still displayed without a map image |
| at-locate-enrichment-failure | uc-find-service-station (A7) | fr-locate-enrich-details, nfr-graceful-degradation | Stations are found | Phone/website enrichment fails for one station | That station is shown with blank phone/website; other stations are unaffected |

---

## at-session-*: Manage Session Data (uc-manage-session)

| AT ID | Use Case | Requirement(s) | Given | When | Then |
| --- | --- | --- | --- | --- | --- |
| at-session-auto-init | uc-manage-session | fr-session-auto-init | A user opens the application for the first time in a browser session | The app loads | A new session ID, empty document/index state, and empty histories are created automatically, with no sign-in step |
| at-session-stats-visible | uc-manage-session | fr-session-stats-display | An active session with documents and queries | User views the sidebar and the Session page | Document count and session duration are shown in the sidebar; document count, query count, session duration, and per-document parse status are shown on the Session page |
| at-session-manual-clear | uc-manage-session | fr-session-manual-clear | An active session with uploaded documents, query history, and diagnosis history | User clicks "Clear All Data" | All documents, indexes, and histories are reset to empty; a confirmation is shown |
| at-session-isolated-across-sessions | uc-manage-session (A1) | fr-session-in-memory-only | A user uploads a file in one browser session | The user opens the application in a separate/new browser session | The new session starts empty; the first session's data is not visible |
| at-session-no-disk-persistence | uc-manage-session | fr-session-in-memory-only, nfr-no-persistence | A file has been uploaded and queried | The session ends (browser/tab closed) | No document content, passage text, or generated answers/diagnoses remain accessible; nothing was written to disk or an external database |

---

## Non-Functional Verification

| AT ID | Requirement(s) | Given | When | Then |
| --- | --- | --- | --- | --- |
| at-nfr-file-size-limit | nfr-file-size-limit | A file larger than 50 MB | Upload attempted | Rejected before parsing begins |
| at-nfr-llm-timeout | nfr-llm-call-timeout | An LLM or Mapbox MCP call that would otherwise hang | The call is made | The call is bounded by the configured timeout rather than blocking indefinitely |
| at-nfr-relevance-filtering | nfr-relevance-filtering | FAISS search results below the configured similarity threshold | A query is run | Those results are excluded from the passages sent to answer generation |
| at-nfr-secret-handling | nfr-secret-handling | The application is running with configured API keys/tokens | Any error message or log line is produced | No key/token value appears in the UI or logs |
| at-nfr-graceful-degradation | nfr-graceful-degradation | A non-essential sub-step fails (vector search for one query, station enrichment, map rendering) | The overall operation (diagnosis or station lookup) runs | The operation still completes and returns a degraded-but-usable result |

---

## Traceability to Requirements

| Acceptance Test Group | Use Case | Functional Requirements |
| --- | --- | --- |
| at-upload-* | uc-upload-document | fr-upload-* |
| at-query-* | uc-query-documents | fr-query-* |
| at-diagnose-* | uc-diagnose-symptom | fr-diagnose-* |
| at-locate-* | uc-find-service-station | fr-locate-* |
| at-session-* | uc-manage-session | fr-session-* |
| Non-Functional Verification | (cross-cutting) | nfr-* |
| AT-06.1, AT-06.2 | All | All FRs | All NFRs |

---

## Notes for QA & Development

1. **Test Environment**: These tests should run on a local development instance (localhost) and on a staged/QA deployment.
2. **Automation**: Tests AT-01.1 to AT-05.3 can be automated using Selenium, Playwright, or similar tools. Tests AT-06.1 and AT-06.2 are good candidates for manual or BDD-style automation (e.g., with Cucumber/Behave).
3. **Performance Baselines**: NFR-01.1 and NFR-01.2 timings should be captured on a reference environment (e.g., a specific VM or cloud instance) to ensure consistent measurement.
4. **File Test Data**: Create a small library of test files:
   - 5-page PDF manual
   - 100-page PDF manual
   - Sample image (scanned manual page)
   - Sample Excel file with maintenance data
   - Sample PowerPoint presentation
   - (Optionally) Sample video with captions
5. **Edge Cases**: Additional tests to consider for future versions:
   - Very large files (close to 50 MB limit)
   - Files with unusual encoding or corrupted metadata
   - Queries with special characters or non-English languages
   - Concurrent query submissions from the same user
6. **Logging**: Ensure all errors and key events are logged for debugging and auditing.

---

**Test Execution Status**:
- [ ] AT-01.1 through AT-06.2 Planned
- [ ] Tests Implemented (Automated/Manual)
- [ ] Tests Executed
- [ ] All Tests Passed

---

## End of Acceptance Tests Document
