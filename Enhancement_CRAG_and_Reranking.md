# Enhancement Deep Dive: Neural Cross-Encoder Reranking & Corrective RAG (CRAG)

This document provides a comprehensive technical breakdown of the **2-Stage Neural Cross-Encoder Reranking** and **Corrective RAG (CRAG)** enhancements implemented in this repository. 

You can use this document as your personal reference for understanding the architecture and preparing for technical interviews.

---

## 1. Executive Summary

Standard (Naive) RAG retrieves documents using a single-pass embedding search (Bi-Encoder) and blindly passes the top $K$ chunks into the LLM context. In technical domains like automotive repair, this leads to two major failures:
1. **Subtle False Positives**: Bi-encoder vector search misses subtle technical distinctions (e.g., confusing "AC condenser fan relay" with "radiator cooling fan relay").
2. **Hallucination on Missing Data**: When a user asks about something not in the manual, the retriever still returns the "least irrelevant" chunks, causing the LLM to hallucinate.

### The Solution We Built:
```
                                 THE ENHANCED CRAG PIPELINE
                                 
   [User Query / Symptom]
             │
             ▼
   ┌─────────────────────────────────────────────────────────┐
   │ 1st-Stage Hybrid Retrieval: Lexical (BM25) + Vector     │
   │ (Gathers top 10 candidates using Reciprocal Rank Fusion)│
   └────────────────────────────┬────────────────────────────┘
                                │ (Candidate Passages)
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │ 2nd-Stage Neural Cross-Encoder Reranker                 │
   │ (Deep cross-attention over query + document pairs)      │
   └────────────────────────────┬────────────────────────────┘
                                │ (Reranked Passages + Neural Scores)
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │ Corrective RAG (CRAG) Evaluator & Guardrail             │
   │ - Filters low-relevance noise chunks                    │
   │ - Classifies quality: CORRECT / AMBIGUOUS / OUT_OF_SCOPE│
   └────────────────────────────┬────────────────────────────┘
                                │
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                        ▼
  [🟢 CORRECT]            [🟡 AMBIGUOUS]           [🔴 OUT_OF_SCOPE]
High confidence      Moderate confidence       Shield LLM from hallucinating
Pass to Reasoning    Flag uncertainty to LLM   Trigger domain guardrail badge
```

---

## 2. Theoretical Deep Dive: Bi-Encoders vs. Cross-Encoders

### Why Dual-Stage Retrieval is Essential
In information retrieval, there is an inherent trade-off between **search speed** and **semantic accuracy**:

| Feature | 1st Stage: Bi-Encoder (Embedding Vector Search) | 2nd Stage: Cross-Encoder (Neural Reranker) |
| :--- | :--- | :--- |
| **Architecture** | Dual-Tower: Embeds query $q$ and document $d$ **independently**: $\vec{u} = f(q)$, $\vec{v} = f(d)$. | Single-Tower: Feeds $(q, d)$ **together** into the Transformer with full cross-attention. |
| **Similarity** | Cosine / L2 distance between static vectors: $\text{sim}(\vec{u}, \vec{v})$. | Cross-attention score output from classification head: $S = g([q; d])$. |
| **Complexity** | $O(1)$ lookup with vector index (millisecond latency over millions of docs). | $O(K \cdot L^2)$ computational cost (too slow for $1,000,000$ docs, but fast for top 10–20 docs). |
| **Cross-Token Attention** | ❌ None (words in query cannot attend to words in document). | ✅ **Full bidirectional attention between every query word and every document word.** |
| **Role in Pipeline** | **Candidate Generation**: Filters 10,000 pages down to top 10 candidates. | **Precision Reranking**: Re-orders top 10 candidates with surgical accuracy. |

---

## 3. The Corrective RAG (CRAG) Paradigm

Based on the landmark paper *Corrective Retrieval Augmented Generation (Yan et al., 2024)*, CRAG adds a **self-reflective evaluation and filtering step** before generation:

1. **Context Evaluation**:
   - Each retrieved chunk is scored by the neural Cross-Encoder.
   - The overall retrieval confidence is evaluated against domain thresholds:
     - **$\ge 55\%$ $\rightarrow$ `CORRECT`**: The manual directly answers the question.
     - **$28\% \le \text{Score} < 55\%$ $\rightarrow$ `AMBIGUOUS`**: Partial information; LLM is instructed to flag diagnostic uncertainty.
     - **$< 28\%$ $\rightarrow$ `OUT_OF_SCOPE`**: Information is missing. System prevents hallucination and notifies user.
2. **Adaptive Noise Filtering**:
   - Chunks that fall below the adaptive cutoff ($< 45\%$ of the top score) are discarded. This stops irrelevant text from cluttering the LLM's prompt.

