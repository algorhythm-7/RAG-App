"""Stage 2: Reasoning LLM — differential diagnosis over hybrid-retrieved context."""

import json
import time
from typing import List, Tuple

from openai import OpenAI

from src.models import DiagnosisResult, Passage
from src.utils.constants import (
    ERROR_CODES,
    OPENROUTER_API_BASE_URL,
    OPENROUTER_API_KEY,
    QUERY_TIMEOUT_SECONDS,
    REASONING_MODEL,
)
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)

_SYSTEM_PROMPT = """You are an expert vehicle diagnostic technician. Using ONLY the provided service \
manual excerpts (with page citations) and diagram captions, produce a differential diagnosis for the \
driver's symptom.

Think step by step, then respond ONLY with JSON in this exact shape, with no extra commentary:
{
  "thinking": "short internal reasoning trace",
  "steps": ["step 1", "step 2", "..."],
  "differential": [{"cause": "...", "likelihood": "high|medium|low", "evidence": "..."}],
  "cited_pages": ["Page 12", "..."]
}
If the excerpts do not contain enough information, say so in "thinking" and keep "differential" minimal."""


class ReasoningLLM:
    """Stage 2 reasoning: hybrid-retrieved context -> differential diagnosis."""

    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set in environment or secrets")
        self.client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_API_BASE_URL)

    def diagnose(
        self,
        symptom_text: str,
        retrieved: List[Tuple[Passage, float]],
        timeout_seconds: int = QUERY_TIMEOUT_SECONDS,
    ) -> DiagnosisResult:
        """Produce a differential diagnosis from the symptom and hybrid-retrieved passages.

        Args:
            symptom_text: The driver's symptom description.
            retrieved: Fused (Passage, score) results from the hybrid retriever.
            timeout_seconds: Timeout for the LLM call.

        Returns:
            DiagnosisResult with thinking trace, steps, differential, citations, diagrams.
        """
        start_time = time.time()
        diagrams = [
            {"section": p.section, "image_bytes": p.image_bytes}
            for p, _ in retrieved
            if p.is_diagram and p.image_bytes
        ]

        if not retrieved:
            return DiagnosisResult(
                thinking="No relevant passages were retrieved from the uploaded manuals.",
                diagrams=diagrams,
                response_time_ms=int((time.time() - start_time) * 1000),
            )

        context = self._build_context(retrieved)

        try:
            response = self.client.chat.completions.create(
                model=REASONING_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"SYMPTOM: {symptom_text}\n\nEXCERPTS:\n{context}"},
                ],
                temperature=0.3,
                max_tokens=900,
                timeout=timeout_seconds,
            )
            parsed = self._parse_json(response.choices[0].message.content)
            elapsed_ms = int((time.time() - start_time) * 1000)

            log_event("reasoning", passages=len(retrieved), response_time_ms=elapsed_ms)

            return DiagnosisResult(
                thinking=parsed.get("thinking", ""),
                steps=parsed.get("steps", []),
                differential=parsed.get("differential", []),
                cited_pages=parsed.get("cited_pages") or self._default_pages(retrieved),
                diagrams=diagrams,
                confidence=0.8 if parsed.get("differential") else 0.3,
                response_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Reasoning LLM failed: {e}")
            return DiagnosisResult(
                thinking=ERROR_CODES.get("INTERNAL_ERROR", "An error occurred."),
                diagrams=diagrams,
                response_time_ms=elapsed_ms,
            )

    def _build_context(self, retrieved: List[Tuple[Passage, float]]) -> str:
        return "\n\n".join(f"[{p.section}]\n{p.text}" for p, _ in retrieved)

    def _default_pages(self, retrieved: List[Tuple[Passage, float]]) -> List[str]:
        seen, pages = set(), []
        for p, _ in retrieved:
            if p.section not in seen:
                seen.add(p.section)
                pages.append(p.section)
        return pages

    def _parse_json(self, content: str) -> dict:
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            content = content.split("json", 1)[-1] if content.lower().startswith("json") else content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(content[start:end + 1])
                except json.JSONDecodeError:
                    pass
            return {}
