"""Answer generation using Open Router LLM."""

import time
from typing import List, Tuple
from openai import OpenAI

from src.models import Passage, QueryResult, SourceAttribution
from src.utils.logger import setup_logger, log_event
from src.utils.constants import OPENROUTER_API_KEY, OPENROUTER_API_BASE_URL, OPENAI_MODEL, QUERY_TIMEOUT_SECONDS, ERROR_CODES

logger = setup_logger(__name__)


class AnswerGenerator:
    """Generate answers using Open Router LLM."""
    
    def __init__(self):
        """Initialize the answer generator."""
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set in environment or secrets")
        self.client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_API_BASE_URL)
    
    def generate_answer(
        self,
        query_text: str,
        passages: List[Passage],
        timeout_seconds: int = QUERY_TIMEOUT_SECONDS,
    ) -> QueryResult:
        """Generate an answer using passages and LLM.
        
        Args:
            query_text: The user's question.
            passages: Relevant passages retrieved from documents.
            timeout_seconds: Timeout for LLM call.
        
        Returns:
            QueryResult with status, answer, sources, confidence.
        """
        start_time = time.time()
        
        try:
            # Check if we have passages
            if not passages:
                return QueryResult(
                    status="no_results",
                    answer=ERROR_CODES.get("NO_RESULTS", "No information found."),
                    sources=[],
                    confidence=0.0,
                    response_time_ms=int((time.time() - start_time) * 1000),
                )
            
            # Build prompt
            prompt = self._build_prompt(query_text, passages)
            
            # Call LLM
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based on the provided documents. Be concise and accurate. If the information is not in the documents, say so."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500,
                timeout=timeout_seconds,
            )
            
            answer = response.choices[0].message.content
            
            # Build source attributions
            sources = self._build_sources(passages)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            log_event(
                "generate_answer",
                query=query_text[:50],
                passage_count=len(passages),
                response_time_ms=elapsed_ms,
            )
            
            return QueryResult(
                status="success",
                answer=answer,
                sources=sources,
                confidence=0.85,  # Simplified confidence; could be improved
                response_time_ms=elapsed_ms,
            )
        
        except TimeoutError:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"LLM call timed out after {elapsed_ms}ms")
            return QueryResult(
                status="error",
                answer=ERROR_CODES.get("QUERY_TIMEOUT", "Query timed out."),
                sources=[],
                confidence=0.0,
                response_time_ms=elapsed_ms,
            )
        
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Failed to generate answer: {e}")
            return QueryResult(
                status="error",
                answer=ERROR_CODES.get("INTERNAL_ERROR", "An error occurred."),
                sources=[],
                confidence=0.0,
                response_time_ms=elapsed_ms,
            )
    
    def _build_prompt(self, query_text: str, passages: List[Passage]) -> str:
        """Build prompt for LLM.
        
        Args:
            query_text: User's question.
            passages: Retrieved passages.
        
        Returns:
            Formatted prompt string.
        """
        context = "\n\n".join([
            f"[{p.section}]\n{p.text}"
            for p in passages
        ])
        
        return f"""Based on the following document excerpts, answer the question:

DOCUMENTS:
{context}

QUESTION: {query_text}

ANSWER:"""
    
    def _build_sources(self, passages: List[Passage]) -> List[dict]:
        """Build source attribution list.
        
        Args:
            passages: Retrieved passages.
        
        Returns:
            List of source attribution dicts.
        """
        sources = []
        seen_docs = set()
        
        for passage in passages:
            doc_key = (passage.document_id, passage.section)
            if doc_key not in seen_docs:
                sources.append({
                    "document_id": passage.document_id,
                    "document_name": passage.document_id,  # Will be filled in by session manager
                    "section": passage.section,
                    "passage": passage.text[:200] + "..." if len(passage.text) > 200 else passage.text,
                })
                seen_docs.add(doc_key)
        
        return sources