---

## 4. Code Implementation in This Repository

### 1. `src/components/cross_encoder_reranker.py`
- Implements `CrossEncoderReranker` using `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- Normalizes raw model output logits via Sigmoid:
  $$\sigma(x) = \frac{1}{1 + e^{-x}}$$
- Includes an automotive **DTC Boost heuristic**: If an exact Diagnostic Trouble Code (e.g., `P0300`, `P0420`) matches between the query and the manual chunk, it applies a targeted relevance boost.
- Includes a graceful fallback for offline/test environments.

### 2. `src/components/crag_evaluator.py`
- Implements `CRAGEvaluator.evaluate_and_filter()`.
- Produces a structured `CRAGReport` with the relevance grade, confidence percentage, actions taken, and chunk-by-chunk score breakdown.

### 3. `src/components/hybrid_retriever.py`
- Coordinates the end-to-end flow:
  `BM25 Lexical + ChromaDB Vector` $\xrightarrow{\text{RRF}}$ `Cross-Encoder Rerank` $\xrightarrow{\text{CRAG Filtering}}$ `Filtered Passages + Report`.

### 4. `app.py` Streamlit Observability UI
- Adds an interactive **CRAG & Reranker Observability Panel** on both the **Query** and **Diagnose** pages:
  - Visual status badge (🟢 `CORRECT`, 🟡 `AMBIGUOUS`, 🔴 `OUT_OF_SCOPE`)
  - Neural Confidence metric
  - Retained vs. filtered passage metrics
  - Transparent per-chunk neural score breakdown table

---

## 5. Resume & Interview Preparation Guide

### 📋 Resume Bullet Points (Copy & Paste Ready)
> • **Engineered an Advanced Multimodal Corrective RAG (CRAG) pipeline** utilizing 2-stage neural Cross-Encoder reranking (`ms-marco-MiniLM`) and hybrid BM25/Vector retrieval, increasing retrieval Precision@K and preventing out-of-scope hallucinations.
>
> • **Implemented real-time retrieval observability and self-reflective context evaluation**, classifying document relevance (Correct/Ambiguous/Out-of-Scope) and filtering noisy passages before LLM synthesis.

---

### 🎙️ Top 5 Interview Questions & Winning Answers

#### Q1: "Why did you use both a Bi-Encoder and a Cross-Encoder?"
> **Answer**: *"Bi-encoders embed documents into static vectors independently, which allows for millisecond approximate nearest neighbor search across large corpora. However, because query and document tokens never interact during embedding, bi-encoders miss subtle semantic dependencies. A Cross-Encoder performs full cross-attention over all (query, document) token pairs simultaneously. By using a Bi-Encoder + BM25 in Stage 1 to retrieve the top 10 candidates, and a Cross-Encoder in Stage 2 to rerank them, we achieve the search speed of vector indexing combined with the ranking accuracy of deep cross-attention."*

#### Q2: "What is Corrective RAG (CRAG) and what problem does it solve?"
> **Answer**: *"In standard RAG, the LLM assumes that whatever the retriever returns is relevant. If the user's question is outside the scope of the manual, the retriever still returns the closest mathematical vectors, leading to confident hallucinations. CRAG introduces an evaluator node that grades retrieval confidence. If confidence is high (`CORRECT`), it filters out noisy chunks; if confidence is low (`OUT_OF_SCOPE`), it blocks hallucination and triggers guardrail notifications."*

#### Q3: "How did you combine BM25 and Vector Search before reranking?"
> **Answer**: *"We used Reciprocal Rank Fusion (RRF). Since BM25 scores (unbounded term frequencies) and vector similarities (cosine/L2 distances) operate on completely different numerical scales, you cannot simply add them together. RRF calculates score contributions based purely on document rank position ($1 / (k + \text{rank})$), allowing balanced lexical and semantic candidate generation."*

#### Q4: "Why was BM25 necessary if you already had neural embeddings?"
> **Answer**: *"In automotive engineering, users frequently search for specific alphanumeric codes—like DTC trouble code `P0300`, part numbers, or relay pin numbers (`Pin 4 Ground`). Dense vector embeddings compress text into general semantic spaces and often struggle with exact token matches. BM25 guarantees that rare alphanumeric codes are surfaced with 100% precision."*

#### Q5: "How does the system handle diagrams and electrical schematics?"
> **Answer**: *"We implemented a multimodal pipeline: embedded diagram images are extracted via PyMuPDF, captioned with a Vision-Language Model (`LLaVA`), and embedded into a shared vector space using `clip-ViT-B-32`. This allows text queries to match visual diagrams directly and displays the schematics alongside diagnostic steps."*
