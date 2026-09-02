# The Definitive Beginner's Guide to Retrieval-Augmented Generation (RAG) & System Implementation

Welcome! This document is designed to take you from a complete beginner to having a deep, architectural, and code-level understanding of **Retrieval-Augmented Generation (RAG)**. 

Using this repository (**Know My Car / Vehicle Owner's Manual Diagnostic App**) as our reference implementation, you will learn both the **theoretical principles** of RAG and the **exact line-by-line implementation** techniques used to build a production-grade, multimodal, hybrid RAG application.

---

## Table of Contents
1. [What is RAG and Why Does It Exist?](#1-what-is-rag-and-why-does-it-exist)
   - [Parametric vs. Non-Parametric Memory](#parametric-vs-non-parametric-memory)
   - [The Core Problems RAG Solves](#the-core-problems-rag-solves)
2. [The Spectrum of RAG Architectures](#2-the-spectrum-of-rag-architectures)
   - [Naive RAG (Baseline)](#naive-rag-baseline)
   - [Advanced RAG (Pre-retrieval & Post-retrieval Optimizations)](#advanced-rag-pre-retrieval--post-retrieval-optimizations)
   - [Modular / Agentic RAG (Multi-Stage Reasoning & Tool Calling)](#modular--agentic-rag-multi-stage-reasoning--tool-calling)
3. [Deep Dive into Core RAG Concepts & Nuances](#3-deep-dive-into-core-rag-concepts--nuances)
   - [Ingestion & Document Parsing](#ingestion--document-parsing)
   - [Chunking Strategies (Fixed, Semantic, Header-Aware with Overlap)](#chunking-strategies)
   - [Embeddings & Representation (Dense vs. Sparse, Multimodal CLIP)](#embeddings--representation)
   - [Lexical Search (BM25) vs. Semantic Search (Vector)](#lexical-search-bm25-vs-semantic-search-vector)
   - [Hybrid Retrieval & Reciprocal Rank Fusion (RRF)](#hybrid-retrieval--reciprocal-rank-fusion-rrf)
   - [Query Triage, Transformation & Expansion](#query-triage-transformation--expansion)
   - [Context Synthesis, Grounding & Source Attribution](#context-synthesis-grounding--source-attribution)
   - [Tool Use via MCP (Model Context Protocol)](#tool-use-via-mcp-model-context-protocol)
4. [How This Application Implements RAG: End-to-End Code Walkthrough](#4-how-this-application-implements-rag-end-to-end-code-walkthrough)
   - [Architecture Diagram](#architecture-diagram)
   - [Step 1: Document Parsing & OCR Pipeline (`document_parser.py`, `pdf_ingester.py`)](#step-1-document-parsing--ocr-pipeline)
   - [Step 2: Vision-Language Model Diagram Captioning (`vlm_captioner.py`)](#step-2-vision-language-model-diagram-captioning)
   - [Step 3: Header-Aware Chunking with Overlap (`chunker.py`)](#step-3-header-aware-chunking-with-overlap)
   - [Step 4: Lexical BM25 & Semantic ChromaDB Indexing (`bm25_index.py`, `vector_store.py`, `embedding_generator.py`)](#step-4-lexical-bm25--semantic-chromadb-indexing)
   - [Step 5: Stage 1 Symptom Triage (`triage_llm.py`)](#step-5-stage-1-symptom-triage)
   - [Step 6: Hybrid Retrieval with Reciprocal Rank Fusion (`hybrid_retriever.py`)](#step-6-hybrid-retrieval-with-reciprocal-rank-fusion)
   - [Step 7: Stage 2 Diagnostic Reasoning & Grounded Q&A (`reasoning_llm.py`, `answer_generator.py`)](#step-7-stage-2-diagnostic-reasoning--grounded-qa)
   - [Step 8: Stage 3 Location Resolution via Mapbox MCP (`location_llm.py`, `mapbox_mcp_client.py`)](#step-8-stage-3-location-resolution-via-mapbox-mcp)
   - [Step 9: Ephemeral Session Management (`session_manager.py`)](#step-9-ephemeral-session-management)
5. [Summary Comparison Matrix](#5-summary-comparison-matrix)
6. [Glossary of Key Terms](#6-glossary-of-key-terms)

---

## 1. What is RAG and Why Does It Exist?

### Parametric vs. Non-Parametric Memory
To understand RAG, you must understand how Large Language Models (LLMs) store information:

1. **Parametric Memory (Internal Weights)**:
   - When a model like GPT-4 or Qwen is trained, all its "knowledge" is baked into billions of numerical weights (parameters).
   - *Limitation*: This knowledge is **frozen at the training cutoff date**. It cannot know about your private files, your specific 2024 car manual, or real-time diagnostic codes unless retrained (which is slow, extremely expensive, and prone to forgetting).
2. **Non-Parametric Memory (External Knowledge Base)**:
   - This refers to external data stores: PDF manuals, SQL databases, vector indices, search engines, and documents.
   - *Advantage*: Up-to-date, private, easily auditable, and can be added, updated, or deleted instantly at zero training cost.

### The Core Problems RAG Solves
**RAG (Retrieval-Augmented Generation)** is the architectural pattern of fetching relevant information from **non-parametric memory** (your documents) and passing it directly into the LLM's **context window** as prompt background when answering a query.

RAG eliminates the three biggest pitfalls of generative AI:
- **Hallucinations**: Without source context, an LLM invents plausible-sounding but completely fabricated specifications (e.g., guessing incorrect tire pressures or oil types).
- **Knowledge Blind Spots**: Enables LLMs to answer questions on proprietary, private, or niche technical data (e.g., a specific vehicle's wiring pinout).
- **Lack of Auditability / Explainability**: In engineering or legal workflows, an answer is useless without citations. RAG allows you to cite exact document names, sections, page numbers, and diagrams.

---

## 2. The Spectrum of RAG Architectures

RAG systems have evolved through three distinct evolutionary stages:

```
+-------------------------------------------------------------------------+
|                              RAG EVOLUTION                              |
+-------------------------------------------------------------------------+
|                                                                         |
|  1. Naive RAG:                                                          |
|     [Doc] -> [Fixed Split] -> [Vector Embed] -> [Top-K] -> [LLM Answer] |
|                                                                         |
|  2. Advanced RAG:                                                       |
|     [Doc] -> [Smart Chunk] -> [Hybrid Search: BM25 + Vector] -> [RRF]   |
|            -> [Rerank] -> [Contextual Prompt] -> [LLM Answer]          |
|                                                                         |
|  3. Modular / Agentic RAG (What this app implements!):                  |
|     [Symptom] -> [Stage 1: Triage LLM]                                  |
|               -> [Multi-Query Hybrid Retrieval (BM25 + ChromaDB + VLM)] |
|               -> [Reciprocal Rank Fusion]                               |
|               -> [Stage 2: Diagnostic Reasoning LLM + Citations]        |
|               -> [Stage 3: Mapbox MCP Tool Execution for Service Shops] |
+-------------------------------------------------------------------------+
```

### 1. Naive RAG (Baseline)
- Takes a document, splits it into arbitrary fixed chunks (e.g., every 500 characters).
- Converts each chunk into a mathematical vector using an embedding model.
- When a user asks a question, converts the question into a vector and finds the nearest chunk vectors by cosine similarity.
- Dumps the top 3 chunks into an LLM prompt.
- **Why Naive RAG Fails in Complex Domains**:
  - *Cutoff Context*: Splitting mid-sentence or mid-table ruins meaning.
  - *Keyword Blindness*: Pure vector search struggles with exact alphanumeric strings like Diagnostic Trouble Codes (`P0300`), connector IDs (`C201`), or part numbers.
  - *Visual Blindness*: Technical manuals are full of circuit diagrams and schematics that text-only vectorizers ignore completely.

### 2. Advanced RAG
- Introduces **pre-retrieval** (header-aware chunking, OCR cleanup, query expansion) and **post-retrieval** strategies (reranking, fusion, filtering).
- Uses **Hybrid Search** (combining keyword/lexical search like BM25 with dense semantic vector search).

### 3. Modular / Agentic RAG
- Breaks the problem into multi-stage specialized reasoning agents and tools.
- A **Triage Agent** breaks down a user's natural language symptom into discrete sub-queries and vehicle systems.
- A **Hybrid Engine** gathers multimodal passages and diagrams.
- A **Reasoning Agent** synthesizes a differential diagnosis with explicit evidence and page references.
- **Tool-calling components** (like the Model Context Protocol / MCP) execute real-world actions (e.g., geocoding locations and mapping repair shops).

---

## 3. Deep Dive into Core RAG Concepts & Nuances

### Ingestion & Document Parsing
Real-world documents are messy. Technical vehicle manuals contain mixed layouts: multi-column text, wiring schematics, embedded images, tables, and repair flowcharts.

1. **Structured PDF Parsing**: Standard text extractors scramble tables and multi-column text. Modern RAG uses tools like `PyMuPDF4LLM` to convert PDF layouts into clean, Markdown-formatted text that preserves headers (`#`, `##`) and tables.
2. **Optical Character Recognition (OCR) with Image Preprocessing**: When manuals contain scanned pages or diagrams with embedded text, standard parsing yields empty strings. Advanced RAG uses Computer Vision (OpenCV) to apply:
   - **CLAHE (Contrast Limited Adaptive Histogram Equalization)**: Balances lighting across the image.
   - **Adaptive Binarization**: Converts dark/light gradients into sharp black text on white backgrounds.
   - **Denoising**: Removes scan artifacts before feeding into OCR engines like Tesseract or EasyOCR.

### Chunking Strategies
LLMs have context window limits, and embedding models work best when text focuses on a single coherent topic. If chunks are too large, the vector becomes diluted; if chunks are too small, critical context is lost.

```
Header-Aware Chunking with Overlap:
[## System: Air Conditioning]
  [### Compressor Clutch Operation]
    [Chunk 1: Paragraph A + Paragraph B (Max 1600 chars)] ... [200 char overlap]
                                                            [Chunk 2: Overlap + Paragraph C]
```

- **Fixed-Size Chunking**: Slices every $N$ characters. (Flawed: breaks sentences and table rows).
- **Semantic Chunking**: Splits based on semantic shifts between sentences.
- **Header-Aware Chunking (Best for Manuals)**: Respects document structure by splitting at Markdown headers (`#`, `##`, `###`). Sub-chunks inherit their parent section title (`"HVAC > Compressor Clutch > Diagnostic Steps"`), so the vector representation knows where the passage came from.
- **Chunk Overlap**: Carries the last 100–200 characters of Chunk 1 into the beginning of Chunk 2. This prevents search queries from missing concepts split across chunk boundaries.

### Embeddings & Representation
An embedding model converts text or images into a high-dimensional vector of numbers (e.g., 384 or 1536 floating-point values) where mathematically close vectors represent semantically similar meanings.

- **Dense Vectors**: Capture semantic meaning (e.g., `"warm air blowing"` is close to `"cooling performance degraded"`).
- **Multimodal CLIP Embeddings**: Models like `clip-ViT-B-32` embed text and images into the *same shared vector space*. A text query like *"wiring schematic for blower motor"* can directly match the image vector of a wiring diagram.

### Lexical Search (BM25) vs. Semantic Search (Vector)

| Search Type | Algorithm | Superpower | Weakness |
| :--- | :--- | :--- | :--- |
| **Lexical (Keyword)** | **BM25 / BM25Plus** | Exact string matching, part numbers (`05058693AA`), DTC codes (`P0420`), connector pinouts (`Pin 4 Ground`). | Cannot understand synonyms (searches for "tyre" won't find "wheel"). |
| **Semantic (Dense Vector)** | **Cosine / L2 Distance** | Conceptual similarity, paraphrasing, synonyms, multilingual queries. | Can miss exact technical alphanumeric strings or rare codes. |

### Hybrid Retrieval & Reciprocal Rank Fusion (RRF)
To get the best of both worlds, **Hybrid Retrieval** executes both BM25 and Vector search in parallel. 

However, their score scales are completely different (BM25 returns unbounded positive scores like `14.2`, while vector distance might return `0.82`). You cannot simply add them together.

**Reciprocal Rank Fusion (RRF)** solves this by looking only at the *rank position* of each document in the respective result lists:

$$\text{RRF Score}(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$

Where:
- $M$ is the set of search algorithms (e.g., BM25 and ChromaDB Vector Search).
- $r_m(d)$ is the rank position (1, 2, 3...) of document $d$ in system $m$.
- $k$ is a smoothing constant (typically $k = 60$).

If a passage ranks #1 in BM25 and #2 in Vector Search, its RRF score is:
$$\text{Score} = \frac{1}{60 + 1} + \frac{1}{60 + 2} = 0.01639 + 0.01613 = 0.03252$$

### Query Triage, Transformation & Expansion
Users rarely write queries that match the exact technical terminology of a workshop manual.
- User says: *"Car shudders when braking at high speed."*
- Service manual title: *"Front Disc Brake Rotor Lateral Runout and Thickness Variation."*

**Query Triage / Expansion (Stage 1)** passes the user's raw symptom to a fast LLM that returns:
1. Candidate vehicle subsystems (`["Brake System", "Suspension", "Wheel Assembly"]`).
2. Multiple targeted technical search queries (`["brake rotor runout inspection", "disc thickness variation measurement", "caliper slide pin torque"]`).

### Context Synthesis, Grounding & Source Attribution
The retrieved chunks are formatted into a prompt context template:
```text
SYSTEM: You are an expert automotive technician. Use ONLY the excerpts below.
EXCERPTS:
[Page 42 - Diagnostic Trouble Codes]
P0300 indicates random/multiple cylinder misfire detected...

[Page 88 - Ignition Coil Inspection]
Measure primary resistance across terminals 1 and 2 (0.7 - 0.9 ohms)...

USER SYMPTOM: Engine sputtering under load with flashing check engine light.
```
The model generates the answer, cites page numbers, and outputs structured JSON containing steps, differential diagnoses, and confidence ratings.

### Tool Use via MCP (Model Context Protocol)
RAG doesn't have to stop at generating text. In modern agentic architectures, the LLM uses structured outputs to invoke external tools. 
Using **MCP (Model Context Protocol)** over JSON-RPC 2.0, the app can take the diagnosis, geocode the user's location, find nearby specialty mechanics, and render a live map.

---

## 4. How This Application Implements RAG: End-to-End Code Walkthrough

Let's examine how each concept is implemented in the codebase:

### Architecture Diagram

```
 know-my-car--owner-s-manual-main/
 ├── app.py                          # Streamlit UI (Home, Upload, Diagnose, Query, Session)
 └── src/
     ├── models.py                   # Data contracts (Passage, Document, QueryResult, DiagnosisResult)
     ├── components/
     │   ├── document_parser.py      # Multi-format parsing + OCR
     │   ├── pdf_ingester.py         # PyMuPDF4LLM Markdown extraction + Diagram isolation
     │   ├── vlm_captioner.py        # Vision-Language Model diagram captioning (LLaVA)
     │   ├── chunker.py              # Header-aware chunking with trailing overlap
     │   ├── embedding_generator.py  # Multimodal CLIP embeddings (sentence-transformers)
     │   ├── bm25_index.py           # BM25Plus lexical index for DTCs & part numbers
     │   ├── vector_store.py         # ChromaDB in-memory vector store
     │   ├── hybrid_retriever.py     # Reciprocal Rank Fusion (RRF) search
     │   ├── triage_llm.py           # Stage 1: Symptom -> Systems & Search queries
     │   ├── reasoning_llm.py        # Stage 2: Context -> Differential diagnosis & steps
     │   ├── answer_generator.py     # General Q&A with source attribution
     │   ├── location_llm.py         # Stage 3: Mapbox MCP geocoding & shop locator
     │   ├── mapbox_mcp_client.py    # JSON-RPC 2.0 Mapbox MCP Client
     │   └── session_manager.py      # Ephemeral state orchestration
     └── utils/
         └── constants.py            # Model names, timeouts, chunk limits, thresholds
```

---

### Step 1: Document Parsing & OCR Pipeline
**Files:** `src/components/document_parser.py` & `src/components/pdf_ingester.py`

When a document is uploaded:
1. `DocumentParser.parse()` detects the format (`.pdf`, `.png`, `.xlsx`, `.pptx`, `.mp4`).
2. For PDFs, `PdfIngester.ingest()` uses `pymupdf4llm.to_markdown(doc, page_chunks=True)` to convert pages into layout-preserved Markdown text.
3. It iterates through raw image streams in the PDF via PyMuPDF xrefs, extracting embedded electrical and component schematics as PNG bytes.
4. For standalone image files, `DocumentParser._preprocess_image()` uses OpenCV to apply CLAHE contrast enhancement, adaptive thresholding, and denoising, followed by Tesseract/EasyOCR extraction.

```python
# From src/components/pdf_ingester.py
doc = pymupdf.open(stream=file_bytes, filetype="pdf")
page_chunks = pymupdf4llm.to_markdown(doc, page_chunks=True)
for i, chunk in enumerate(page_chunks):
    pages.append({"page": chunk.get("metadata", {}).get("page_number", i + 1), "markdown": chunk.get("text", "")})
```

---

### Step 2: Vision-Language Model Diagram Captioning
**File:** `src/components/vlm_captioner.py`

Diagrams cannot be indexed by text embeddings alone unless captioned. The application sends extracted diagram bytes to a vision model (e.g. `llava:7b`):

```python
# From src/components/vlm_captioner.py
_PROMPT = (
    "Describe this vehicle service manual diagram for a technician: identify the component, "
    "connectors, wiring colors, part numbers, and any labels visible. Be concise but complete."
)
b64 = base64.b64encode(image_bytes).decode("utf-8")
response = self.client.chat.completions.create(
    model=VLM_MODEL,
    messages=[{"role": "user", "content": [{"type": "text", "text": _PROMPT}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}]
)
```
The resulting caption is attached to a `Passage` object with `is_diagram=True` and its original image bytes preserved so it can later be shown to the user in the Streamlit UI.

---

### Step 3: Header-Aware Chunking with Overlap
**File:** `src/components/chunker.py`

The `Chunker` splits pages along Markdown headers (`#`, `##`, `###`, `####`):

```python
# From src/components/chunker.py
_HEADER_PATTERN = re.compile(r"^(#{1,4}\s+.+)$", re.MULTILINE)

# If a section exceeds CHUNK_MAX_CHARS (1600 chars), it splits on paragraph boundaries
# and carries a trailing overlap (CHUNK_OVERLAP_CHARS = 200) to the next chunk:
prev_tail = ""
for sub in self._split_to_max(section_text):
    combined = f"{prev_tail}\n\n{sub}".strip() if prev_tail else sub
    chunks.append(self._clone(passage, combined, len(chunks), section=section_label))
    prev_tail = sub[-CHUNK_OVERLAP_CHARS:] if len(sub) > CHUNK_OVERLAP_CHARS else sub
```

---

### Step 4: Lexical BM25 & Semantic ChromaDB Indexing
**Files:** `src/components/bm25_index.py`, `src/components/vector_store.py`, `src/components/embedding_generator.py`

The chunked passages are indexed in two parallel engines:

1. **BM25 Lexical Index (`BM25Plus`)**:
   - Tokenizes text with alphanumeric regex (`[A-Za-z0-9]+`), preserving DTC codes and part numbers.
   - Uses `BM25Plus` to avoid negative scoring on technical terms that appear frequently in small manuals.
2. **ChromaDB Vector Store**:
   - Uses `EmbeddingGenerator` (`SentenceTransformer('sentence-transformers/clip-ViT-B-32')`).
   - For text chunks, it embeds the text.
   - For diagram chunks, it passes the raw PIL image directly into the CLIP vision encoder.
   - Stores embeddings in an in-memory ephemeral ChromaDB collection.

---

### Step 5: Stage 1 Symptom Triage
**File:** `src/components/triage_llm.py`

When a user describes a symptom in the **Diagnose** tab (e.g., *"AC blows warm air only at highway speeds and clutch won't engage"*):
`TriageLLM` executes a fast prompt requiring strict JSON:
```json
{
  "systems": ["HVAC", "Engine Cooling", "Electrical"],
  "search_queries": [
    "compressor clutch high speed disengagement",
    "A/C high pressure cutoff switch",
    "refrigerant charge low symptoms"
  ]
}
```

---

### Step 6: Hybrid Retrieval with Reciprocal Rank Fusion
**File:** `src/components/hybrid_retriever.py`

For every query generated by the triage stage, `HybridRetriever`:
1. Queries the BM25 index for top 10 matches.
2. Queries the Vector Store for top 10 matches.
3. Merges the scores using the Reciprocal Rank Fusion formula:

```python
# From src/components/hybrid_retriever.py
def _accumulate_rrf(self, ranked_results, fused_scores, passage_by_key):
    for rank, (passage, _score) in enumerate(ranked_results, start=1):
        key = (passage.document_id, passage.section, passage.passage_index)
        fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
        passage_by_key[key] = passage
```
The top 8 overall ranked passages are selected for the reasoning model.

---

### Step 7: Stage 2 Diagnostic Reasoning & Grounded Q&A
**Files:** `src/components/reasoning_llm.py` & `src/components/answer_generator.py`

`ReasoningLLM` takes the fused excerpts and generates a differential diagnosis:

```python
# From src/components/reasoning_llm.py
_SYSTEM_PROMPT = """You are an expert vehicle diagnostic technician. Using ONLY the provided service \
manual excerpts (with page citations) and diagram captions, produce a differential diagnosis for the \
driver's symptom.
Respond ONLY with JSON:
{
  "thinking": "short internal reasoning trace",
  "steps": ["step 1", "step 2", "..."],
  "differential": [{"cause": "...", "likelihood": "high|medium|low", "evidence": "..."}],
  "cited_pages": ["Page 12", "..."]
}"""
```

The user receives:
- **Thinking trace**: Why the AI arrived at this conclusion.
- **Ordered Diagnostic Steps**: Concrete testing sequence for the mechanic.
- **Ranked Differential Causes**: Each with a likelihood rating and cited evidence.
- **Diagram Previews**: The actual wiring schematics embedded directly in the Streamlit UI.

For direct questions on the **Query** tab, `answer_generator.py` runs standard grounded Q&A with expandable source accordions.

---

### Step 8: Stage 3 Location Resolution via Mapbox MCP
**Files:** `src/components/location_llm.py` & `src/components/mapbox_mcp_client.py`

Once a diagnosis is made (e.g. *"AC Compressor Clutch Failure"*), the user can enter their location:
1. `LocationLLM` queries the OpenAI endpoint to map the diagnosis to a Mapbox search category (`"car_repair"`, `"auto_parts"`).
2. `MapboxMCPClient` sends JSON-RPC 2.0 requests to the hosted Mapbox MCP server:
   - Calls `search_and_geocode_tool` to get latitude/longitude coordinates.
   - Calls `category_search_tool` to locate repair shops within proximity.
   - Calls `place_details_tool` to fetch phone numbers and websites.
   - Calls `static_map_image_tool` to render a static map with color-coded markers.

---

### Step 9: Ephemeral Session Management
**File:** `src/components/session_manager.py`

Streamlit re-runs script files from top to bottom on each user interaction. 
`SessionManager` manages state persistence inside `st.session_state`:
- Keeps the in-memory ChromaDB collection, BM25 indices, query history, and active document dictionaries cached across page changes.
- Automatically re-indexes both lexical and vector engines whenever a new document is added.
- Provides 1-click memory clearing to wipe all session data without restarting the server.

---

## 5. Summary Comparison Matrix

| RAG Component | Theoretical Purpose | Implementation in this Codebase |
| :--- | :--- | :--- |
| **Ingestion** | Extract layout-preserved text and diagrams from raw files. | `PyMuPDF4LLM` (PDF Markdown) + `pdfplumber` + OpenCV / Tesseract / EasyOCR. |
| **VLM Captioning** | Make non-text visual diagrams searchable. | `VLMCaptioner` calling `llava:7b` via OpenRouter / Ollama. |
| **Chunking** | Divide content into coherent contextual blocks. | `Chunker` with Markdown header splitting + 200 char trailing overlap. |
| **Embeddings** | Map multimodal data into high-dimensional semantic vector space. | `SentenceTransformer` using `clip-ViT-B-32` (multimodal image + text). |
| **Lexical Index** | Exact-match retrieval for part numbers & codes. | `BM25Plus` from `rank_bm25` with alphanumeric tokenization. |
| **Vector Store** | Fast nearest-neighbor semantic search. | In-memory `ChromaDB EphemeralClient` with L2-to-similarity conversion. |
| **Query Expansion** | Translate vague symptoms into targeted queries. | `TriageLLM` decomposing symptoms into systems and search queries. |
| **Hybrid Fusion** | Combine keyword and semantic search results without score distortion. | `HybridRetriever` using Reciprocal Rank Fusion (RRF with $k=60$). |
| **Reasoning & Synthesis** | Generate structured, cited diagnostic conclusions. | `ReasoningLLM` producing thinking traces, likelihoods, steps, and citations. |
| **Tool Execution** | Perform real-world grounded actions. | `LocationLLM` + `MapboxMCPClient` via JSON-RPC 2.0. |

---

## 6. Glossary of Key Terms

- **RAG (Retrieval-Augmented Generation)**: The architecture of fetching relevant external documents to augment an LLM's prompt context before generation.
- **Dense Embedding**: A continuous vector of numbers generated by a neural network that represents semantic concepts.
- **Sparse / Lexical Representation**: Word-frequency-based indexing (like TF-IDF or BM25) focused on exact keyword matches.
- **BM25 (Best Matching 25)**: A probabilistic lexical ranking function widely used in information retrieval.
- **Reciprocal Rank Fusion (RRF)**: An algorithm that combines the ranked results of multiple search engines based on their positions rather than raw scores.
- **Chunk Overlap**: The practice of duplicating a small portion of text at the boundary between adjacent chunks to prevent context fragmentation.
- **VLM (Vision-Language Model)**: A multimodal AI model capable of understanding and describing images in natural language text.
- **MCP (Model Context Protocol)**: An open standard enabling AI models to interact with external tools and data sources via JSON-RPC.
- **Hallucination**: When an LLM generates factually incorrect or ungrounded statements with high confidence.
- **Differential Diagnosis**: A systematic diagnostic method used to identify the presence of an entity where multiple alternatives are possible.
- **Grounding**: Restricting the model's answers exclusively to the facts provided in the prompt context.

---
*Happy learning! You can reference this document anytime while inspecting, modifying, or extending the codebase.*
