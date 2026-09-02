"""Application constants and configuration."""

import os
import streamlit as st

# API Configuration — defaults point at a local Ollama server (OpenAI-compatible endpoint).
# Ollama ignores the API key value but the OpenAI SDK requires a non-empty string.
OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", "ollama"))
OPENROUTER_API_BASE_URL = st.secrets.get(
    "OPENROUTER_API_BASE_URL", os.getenv("OPENROUTER_API_BASE_URL", "http://localhost:11434/v1")
)
OPENAI_MODEL = st.secrets.get("OPENAI_MODEL", "qwen2.5:7b-instruct-q4_K_M")
EMBEDDING_MODEL = st.secrets.get("EMBEDDING_MODEL", "sentence-transformers/clip-ViT-B-32")

# Diagnostic pipeline models (Stage 1 triage, Stage 2 reasoning, diagram captioning)
TRIAGE_MODEL = st.secrets.get("TRIAGE_MODEL", "qwen2.5:7b-instruct-q4_K_M")
REASONING_MODEL = st.secrets.get("REASONING_MODEL", "qwen2.5:7b-instruct-q4_K_M")
VLM_MODEL = st.secrets.get("VLM_MODEL", "llava:7b")

# Header-aware chunking (with overlap) for the diagnostic pipeline
CHUNK_MAX_CHARS = 1600
CHUNK_OVERLAP_CHARS = 200

# Hybrid retrieval (BM25 + vector, fused with Reciprocal Rank Fusion)
RETRIEVAL_TOP_K = 10  # per-query candidates from each of BM25 and vector search
HYBRID_TOP_K = 8  # final fused passages passed to the reasoning stage
RRF_K = 60  # RRF constant (higher = flatter rank weighting)

# Stage 3: Location LLM + Mapbox MCP (find nearest service station)
MAPBOX_ACCESS_TOKEN = st.secrets.get("MAPBOX_ACCESS_TOKEN", os.getenv("MAPBOX_ACCESS_TOKEN", ""))
MAPBOX_MCP_URL = st.secrets.get("MAPBOX_MCP_URL", "https://mcp.mapbox.com/mcp")
LOCATION_MODEL = st.secrets.get("LOCATION_MODEL", "qwen2.5:7b-instruct-q4_K_M")
STATION_SEARCH_LIMIT = 5  # number of candidate stations to fetch/display
STATION_MAP_ZOOM = 12
STATION_MAP_SIZE = (600, 400)  # (width, height) px for the static map image

# Timeouts & Performance
QUERY_TIMEOUT_SECONDS = st.secrets.get("QUERY_TIMEOUT_SECONDS", 30)
SESSION_TIMEOUT_MINUTES = st.secrets.get("SESSION_TIMEOUT_MINUTES", 60)
EMBEDDING_CHUNK_SIZE = 1024  # tokens per passage (increased for better context)
FAISS_TOP_K = 5  # number of passages to retrieve
SEMANTIC_CHUNK_MIN_SIZE = 200  # minimum chars for a semantic chunk
SEMANTIC_CHUNK_MAX_SIZE = 4096  # maximum chars for a semantic chunk (increased)

# Limits
MAX_DOCS_PER_SESSION = st.secrets.get("MAX_DOCS_PER_SESSION", 10)
MAX_FILE_SIZE_MB = st.secrets.get("MAX_FILE_SIZE_MB", 50)
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Supported Formats
SUPPORTED_FORMATS = {
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".xls": "excel",
    ".xlsx": "excel",
    ".ppt": "powerpoint",
    ".pptx": "powerpoint",
    ".mp4": "video",
    ".mov": "video",
    ".avi": "video",
    ".webm": "video",
}

# Relevance Threshold
RELEVANCE_THRESHOLD = 0.3  # Minimum similarity score (1/(1+L2_distance)) to include passage

# Error Codes
ERROR_CODES = {
    "UNSUPPORTED_FORMAT": "File format not supported. Please upload PDF, image, Excel, PowerPoint, or video files.",
    "FILE_TOO_LARGE": "File is too large (max 50 MB). Please upload a smaller file.",
    "DUPLICATE_FILE": "This file is already uploaded.",
    "PARSE_FAILED": "Unable to parse this file. Please check the file integrity and try again. If the problem persists, try a different format.",
    "NO_DOCUMENTS": "No documents uploaded. Please upload a document first.",
    "QUERY_TIMEOUT": "Query took too long to process. Please try again or rephrase your question.",
    "NO_RESULTS": "No relevant information found. Please try rephrasing your question or upload additional documents.",
    "OUT_OF_SCOPE": "Your question doesn't relate to the uploaded documents. Please ask something about the vehicle manuals.",
    "INTERNAL_ERROR": "An internal error occurred. Please try again.",
}

# UI Messages
UI_MESSAGES = {
    "upload_success": "✅ File uploaded successfully: {filename}",
    "upload_duplicate": "⚠️ This file is already uploaded.",
    "query_success": "✅ Found relevant information!",
    "query_no_results": "❌ No relevant information found.",
    "session_cleared": "✅ Session cleared successfully.",
    "processing": "⏳ Processing... Please wait.",
}
